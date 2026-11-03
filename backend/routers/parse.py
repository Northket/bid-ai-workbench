# -*- coding: utf-8 -*-
"""第二阶段：真实文档解析 API。

- POST /api/parse/documents/{id}      启动解析（后台执行，轮询任务状态）
- GET  /api/parse/documents/{id}/tasks 任务版本列表
- GET  /api/parse/tasks/{id}          任务详情（状态轮询）
- GET  /api/parse/tasks/{id}/results  结果（可按类别/核验状态过滤）
- GET  /api/parse/documents/{id}/latest 最新完成任务的完整结果
- PUT  /api/parse/results/{id}        人工核验/修改（original_text 永不覆盖）
- POST /api/parse/tasks/{id}/retry    失败重试
- GET  /api/parse/tasks/{id}/export   导出 xlsx
- POST /api/parse/results/{id}/to-requirement  一键登记为投标要求
"""
import hashlib
import threading
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import UPLOAD_DIR, SessionLocal, get_db
from models import BidRequirement, DocumentFile, DocumentParseResult, DocumentParseTask
from services.doc_parser.engine import (ENGINE_VERSION, ParseEngineError, build_report,
                                        extract_structured, parse_document)

router = APIRouter(prefix="/api/parse", tags=["parse"])

CATEGORIES = {
    "basic": "项目基本信息", "timeline": "关键时间节点", "qualification": "投标人资格条件",
    "rejection": "否决投标及实质性响应条款", "evaluation": "评标办法及评分标准",
    "technical": "技术标要求", "commercial": "商务标及资信标要求",
}
VERIFIED_SET = {"confirmed", "doubtful"}


