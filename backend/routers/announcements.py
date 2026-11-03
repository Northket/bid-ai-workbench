"""招标公告中心 API。

演示数据在 seed 中写入，is_demo=True；真实数据源（深圳公共资源交易平台）
接入接口在 /fetch 预留，当前返回"未配置"而非伪造数据。
"""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from database import get_db
from models import Announcement, Setting, TenderProject
from schemas import AnnouncementCreate, AnnouncementOut

router = APIRouter(prefix="/api/announcements", tags=["announcements"])


@router.get("")
def list_announcements(
    keyword: str = "",
    ann_type: str = "",
    project_code: str = "",
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    q = db.query(Announcement)
    if keyword:
        q = q.filter(or_(Announcement.title.contains(keyword),
                         Announcement.content.contains(keyword),
                         Announcement.project_code.contains(keyword)))
    if ann_type:
        q = q.filter(Announcement.ann_type == ann_type)
    if project_code:
        q = q.filter(Announcement.project_code == project_code)
    if date_from:
        q = q.filter(Announcement.publish_date >= date_from)
    if date_to:
        q = q.filter(Announcement.publish_date <= date_to)
    total = q.count()
    items = (q.order_by(Announcement.publish_date.desc(), Announcement.id.desc())
             .offset((page - 1) * page_size).limit(page_size).all())
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [AnnouncementOut.model_validate(i) for i in items],
    }


@router.get("/stats")
def stats(db: Session = Depends(get_db)):
    rows = db.query(Announcement).all()
    by_type: dict[str, int] = {}
    for r in rows:
        by_type[r.ann_type] = by_type.get(r.ann_type, 0) + 1
    demo_count = sum(1 for r in rows if r.is_demo)
    return {"total": len(rows), "by_type": by_type, "demo_count": demo_count}


@router.get("/{ann_id}", response_model=AnnouncementOut)
def get_announcement(ann_id: int, db: Session = Depends(get_db)):
    ann = db.get(Announcement, ann_id)
    if not ann:
        raise HTTPException(404, "公告不存在")
    return ann


@router.post("", response_model=AnnouncementOut)
def create_announcement(payload: AnnouncementCreate, db: Session = Depends(get_db)):
    data = payload.model_dump()
    data.setdefault("source", "手动录入")
    ann = Announcement(**data, is_demo=False)
    db.add(ann)
    db.commit()
    db.refresh(ann)
    return ann


@router.delete("/{ann_id}")
def delete_announcement(ann_id: int, db: Session = Depends(get_db)):
    ann = db.get(Announcement, ann_id)
    if not ann:
        raise HTTPException(404, "公告不存在")
    db.delete(ann)
    db.commit()
    return {"ok": True}


@router.post("/fetch")
def fetch_from_source(db: Session = Depends(get_db)):
    """预留的外部数据源抓取接口。

    未配置真实抓取服务时明确返回 not_configured，不用假数据冒充。
    """
    endpoint = db.query(Setting).filter(Setting.key == "data_source.szggzy.url").first()
    return {
        "ok": False,
        "status": "not_configured",
        "message": "真实数据源抓取服务尚未接入。请在「系统设置 → 数据源配置」中配置深圳公共资源交易平台接口后重试。",
        "endpoint": endpoint.value if endpoint else "",
        "reference_url": "https://www.szggzy.cn",
    }
