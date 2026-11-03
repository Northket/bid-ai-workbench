"""招标文件解析中心 API。

上传真实文件保存至本地 uploads/tender-docs；解析服务接口预留，
演示阶段 /parse 返回明确标注的演示解析结果。
"""
import hashlib
import json
import threading
import uuid
import zipfile
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from database import UPLOAD_DIR, get_db
from models import ActivityLog, DocumentFile, TenderProject
from schemas import DocumentOut, DocumentUpdate
from services.file_storage import TENDER_DOC_EXTS, get_max_size_mb, sanitize_filename, save_upload

router = APIRouter(prefix="/api/documents", tags=["documents"])

# 兼容引用：第一阶段解析中心以 PDF/Word 为主，Excel 清单文件亦接受存储
ALLOWED_EXT = TENDER_DOC_EXTS


def _valid_project(db, project_id: int | None):
    """关联项目必须存在且不在回收站。"""
    if project_id is None:
        return True
    p = db.get(TenderProject, project_id)
    return bool(p and p.deleted_at is None)


def _to_out(doc: DocumentFile) -> dict:
    data = DocumentOut.model_validate(doc).model_dump()
    data["project_name"] = doc.project.name if doc.project else None
    return data


@router.get("")
def list_documents(project_id: int | None = None, status: str = "", keyword: str = "",
                   db: Session = Depends(get_db)):
    q = db.query(DocumentFile)
    if project_id:
        q = q.filter(DocumentFile.project_id == project_id)
    if status:
        q = q.filter(DocumentFile.status == status)
    if keyword:
        q = q.filter(DocumentFile.original_name.contains(keyword))
    docs = q.order_by(DocumentFile.uploaded_at.desc()).all()
    return [_to_out(d) for d in docs]


PACKAGE_EXTS = {".pdf", ".docx", ".doc", ".xls", ".xlsx"}
MAIN_FILE_HINT = "招标文件"


@router.post("/import-package")
async def import_package(
    file: UploadFile = File(...),
    project_id: int | None = Form(None),
    db: Session = Depends(get_db),
):
    """导入深圳交易平台招标文件包（.zip 封装，内含 Project.xml + File.zip）或普通 zip。

    - 原件不动：仅在临时目录解包读取，业务文件存入 uploads/tender-docs/；
    - 记录原始 zip 的 SHA-256（source_sha256），导入后可验证原件未被修改；
    - zip 内业务文件按扩展名白名单过滤；包内所有文件归入同一 package_id。
    """
    import time as _time

    if project_id and not _valid_project(db, project_id):
        raise HTTPException(400, "关联项目不存在或已在回收站")
    original = sanitize_filename(file.filename or "")
    if not original.lower().endswith(".zip"):
        raise HTTPException(400, "请上传 .zip 格式的招标文件交易包")

    limit_mb = get_max_size_mb(db)
    save_dir = UPLOAD_DIR / "tender-docs"
    save_dir.mkdir(parents=True, exist_ok=True)
    tmp_zip = save_dir / f"pkg_{_time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}.zip.tmp"
    h = hashlib.sha256()
    size = 0
    try:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > limit_mb * 1024 * 1024:
                raise HTTPException(400, f"文件超过大小限制（{limit_mb} MB）")
            h.update(chunk)
            tmp_zip.open("ab").write(chunk)
        if size == 0:
            raise HTTPException(400, "上传内容为空文件")
        source_sha = h.hexdigest()

        if not zipfile.is_zipfile(tmp_zip):
            raise HTTPException(400, "不是有效的 zip 文件（可能已损坏）")

        package_id = uuid.uuid4().hex[:10]
        created: list[dict] = []
        outer = zipfile.ZipFile(tmp_zip)
        try:
            # 兼容两种结构：A. 交易平台封装（Project.xml + File.zip）；B. 普通 zip
            names = outer.namelist()
            meta = {}
            if "Project.xml" in names and "File.zip" in names:
                try:
                    import xml.etree.ElementTree as ET
                    root = ET.fromstring(outer.read("Project.xml").decode("utf-8", errors="replace"))

                    def _text(tag):
                        el = root.find(tag)
                        return (el.text or "").strip() if el is not None and el.text else ""
                    meta = {
                        "项目名称": _text("招标项目名称"),
                        "项目编号": _text("招标项目编号"),
                        "招标人": _text("招标人"),
                        "招标代理": _text("招标代理"),
                    }
                except Exception:
                    meta = {}
                inner_path = save_dir / f"{tmp_zip.stem}_inner.zip"
                inner_path.write_bytes(outer.read("File.zip"))
                outer.close()
                source = zipfile.ZipFile(inner_path)
            else:
                inner_path = None
                source = outer
            try:
                for info in source.infolist():
                    if info.is_dir():
                        continue
                    rel = info.filename.replace("\\", "/")
                    ext = Path(rel).suffix.lower()
                    if ext not in PACKAGE_EXTS:
                        continue
                    flat_name = sanitize_filename(rel.replace("/", "_").replace("\\", "_"))
                    stored_name = f"{package_id}_{uuid.uuid4().hex[:6]}_{flat_name}"
                    dest = save_dir / stored_name
                    with source.open(info) as src, open(dest, "wb") as out:
                        while True:
                            buf = src.read(1024 * 1024)
                            if not buf:
                                break
                            out.write(buf)
                    doc = DocumentFile(
                        original_name=rel[:280], stored_name=stored_name, file_type=ext.lstrip("."),
                        size=info.file_size, project_id=project_id, status="待解析",
                        source_sha256=source_sha, package_id=package_id)
                    db.add(doc)
                    db.flush()
                    created.append({"id": doc.id, "name": rel, "size": info.file_size,
                                    "is_main": bool(MAIN_FILE_HINT in rel and ext == ".pdf"),
                                    "parse_supported": ext in {".pdf", ".docx", ".xlsx"}})
            finally:
                source.close()
                if inner_path and inner_path.exists():
                    inner_path.unlink(missing_ok=True)
        finally:
            try:
                outer.close()  # 幂等：重复关闭安全
            except Exception:
                pass
        if not created:
            raise HTTPException(400, "zip 包内未找到可导入的业务文件（pdf/docx/xlsx）")
        db.add(ActivityLog(kind="upload", target="document", target_id=created[0]["id"],
                           title=f"交易包导入 {original}（{len(created)} 个文件）"))
        db.commit()
        main_file = next((c for c in created if c["is_main"]), created[0])
        return {"ok": True, "package_id": package_id, "source_sha256": source_sha,
                "files": created, "main_file": main_file, "meta": meta,
                "message": f"已导入 {len(created)} 个文件，主文件：{main_file['name']}"}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(400, f"交易包解析失败：{exc}")
    finally:
        tmp_zip.unlink(missing_ok=True)
        for leftover in save_dir.glob("pkg_*_inner.zip"):
            leftover.unlink(missing_ok=True)


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    project_id: int | None = Form(None),
    db: Session = Depends(get_db),
):
    """整改 B3：分块写入 + 大小限制（读系统设置）+ 魔数校验 + 路径安全。"""
    if project_id and not _valid_project(db, project_id):
        raise HTTPException(400, "关联项目不存在或已在回收站")

    stored = await save_upload(file, "tender-docs", db, allowed_exts=TENDER_DOC_EXTS)

    doc = DocumentFile(
        original_name=stored.original_name,
        stored_name=stored.stored_name,
        file_type=stored.ext,
        size=stored.size,
        project_id=project_id,
        status="待解析",
    )
    db.add(doc)
    db.flush()
    db.add(ActivityLog(kind="upload", target="document", target_id=doc.id, title=stored.original_name))
    try:
        db.commit()
    except Exception:
        db.rollback()
        stored.path.unlink(missing_ok=True)  # 元数据与磁盘保持一致
        raise HTTPException(500, "文件记录保存失败，已回滚本次上传")
    db.refresh(doc)
    return _to_out(doc)


