"""投标项目管理 API：任务清单、时间节点、成果文件、项目工作区汇总。"""
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from database import UPLOAD_DIR, get_db
from models import BidTask, Deliverable, Milestone, TenderProject
from schemas import DeliverableOut, MilestoneCreate, MilestoneOut, TaskCreate, TaskOut, TaskUpdate

router = APIRouter(prefix="/api/bids", tags=["bids"])


@router.get("/projects")
def list_bid_projects(db: Session = Depends(get_db)):
    """参与投标的项目及其任务进度（不含回收站项目）。"""
    projects = db.query(TenderProject).filter(
        TenderProject.participating == True,  # noqa: E712
        TenderProject.deleted_at.is_(None)).all()
    result = []
    for p in projects:
        tasks = p.tasks
        done = sum(1 for t in tasks if t.status == "已完成")
        result.append({
            "id": p.id,
            "name": p.name,
            "code": p.code,
            "region": p.region,
            "project_type": p.project_type,
            "stage": p.stage,
            "deadline": p.deadline,
            "budget": p.budget,
            "task_total": len(tasks),
            "task_done": done,
            "progress": round(done / len(tasks) * 100) if tasks else 0,
            "milestone_count": len(p.milestones),
            "deliverable_count": len(p.deliverables),
        })
    return result


@router.get("/projects/{project_id}/overview")
def project_overview(project_id: int, db: Session = Depends(get_db)):
    """投标工作区汇总：基本信息 + 任务 + 节点 + 成果。"""
    p = db.get(TenderProject, project_id)
    if not p or p.deleted_at is not None:
        raise HTTPException(404, "项目不存在或已在回收站")
    return {
        "project": {
            "id": p.id, "name": p.name, "code": p.code, "region": p.region,
            "project_type": p.project_type, "tender_method": p.tender_method,
            "tenderer": p.tenderer, "agency": p.agency, "budget": p.budget,
            "publish_date": p.publish_date, "deadline": p.deadline,
            "stage": p.stage, "participating": p.participating, "description": p.description,
        },
        "tasks": [TaskOut.model_validate(t).model_dump() for t in p.tasks],
        "milestones": sorted([MilestoneOut.model_validate(m).model_dump() for m in p.milestones],
                             key=lambda m: (m["date"] is None, m["date"])),
        "deliverables": [DeliverableOut.model_validate(d).model_dump() for d in p.deliverables],
    }


# ---------------- 任务 ----------------
@router.post("/tasks", response_model=TaskOut)
def create_task(payload: TaskCreate, db: Session = Depends(get_db)):
    _p = db.get(TenderProject, payload.project_id)
    if not _p or _p.deleted_at is not None:
        raise HTTPException(400, "关联项目不存在或已在回收站")
    task = BidTask(**payload.model_dump())
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.put("/tasks/{task_id}", response_model=TaskOut)
def update_task(task_id: int, payload: TaskUpdate, db: Session = Depends(get_db)):
    task = db.get(BidTask, task_id)
    if not task:
        raise HTTPException(404, "任务不存在")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(task, k, v)
    db.commit()
    db.refresh(task)
    return task


@router.delete("/tasks/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = db.get(BidTask, task_id)
    if not task:
        raise HTTPException(404, "任务不存在")
    db.delete(task)
    db.commit()
    return {"ok": True}


# ---------------- 时间节点 ----------------
@router.post("/milestones", response_model=MilestoneOut)
def create_milestone(payload: MilestoneCreate, db: Session = Depends(get_db)):
    _p = db.get(TenderProject, payload.project_id)
    if not _p or _p.deleted_at is not None:
        raise HTTPException(400, "关联项目不存在或已在回收站")
    m = Milestone(**payload.model_dump())
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


@router.delete("/milestones/{milestone_id}")
def delete_milestone(milestone_id: int, db: Session = Depends(get_db)):
    m = db.get(Milestone, milestone_id)
    if not m:
        raise HTTPException(404, "节点不存在")
    db.delete(m)
    db.commit()
    return {"ok": True}


# ---------------- 成果文件 ----------------
@router.post("/deliverables/upload")
async def upload_deliverable(
    project_id: int = Form(...),
    category: str = Form("投标文件"),
    version: str = Form("V1.0"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """整改 B3：走统一安全存储服务（分块/限额/魔数/路径安全）。"""
    from services.file_storage import DELIVERABLE_EXTS, save_upload

    _p = db.get(TenderProject, project_id)
    if not _p or _p.deleted_at is not None:
        raise HTTPException(400, "关联项目不存在或已在回收站")
    stored = await save_upload(file, "deliverables", db, allowed_exts=DELIVERABLE_EXTS)
    d = Deliverable(project_id=project_id, name=stored.original_name, category=category,
                    version=version,
                    file_path=f"uploads/deliverables/{stored.stored_name}", size=stored.size)
    db.add(d)
    try:
        db.commit()
    except Exception:
        db.rollback()
        stored.path.unlink(missing_ok=True)
        raise HTTPException(500, "成果文件记录保存失败，已回滚本次上传")
    db.refresh(d)
    return DeliverableOut.model_validate(d)


@router.delete("/deliverables/{deliverable_id}")
def delete_deliverable(deliverable_id: int, db: Session = Depends(get_db)):
    d = db.get(Deliverable, deliverable_id)
    if not d:
        raise HTTPException(404, "成果文件不存在")
    if d.file_path:
        real = UPLOAD_DIR.parent / d.file_path
        if real.exists():
            real.unlink()
    db.delete(d)
    db.commit()
    return {"ok": True}


@router.get("/deliverables/{deliverable_id}/download")
def download_deliverable(deliverable_id: int, db: Session = Depends(get_db)):
    from fastapi.responses import FileResponse

    d = db.get(Deliverable, deliverable_id)
    if not d:
        raise HTTPException(404, "成果文件不存在")
    if not d.file_path:
        raise HTTPException(400, "演示记录没有实际文件，无法下载")
    p = UPLOAD_DIR.parent / d.file_path
    if not p.exists():
        raise HTTPException(404, "文件已不存在")
    return FileResponse(p, filename=d.name)
