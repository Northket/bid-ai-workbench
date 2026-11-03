"""投标要求管理 API（技术标 / 商务标 / 资信标）。

整改 C1：要求可关联原始招标文件（document_id + 页码/章节/条款/原文片段），
核验状态流转自动记录 verified_at / verified_by。
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import BidRequirement, DocumentFile, TenderProject
from schemas import RequirementCreate, RequirementOut, RequirementUpdate

router = APIRouter(prefix="/api/requirements", tags=["requirements"])

CATEGORY_NAMES = {"technical": "技术标", "business": "商务标", "credit": "资信标"}
DEFAULT_OPERATOR = "张工（投标部）"


def _to_out(req: BidRequirement) -> dict:
    data = RequirementOut.model_validate(req).model_dump()
    data["project_name"] = req.project.name if req.project else None
    data["document_name"] = req.document.original_name if req.document else None
    return data


def _apply_verification(req: BidRequirement, data: dict):
    """核验状态与旧字段 confirmed 保持双向同步，并记录核验人与时间。"""
    status = data.get("verification_status")
    if status is None and data.get("confirmed") is not None:
        status = "confirmed" if data["confirmed"] else "pending"
    if status is not None:
        req.verification_status = status
        if status == "confirmed":
            req.verified_at = datetime.now()
            req.verified_by = DEFAULT_OPERATOR
            req.confirmed = True
        else:
            req.confirmed = False
            if status == "rejected":
                req.verified_at = datetime.now()
                req.verified_by = DEFAULT_OPERATOR


@router.get("")
def list_requirements(project_id: int | None = None, category: str = "",
                      status: str = "", keyword: str = "", db: Session = Depends(get_db)):
    q = db.query(BidRequirement)
    if project_id:
        q = q.filter(BidRequirement.project_id == project_id)
    if category:
        if category not in CATEGORY_NAMES:
            raise HTTPException(400, "category 取值必须为 technical/business/credit")
        q = q.filter(BidRequirement.category == category)
    if status:
        q = q.filter(BidRequirement.status == status)
    if keyword:
        q = q.filter(BidRequirement.name.contains(keyword))
    reqs = q.order_by(BidRequirement.importance.desc(), BidRequirement.updated_at.desc()).all()
    return [_to_out(r) for r in reqs]


@router.get("/summary")
def summary(db: Session = Depends(get_db)):
    """三类要求完成情况统计。"""
    rows = db.query(BidRequirement).all()
    result = {}
    for key, label in CATEGORY_NAMES.items():
        subset = [r for r in rows if r.category == key]
        result[key] = {
            "label": label,
            "total": len(subset),
            "done": sum(1 for r in subset if r.status == "已完成"),
            "in_progress": sum(1 for r in subset if r.status == "进行中"),
            "confirmed": sum(1 for r in subset if r.confirmed),
        }
    return result


@router.post("")
def create_requirement(payload: RequirementCreate, db: Session = Depends(get_db)):
    p = db.get(TenderProject, payload.project_id)
    if not p or p.deleted_at is not None:
        raise HTTPException(400, "关联项目不存在或已在回收站")
    data = payload.model_dump()
    if data.get("document_id") is not None and not db.get(DocumentFile, data["document_id"]):
        raise HTTPException(400, "关联文件不存在")
    req = BidRequirement(**data)
    _apply_verification(req, data)
    db.add(req)
    db.commit()
    db.refresh(req)
    return _to_out(req)


@router.put("/{req_id}")
def update_requirement(req_id: int, payload: RequirementUpdate, db: Session = Depends(get_db)):
    req = db.get(BidRequirement, req_id)
    if not req:
        raise HTTPException(404, "要求不存在")
    data = payload.model_dump(exclude_unset=True)
    if "project_id" in data:
        p = db.get(TenderProject, data["project_id"])
        if not p or p.deleted_at is not None:
            raise HTTPException(400, "关联项目不存在或已在回收站")
    if "document_id" in data and data["document_id"] is not None \
            and not db.get(DocumentFile, data["document_id"]):
        raise HTTPException(400, "关联文件不存在")
    for k, v in data.items():
        setattr(req, k, v)
    _apply_verification(req, data)
    db.commit()
    db.refresh(req)
    return _to_out(req)


@router.delete("/{req_id}")
def delete_requirement(req_id: int, db: Session = Depends(get_db)):
    req = db.get(BidRequirement, req_id)
    if not req:
        raise HTTPException(404, "要求不存在")
    db.delete(req)
    db.commit()
    return {"ok": True}
