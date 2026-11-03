"""工作台汇总 API。"""
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import (ActivityLog, Announcement, BidRequirement, BidTask, Deliverable,
                    DocumentFile, HistoricalProject, Milestone, TenderProject)
from schemas import DashboardOut, DocumentOut, ProjectOut

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardOut)
def dashboard(db: Session = Depends(get_db)):
    projects = db.query(TenderProject).filter(TenderProject.deleted_at.is_(None)).all()
    tasks = db.query(BidTask).all()
    docs = db.query(DocumentFile).order_by(DocumentFile.uploaded_at.desc()).limit(6).all()
    reqs = db.query(BidRequirement).all()
    history = db.query(HistoricalProject).all()

    type_map: dict[str, int] = {}
    for p in projects:
        type_map[p.project_type] = type_map.get(p.project_type, 0) + 1

    trend_map: dict[str, float] = {}
    for h in history:
        if h.bid_open_date:
            key = h.bid_open_date.strftime("%Y-%m")
            trend_map[key] = round(trend_map.get(key, 0) + h.bid_amount, 2)
    win_trend = [{"month": k, "amount": v} for k, v in sorted(trend_map.items())][-8:]

    recent_views = (db.query(ActivityLog)
                    .filter(ActivityLog.kind == "view", ActivityLog.target == "project")
                    .order_by(ActivityLog.id.desc()).limit(20).all())
    seen: set[int] = set()
    recent_projects = []
    for log in recent_views:
        p = db.get(TenderProject, log.target_id)
        if p and p.id not in seen and p.deleted_at is None:
            seen.add(p.id)
            recent_projects.append(ProjectOut.model_validate(p))
        if len(recent_projects) >= 5:
            break
    if not recent_projects:
        recent_projects = [ProjectOut.model_validate(p)
                           for p in db.query(TenderProject)
                           .filter(TenderProject.deleted_at.is_(None))
                           .order_by(TenderProject.updated_at.desc()).limit(5).all()]

    bid_progress = []
    for p in projects:
        if not p.participating:
            continue
        ptasks = [t for t in tasks if t.project_id == p.id]
        done = sum(1 for t in ptasks if t.status == "已完成")
        bid_progress.append({
            "project_id": p.id, "name": p.name, "deadline": p.deadline,
            "total": len(ptasks), "done": done,
            "progress": round(done / len(ptasks) * 100) if ptasks else 0,
        })
    bid_progress.sort(key=lambda x: (x["deadline"] is None, x["deadline"]))

    today = date.today()
    upcoming = (db.query(Milestone, TenderProject)
                .join(TenderProject, Milestone.project_id == TenderProject.id)
                .filter(Milestone.date >= today, TenderProject.deleted_at.is_(None))
                .order_by(Milestone.date).limit(6).all())
    upcoming_list = [
        {"project_id": m.project_id, "project_name": p.name, "name": m.name,
         "date": m.date, "kind": m.kind}
        for m, p in upcoming
    ]

    return DashboardOut(
        project_count=len(projects),
        participating_count=sum(1 for p in projects if p.participating),
        favorite_count=sum(1 for p in projects if p.favorite),
        pending_task_count=sum(1 for t in tasks if t.status != "已完成"),
        document_count=db.query(DocumentFile).count(),
        requirement_pending=sum(1 for r in reqs if r.status != "已完成"),
        announcement_count=db.query(Announcement).count(),
        history_count=len(history),
        type_distribution=[{"name": k, "value": v} for k, v in type_map.items()],
        win_trend=win_trend,
        recent_projects=recent_projects,
        recent_documents=[DocumentOut.model_validate(d).model_copy(
            update={"project_name": d.project.name if d.project else None}) for d in docs],
        bid_progress=bid_progress,
        upcoming_milestones=upcoming_list,
    )
