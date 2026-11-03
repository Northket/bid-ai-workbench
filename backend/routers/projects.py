"""招标项目库 API。

整改 B1：删除策略——
- 默认软删除（写入 deleted_at，进入回收站），关联数据与物理文件全部保留；
- ?permanent=true 才物理删除，且：招标文件仅解除关联（文件保留），
  成果文件先移入 uploads/_orphaned/ 再删记录（文件永不物理删除）；
- 新增 /deleted 回收站列表、/{id}/restore 恢复、/{id}/delete-impact 影响范围。
"""
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from database import UPLOAD_DIR, get_db
from models import (ActivityLog, BidTask, Deliverable, DocumentFile, Milestone,
                    TenderProject)
from schemas import ProjectCreate, ProjectOut, ProjectUpdate

router = APIRouter(prefix="/api/projects", tags=["projects"])


def _live(db: Session):
    """未删除项目的查询入口（所有列表/统计必须从这里出发）。"""
    return db.query(TenderProject).filter(TenderProject.deleted_at.is_(None))


@router.get("", response_model=list[ProjectOut])
def list_projects(
    keyword: str = "",
    region: str = "",
    project_type: str = "",
    stage: str = "",
    favorite: bool | None = None,
    participating: bool | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
):
    q = _live(db)
    if keyword:
        q = q.filter(or_(TenderProject.name.contains(keyword),
                         TenderProject.code.contains(keyword),
                         TenderProject.tenderer.contains(keyword)))
    if region:
        q = q.filter(TenderProject.region == region)
    if project_type:
        q = q.filter(TenderProject.project_type == project_type)
    if stage:
        q = q.filter(TenderProject.stage == stage)
    if favorite is not None:
        q = q.filter(TenderProject.favorite == favorite)
    if participating is not None:
        q = q.filter(TenderProject.participating == participating)
    if date_from:
        q = q.filter(TenderProject.publish_date >= date_from)
    if date_to:
        q = q.filter(TenderProject.publish_date <= date_to)
    return q.order_by(TenderProject.updated_at.desc()).all()


@router.get("/filter-options")
def filter_options(db: Session = Depends(get_db)):
    projects = _live(db).all()
    return {
        "regions": sorted({p.region for p in projects}),
        "project_types": sorted({p.project_type for p in projects}),
        "stages": sorted({p.stage for p in projects}),
    }


@router.get("/deleted", response_model=list[ProjectOut])
def list_deleted(db: Session = Depends(get_db)):
    """回收站：软删除项目列表。"""
    return (db.query(TenderProject).filter(TenderProject.deleted_at.is_not(None))
            .order_by(TenderProject.deleted_at.desc()).all())


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: int, db: Session = Depends(get_db)):
    project = db.get(TenderProject, project_id)
    if not project or project.deleted_at is not None:
        raise HTTPException(404, "项目不存在或已在回收站")
    db.add(ActivityLog(kind="view", target="project", target_id=project.id, title=project.name))
    db.commit()
    return project


@router.post("", response_model=ProjectOut)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    if db.query(TenderProject).filter(TenderProject.code == payload.code,
                                      TenderProject.deleted_at.is_(None)).first():
        raise HTTPException(400, f"项目编号 {payload.code} 已存在")
    project = TenderProject(**payload.model_dump())
    db.add(project)
    db.add(ActivityLog(kind="create", target="project", target_id=0, title=project.name))
    db.commit()
    db.refresh(project)
    return project


@router.put("/{project_id}", response_model=ProjectOut)
def update_project(project_id: int, payload: ProjectUpdate, db: Session = Depends(get_db)):
    project = db.get(TenderProject, project_id)
    if not project or project.deleted_at is not None:
        raise HTTPException(404, "项目不存在或已在回收站")
    data = payload.model_dump(exclude_unset=True)
    if "code" in data and data["code"] != project.code:
        dup = db.query(TenderProject).filter(TenderProject.code == data["code"],
                                             TenderProject.id != project.id,
                                             TenderProject.deleted_at.is_(None)).first()
        if dup:
            raise HTTPException(400, f"项目编号 {data['code']} 已存在")
    for k, v in data.items():
        setattr(project, k, v)
    db.commit()
    db.refresh(project)
    return project


