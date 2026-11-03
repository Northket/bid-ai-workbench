# -*- coding: utf-8 -*-
"""安全文件存储服务（整改 B3）。

- 分块写入，不整体读入内存；
- 服务端强制大小限制（读取系统设置 storage.max_size_mb）；
- 扩展名白名单 + 魔数（文件头）双重校验，识别伪装文件；
- 原始文件名净化（防路径穿越/控制字符），存储名使用 UUID；
- 任一环节失败即清理临时文件，不留无效文件；
- 平台仅存储文件，绝不执行其中任何宏/脚本内容。
"""
import re
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from database import UPLOAD_DIR
from models import Setting

CHUNK_SIZE = 1024 * 1024  # 1MB 分块
DEFAULT_MAX_SIZE_MB = 100

# 扩展名 → (魔数列表, 类型说明)；魔数为文件头前若干字节的前缀匹配
MAGIC_RULES: dict[str, tuple[bytes, str]] = {
    ".pdf": (b"%PDF-", "PDF 文档"),
    ".docx": (b"PK\x03\x04", "Office Open XML（docx/xlsx）"),
    ".xlsx": (b"PK\x03\x04", "Office Open XML（docx/xlsx）"),
    ".doc": (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1", "Office 97-2003（doc/xls）"),
    ".xls": (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1", "Office 97-2003（doc/xls）"),
}

TENDER_DOC_EXTS = {".pdf", ".doc", ".docx", ".xls", ".xlsx"}
DELIVERABLE_EXTS = {".pdf", ".doc", ".docx", ".xls", ".xlsx"}

_UNSAFE_CHARS = re.compile(r'[\\/:*?"<>|\x00-\x1f]')


@dataclass
class StoredFile:
    stored_name: str
    original_name: str
    ext: str
    size: int
    path: Path


def sanitize_filename(name: str) -> str:
    """净化原始文件名：仅取 basename，去除危险字符与控制符，限制长度。"""
    name = (name or "未命名文件").replace("\\", "/").split("/")[-1]
    name = _UNSAFE_CHARS.sub("_", name).strip(" .") or "未命名文件"
    if len(name) > 150:
        stem, dot, ext = name.rpartition(".")
        name = (stem[:120] + ("." + ext if dot else "")) if dot else name[:150]
    return name


def get_max_size_mb(db: Session) -> int:
    """大小限制读取系统设置（默认 100MB，非法值回退默认）。"""
    try:
        row = db.query(Setting).filter(Setting.key == "storage.max_size_mb").first()
        v = int(row.value) if row and row.value else DEFAULT_MAX_SIZE_MB
        return v if v > 0 else DEFAULT_MAX_SIZE_MB
    except (ValueError, TypeError):
        return DEFAULT_MAX_SIZE_MB


def detect_real_ext(head: bytes) -> str | None:
    """根据文件头判断真实类型。"""
    for ext, (magic, _) in MAGIC_RULES.items():
        if head.startswith(magic):
            return ext
    # OLE 宏文档（带宏的 doc/xls）同样是该魔数；仅存储不执行，不额外区分
    return None


async def save_upload(
    file: UploadFile,
    subdir: str,
    db: Session,
    allowed_exts: set[str] | None = None,
    max_size_mb: int | None = None,
) -> StoredFile:
    """安全保存上传文件。任何校验失败抛出 HTTPException 并清理临时文件。"""
    allowed = allowed_exts if allowed_exts is not None else TENDER_DOC_EXTS
    limit_mb = max_size_mb if max_size_mb is not None else get_max_size_mb(db)
    limit = limit_mb * 1024 * 1024

    original = sanitize_filename(file.filename or "")
    ext = Path(original).suffix.lower()
    if ext not in allowed:
        raise HTTPException(400, f"不支持的文件类型「{ext or original}」，仅支持："
                                 + "、".join(sorted(e.lstrip('.') .upper() for e in allowed)))

    dest_dir = UPLOAD_DIR / subdir
    dest_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}{ext}"
    tmp_path = dest_dir / (stored_name + ".part")
    final_path = dest_dir / stored_name

    size = 0
    head = b""
    try:
        while True:
            chunk = await file.read(CHUNK_SIZE)
            if not chunk:
                break
            if not head:
                head = chunk[:16]
                real = detect_real_ext(head)
                if real is None:
                    raise HTTPException(
                        400, f"文件内容与扩展名不符：「{original}」的实际内容不是受支持的 "
                             f"PDF/Word/Excel 文档（魔数校验失败），可能已损坏或伪装，已拒绝上传")
                # docx/xlsx 同为 ZIP 头、doc/xls 同为 OLE 头：同族内允许互换，跨族拒绝
                if real != ext and {real, ext} not in ({".docx", ".xlsx"}, {".doc", ".xls"}):
                    raise HTTPException(
                        400, f"文件内容与扩展名不符：声明为 {ext.upper()}，实际为 {real.upper()}，已拒绝上传")
            size += len(chunk)
            if size > limit:
                raise HTTPException(400, f"文件超过大小限制（{limit_mb} MB），已拒绝上传")
            tmp_path.open("ab").write(chunk)

        if size == 0:
            raise HTTPException(400, "上传内容为空文件，已拒绝")

        tmp_path.replace(final_path)  # 校验全部通过后才落为正式文件名
        return StoredFile(stored_name=stored_name, original_name=original,
                          ext=ext.lstrip("."), size=size, path=final_path)
    except Exception:
        # 失败清理：不留无效文件
        for p in (tmp_path, final_path):
            try:
                p.unlink(missing_ok=True)
            except OSError:
                pass
        raise