@router.post("/{doc_id}/parse")
def parse_document(doc_id: int, background: BackgroundTasks, db: Session = Depends(get_db)):
    """触发解析。真实文件 → 第二阶段解析引擎（后台任务）；演示记录 → 演示结果（明确标注）。"""
    doc = db.get(DocumentFile, doc_id)
    if not doc:
        raise HTTPException(404, "文件不存在")

    if doc.is_demo:
        result = {
            "is_demo": True,
            "note": "演示解析结果：该记录为演示数据，未接入真实文档解析服务。",
            "sections": doc.parse_result and json.loads(doc.parse_result).get("sections", []) or [],
        }
        return {"ok": True, "status": doc.status, "result": result}

    # 真实文件 → 解析引擎（后台执行，前端轮询任务状态）
    from routers.parse import run_parse_task, start_parse
    task = start_parse(doc_id, db)
    background.add_task(lambda: threading.Thread(target=run_parse_task, args=(task.id,), daemon=True).start())
    return {"ok": True, "status": "running", "task_id": task.id, "version": task.version,
            "message": f"解析任务 V{task.version} 已启动（真实引擎），完成后在解析工作台查看",
            "workbench_url": f"/documents/{doc_id}/parse"}


@router.put("/{doc_id}", response_model=DocumentOut)
def update_document(doc_id: int, payload: DocumentUpdate, db: Session = Depends(get_db)):
    doc = db.get(DocumentFile, doc_id)
    if not doc:
        raise HTTPException(404, "文件不存在")
    if payload.project_id is not None and not _valid_project(db, payload.project_id):
        raise HTTPException(400, "关联项目不存在或已在回收站")
    doc.project_id = payload.project_id
    db.commit()
    db.refresh(doc)
    return doc


@router.delete("/{doc_id}")
def delete_document(doc_id: int, db: Session = Depends(get_db)):
    doc = db.get(DocumentFile, doc_id)
    if not doc:
        raise HTTPException(404, "文件不存在")
    # 整改 C1：先解除投标要求的文件引用（保留要求本身与已录入的原文片段）
    from models import (BidRequirement, DocumentParseResult, DocumentParseTask)
    refs = db.query(BidRequirement).filter(BidRequirement.document_id == doc_id).count()
    if refs:
        db.query(BidRequirement).filter(BidRequirement.document_id == doc_id).update(
            {BidRequirement.document_id: None}, synchronize_session="fetch")
    # 第二阶段：清理解析结果与任务记录（先结果后任务）
    db.query(DocumentParseResult).filter(DocumentParseResult.document_id == doc_id).delete(
        synchronize_session="fetch")
    db.query(DocumentParseTask).filter(DocumentParseTask.document_id == doc_id).delete(
        synchronize_session="fetch")
    if doc.stored_name:
        p = UPLOAD_DIR / "tender-docs" / doc.stored_name
        if p.exists():
            p.unlink()
    db.delete(doc)
    db.commit()
    return {"ok": True, "detached_requirements": refs}


@router.get("/{doc_id}/download")
def download_document(doc_id: int, db: Session = Depends(get_db)):
    doc = db.get(DocumentFile, doc_id)
    if not doc:
        raise HTTPException(404, "文件不存在")
    if doc.is_demo or not doc.stored_name:
        raise HTTPException(400, "演示记录没有实际文件，无法下载")
    p = UPLOAD_DIR / "tender-docs" / doc.stored_name
    if not p.exists():
        raise HTTPException(404, "文件已不存在")
    from fastapi.responses import FileResponse
    return FileResponse(p, filename=doc.original_name)