@router.post("/{project_id}/favorite", response_model=ProjectOut)
def toggle_favorite(project_id: int, db: Session = Depends(get_db)):
    project = db.get(TenderProject, project_id)
    if not project or project.deleted_at is not None:
        raise HTTPException(404, "项目不存在或已在回收站")
    project.favorite = not project.favorite
    db.commit()
    db.refresh(project)
    return project


@router.get("/{project_id}/delete-impact")
def delete_impact(project_id: int, db: Session = Depends(get_db)):
    """删除前影响范围（供前端二次确认展示）。"""
    project = db.get(TenderProject, project_id)
    if not project or project.deleted_at is not None:
        raise HTTPException(404, "项目不存在或已在回收站")
    return {
        "project": {"id": project.id, "name": project.name, "code": project.code},
        "documents": db.query(DocumentFile).filter(DocumentFile.project_id == project_id).count(),
        "requirements": sum(1 for r in project.requirements),
        "tasks": sum(1 for t in project.tasks),
        "milestones": sum(1 for m in project.milestones),
        "deliverables": sum(1 for d in project.deliverables),
        "policy": ("默认执行软删除：项目移入回收站，以上全部关联数据与文件保留，可随时恢复。"
                   "物理删除仅可通过显式参数 permanent=true 触发，且文件仍不会被销毁。"),
    }


@router.delete("/{project_id}")
def delete_project(project_id: int, permanent: bool = False, db: Session = Depends(get_db)):
    project = db.get(TenderProject, project_id)
    if not project:
        raise HTTPException(404, "项目不存在")
    if project.deleted_at is not None and not permanent:
        raise HTTPException(400, "项目已在回收站，如需彻底移除请使用 permanent=true")

    if not permanent:
        # ---- 软删除：仅打标记，一切数据与文件保留 ----
        project.deleted_at = datetime.now()
        project.participating = False
        db.commit()
        return {"ok": True, "mode": "soft",
                "message": f"项目「{project.name}」已移入回收站，关联数据与文件已保留，可随时恢复"}

    # ---- 物理删除：文件永不销毁，仅归档/解除关联 ----
    name = project.name
    # 招标文件：解除项目关联，记录与物理文件保留
    detached = db.query(DocumentFile).filter(DocumentFile.project_id == project_id).count()
    db.query(DocumentFile).filter(DocumentFile.project_id == project_id).update(
        {DocumentFile.project_id: None}, synchronize_session="fetch")
    # 成果文件：物理文件移入 _orphaned 归档目录后删除记录
    orphan_dir = UPLOAD_DIR / "_orphaned" / time_folder()
    moved = 0
    for d in list(project.deliverables):
        if d.file_path:
            src = UPLOAD_DIR.parent / d.file_path
            if src.exists():
                orphan_dir.mkdir(parents=True, exist_ok=True)
                (orphan_dir / src.name).write_bytes(src.read_bytes())
                src.unlink()
                moved += 1
    # Requirement / Task / Milestone 由 ORM 级联删除；Deliverable 记录删除
    db.delete(project)
    db.commit()
    return {"ok": True, "mode": "permanent", "message": (
        f"项目「{name}」已物理删除；{detached} 份招标文件已解除关联并保留，"
        f"{moved} 个成果文件已归档至 uploads/_orphaned/（均未销毁）")}


@router.post("/{project_id}/restore", response_model=ProjectOut)
def restore_project(project_id: int, db: Session = Depends(get_db)):
    project = db.get(TenderProject, project_id)
    if not project:
        raise HTTPException(404, "项目不存在")
    if project.deleted_at is None:
        raise HTTPException(400, "项目不在回收站")
    project.deleted_at = None
    db.commit()
    db.refresh(project)
    return project


def time_folder() -> str:
    from datetime import datetime as _dt
    return _dt.now().strftime("%Y%m%d_%H%M%S")