def sha256_of(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------- 任务执行（后台线程，独立会话） ----------------
def run_parse_task(task_id: int):
    db = SessionLocal()
    try:
        task = db.get(DocumentParseTask, task_id)
        if not task:
            return
        doc = db.get(DocumentFile, task.document_id)
        path = UPLOAD_DIR / "tender-docs" / (doc.stored_name or "") if doc else None
        if not doc or not doc.stored_name or not path or not path.exists():
            task.status = "failed"
            task.error_message = "文件不存在或已被删除，无法解析"
            task.finished_at = datetime.now()
            if doc:
                doc.status = "解析失败"
                doc.error_message = task.error_message
            db.commit()
            return

        task.file_sha256 = sha256_of(path)
        task.engine_version = ENGINE_VERSION
        db.commit()

        parsed = parse_document(path)
        items = extract_structured(parsed)
        report = build_report(parsed, items)

        # 写入结果（批量）
        for it in items:
            db.add(DocumentParseResult(
                task_id=task.id, document_id=doc.id,
                category=it.category, field_key=it.field_key, field_name=it.field_name,
                value=it.value, original_text=it.original_text,
                pdf_page=it.pdf_page, page_label=it.page_label or "",
                chapter=it.chapter[:200], section_no=it.section_no[:32],
                method=it.method, source_layer=it.source_layer, confidence=it.confidence))

        # 结转历史已核验条目（重新解析不覆盖人工成果）
        old_tasks = (db.query(DocumentParseTask)
                     .filter(DocumentParseTask.document_id == doc.id,
                             DocumentParseTask.id != task.id)
                     .order_by(DocumentParseTask.id.desc()).all())
        for old in old_tasks:
            verified = (db.query(DocumentParseResult)
                        .filter(DocumentParseResult.task_id == old.id,
                                DocumentParseResult.verification_status.in_(VERIFIED_SET))
                        .all())
            if not verified:
                continue
            for r in verified:
                db.add(DocumentParseResult(
                    task_id=task.id, document_id=doc.id,
                    category=r.category, field_key=r.field_key, field_name=r.field_name,
                    value=r.manual_value or r.value, original_text=r.original_text,
                    manual_value=r.manual_value, pdf_page=r.pdf_page,
                    page_label=r.page_label, chapter=r.chapter, section_no=r.section_no,
                    method="manual", source_layer=r.source_layer,
                    confidence=r.confidence, verification_status=r.verification_status,
                    verified_at=r.verified_at, verified_by=r.verified_by,
                    is_carried=True, source_task_id=old.id))
            break  # 只从最近一个含已核验条目的版本结转

        task.status = "completed"
        task.finished_at = datetime.now()
        task.stats = report
        task.warnings = parsed.warnings
        task.parser = parsed.parser
        doc.status = "解析完成"
        doc.error_message = ""
        db.commit()
    except ParseEngineError as e:
        _fail(db, task_id, str(e))
    except Exception as e:  # pragma: no cover
        _fail(db, task_id, f"解析异常：{e}")
    finally:
        db.close()


def _fail(db: Session, task_id: int, message: str):
    task = db.get(DocumentParseTask, task_id)
    if not task:
        return
    task.status = "failed"
    task.error_message = message[:2000]
    task.finished_at = datetime.now()
    doc = db.get(DocumentFile, task.document_id)
    if doc:
        doc.status = "解析失败"
        doc.error_message = message[:500]
    db.commit()


def start_parse(doc_id: int, db: Session) -> DocumentParseTask:
    """创建任务并返回（执行由后台线程完成）。"""
    doc = db.get(DocumentFile, doc_id)
    if not doc:
        raise HTTPException(404, "文件不存在")
    if doc.is_demo or not doc.stored_name:
        raise HTTPException(400, "演示记录没有实际文件；请上传/导入真实文件后解析")
    if not (UPLOAD_DIR / "tender-docs" / doc.stored_name).exists():
        raise HTTPException(400, "文件已不存在于存储目录，无法解析")

    last = (db.query(DocumentParseTask)
            .filter(DocumentParseTask.document_id == doc_id)
            .order_by(DocumentParseTask.id.desc()).first())
    task = DocumentParseTask(document_id=doc_id, version=(last.version + 1) if last else 1,
                             status="running", engine_version=ENGINE_VERSION)
    db.add(task)
    doc.status = "解析中"
    db.commit()
    db.refresh(task)
    return task


# ---------------- 端点 ----------------
@router.post("/documents/{doc_id}")
def start(doc_id: int, background: BackgroundTasks, db: Session = Depends(get_db)):
    task = start_parse(doc_id, db)
    background.add_task(lambda: threading.Thread(target=run_parse_task, args=(task.id,), daemon=True).start())
    return {"ok": True, "task_id": task.id, "version": task.version,
            "message": f"解析任务 V{task.version} 已启动，请稍候刷新查看结果"}


@router.get("/documents/{doc_id}/tasks")
def list_tasks(doc_id: int, db: Session = Depends(get_db)):
    tasks = (db.query(DocumentParseTask)
             .filter(DocumentParseTask.document_id == doc_id)
             .order_by(DocumentParseTask.id.desc()).all())
    return [{
        "id": t.id, "version": t.version, "status": t.status,
        "engine_version": t.engine_version, "file_sha256": t.file_sha256,
        "stats": t.stats, "warnings": t.warnings, "error_message": t.error_message,
        "started_at": t.started_at, "finished_at": t.finished_at,
    } for t in tasks]


@router.get("/tasks/{task_id}")
def get_task(task_id: int, db: Session = Depends(get_db)):
    t = db.get(DocumentParseTask, task_id)
    if not t:
        raise HTTPException(404, "任务不存在")
    return {"id": t.id, "document_id": t.document_id, "version": t.version,
            "status": t.status, "stats": t.stats, "warnings": t.warnings,
            "error_message": t.error_message,
            "started_at": t.started_at, "finished_at": t.finished_at,
            "file_sha256": t.file_sha256, "engine_version": t.engine_version}


@router.get("/tasks/{task_id}/results")
def task_results(task_id: int, category: str = "", verification: str = "",
                 db: Session = Depends(get_db)):
    t = db.get(DocumentParseTask, task_id)
    if not t:
        raise HTTPException(404, "任务不存在")
    q = db.query(DocumentParseResult).filter(DocumentParseResult.task_id == task_id)
    if category:
        q = q.filter(DocumentParseResult.category == category)
    if verification:
        q = q.filter(DocumentParseResult.verification_status == verification)
    rows = q.order_by(DocumentParseResult.category, DocumentParseResult.id).all()
    grouped: dict[str, list] = {}
    for r in rows:
        grouped.setdefault(r.category, []).append({
            "id": r.id, "field_key": r.field_key, "field_name": r.field_name,
            "value": r.manual_value or r.value,
            "original_text": r.original_text, "manual_value": r.manual_value,
            "pdf_page": r.pdf_page, "page_label": r.page_label,
            "chapter": r.chapter, "section_no": r.section_no,
            "method": r.method, "source_layer": r.source_layer,
            "confidence": r.confidence, "verification_status": r.verification_status,
            "verified_at": r.verified_at, "verified_by": r.verified_by,
            "is_carried": r.is_carried, "source_task_id": r.source_task_id,
        })
    return {"task_id": task_id, "status": t.status, "categories": grouped,
            "category_names": CATEGORIES}


@router.get("/documents/{doc_id}/latest")
def latest_results(doc_id: int, db: Session = Depends(get_db)):
    """最新任务（优先已完成）的完整结果，前端工作台默认视图。"""
    task = (db.query(DocumentParseTask)
            .filter(DocumentParseTask.document_id == doc_id,
                    DocumentParseTask.status == "completed")
            .order_by(DocumentParseTask.id.desc()).first())
    if not task:
        task = (db.query(DocumentParseTask)
                .filter(DocumentParseTask.document_id == doc_id)
                .order_by(DocumentParseTask.id.desc()).first())
    if not task:
        return {"task": None, "categories": {}, "category_names": CATEGORIES}
    data = task_results(task.id, db=db)
    data["task"] = {
        "id": task.id, "version": task.version, "status": task.status,
        "stats": task.stats, "warnings": task.warnings,
        "error_message": task.error_message, "finished_at": task.finished_at,
        "file_sha256": task.file_sha256, "engine_version": task.engine_version}
    return data


class VerifyBody(BaseModel):
    verification_status: str  # pending/confirmed/doubtful/failed
    manual_value: str | None = None


@router.put("/results/{result_id}")
def verify_result(result_id: int, body: VerifyBody, db: Session = Depends(get_db)):
    r = db.get(DocumentParseResult, result_id)
    if not r:
        raise HTTPException(404, "结果不存在")
    if body.verification_status not in ("pending", "confirmed", "doubtful", "failed"):
        raise HTTPException(400, "核验状态取值非法")
    if body.manual_value is not None and body.manual_value.strip():
        r.manual_value = body.manual_value.strip()  # original_text 永不覆盖
    r.verification_status = body.verification_status
    r.verified_at = datetime.now()
    r.verified_by = "张工（投标部）"
    db.commit()
    return {"ok": True, "id": r.id, "verification_status": r.verification_status,
            "manual_value": r.manual_value}


@router.post("/tasks/{task_id}/retry")
def retry(task_id: int, background: BackgroundTasks, db: Session = Depends(get_db)):
    t = db.get(DocumentParseTask, task_id)
    if not t:
        raise HTTPException(404, "任务不存在")
    if t.status != "failed":
        raise HTTPException(400, "仅失败任务可重试；如需重新解析请直接发起新任务")
    t.status = "running"
    t.error_message = ""
    t.started_at = datetime.now()
    t.finished_at = None
    db.commit()
    background.add_task(lambda: threading.Thread(target=run_parse_task, args=(t.id,), daemon=True).start())
    return {"ok": True, "task_id": t.id, "message": "已重新启动解析"}


@router.get("/tasks/{task_id}/export")
def export_results(task_id: int, db: Session = Depends(get_db)):
    import io

    from openpyxl import Workbook
    t = db.get(DocumentParseTask, task_id)
    if not t:
        raise HTTPException(404, "任务不存在")
    rows = (db.query(DocumentParseResult)
            .filter(DocumentParseResult.task_id == task_id)
            .order_by(DocumentParseResult.category, DocumentParseResult.id).all())
    wb = Workbook()
    wb.remove(wb.active)
    headers = ["字段", "提取结果", "原文依据", "PDF页序", "印刷页码", "章节", "条款号",
               "提取方式", "可信度", "核验状态", "人工修改值", "结转"]
    method_names = {"pdf_text": "PDF文本提取", "ocr": "OCR提取", "rule": "规则提取",
                    "ai": "AI语义提取", "manual": "人工录入"}
    verify_names = {"pending": "待核验", "confirmed": "已核验", "doubtful": "存在疑问",
                    "failed": "提取失败"}
    by_cat: dict[str, list] = {}
    for r in rows:
        by_cat.setdefault(r.category, []).append(r)
    summary = wb.create_sheet("总览")
    summary.append(["类别", "条目数", "已核验"])
    for cat, cat_name in CATEGORIES.items():
        rs = by_cat.get(cat, [])
        summary.append([cat_name, len(rs), sum(1 for x in rs if x.verification_status == "confirmed")])
    for cat, cat_name in CATEGORIES.items():
        ws = wb.create_sheet(cat_name[:28])
        ws.append(headers)
        for r in by_cat.get(cat, []):
            ws.append([
                r.field_name or r.field_key,
                (r.manual_value or r.value or "")[:1000],
                r.original_text[:1000],
                r.pdf_page or "", r.page_label or "", r.chapter or "", r.section_no or "",
                method_names.get(r.method, r.method),
                {"high": "高", "medium": "中", "low": "低"}.get(r.confidence, r.confidence),
                verify_names.get(r.verification_status, r.verification_status),
                r.manual_value or "",
                "历史结转" if r.is_carried else "",
            ])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    doc = db.get(DocumentFile, t.document_id)
    fname = f"解析结果_V{t.version}_{(doc.original_name if doc else '')[:20]}.xlsx".replace("/", "_")
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{__import__('urllib.parse', fromlist=['quote']).quote(fname)}"})


@router.post("/results/{result_id}/to-requirement")
def to_requirement(result_id: int, db: Session = Depends(get_db)):
    """把一条解析结果登记为投标要求（复用 C1 溯源体系）。"""
    r = db.get(DocumentParseResult, result_id)
    if not r:
        raise HTTPException(404, "结果不存在")
    doc = db.get(DocumentFile, r.document_id)
    if not doc or not doc.project_id:
        raise HTTPException(400, "该文件未关联项目，请先在文件中心关联项目")
    cat_map = {"technical": "technical", "commercial": "business",
               "qualification": "credit", "rejection": "business",
               "evaluation": "technical", "timeline": "business", "basic": "technical"}
    req = BidRequirement(
        project_id=doc.project_id,
        category=cat_map.get(r.category, "technical"),
        name=(r.field_name or r.field_key or "解析条目")[:180],
        content=(r.manual_value or r.value or "")[:2000],
        source_text=r.chapter[:280] or "招标文件解析",
        page_no=r.page_label or "",
        document_id=r.document_id,
        page_number=r.pdf_page,
        chapter_title=r.chapter[:200],
        section_number=r.section_no[:32],
        original_text=r.original_text[:2000],
        extraction_method="rule",
        verification_status="pending")
    db.add(req)
    db.commit()
    db.refresh(req)
    return {"ok": True, "requirement_id": req.id,
            "message": "已登记为投标要求（待核验），可在投标要求管理中查看"}
