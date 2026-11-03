# -*- coding: utf-8 -*-
"""PDF 解析器（PyMuPDF）：逐页文本、表格、扫描页检测、印刷页码识别。

- 页序号：PyMuPDF 0-based → 统一转 1-based（与 PDF 阅读器一致）；
- 印刷页码：识别页脚“第X页”“- X -”“X/Y”等模式，识别不到为 None；
- 扫描页：文本 <10 字符且含图片 → is_image_only（OCR 未接入时如实标注）；
- 大文件安全：逐页惰性处理，不整档拼接大字符串（full_text 按需由调用方拼）。
"""
import re
from pathlib import Path

import pymupdf

from .models import PageContent, ParsedDocument, TableData

# 印刷页码（页脚）模式
_LABEL_PATTERNS = [
    re.compile(r"第\s*(\d{1,4})\s*页(?:\s*[,，/]?\s*共\s*\d+\s*页)?\s*$"),
    re.compile(r"[-—–]\s*(\d{1,4})\s*[-—–]\s*$"),
    re.compile(r"(\d{1,4})\s*/\s*\d{1,4}\s*$"),
]


def detect_page_label(page_text: str) -> str | None:
    """从页面文本的末尾几行识别印刷页码。"""
    tail_lines = [ln.strip() for ln in page_text.split("\n") if ln.strip()][-4:]
    for ln in reversed(tail_lines):
        for pat in _LABEL_PATTERNS:
            m = pat.search(ln)
            if m:
                return m.group(1)
    return None


def extract_page_tables(page: "pymupdf.Page") -> list[list[str]]:
    """提取页面表格（PyMuPDF 内置表格识别）。"""
    try:
        tabs = page.find_tables()
        rows_all: list[list[str]] = []
        for t in tabs.tables:
            for row in t.extract():
                cells = [(c or "").replace("\n", " ").strip() for c in row]
                if any(cells):
                    rows_all.append(cells)
        return rows_all
    except Exception:
        return []


def parse_pdf(path: str | Path, max_pages: int = 0, want_tables: bool = False) -> ParsedDocument:
    """第一阶段：逐页文本（快）。表格用 extract_tables_selected 定向提取。"""
    doc = pymupdf.open(str(path))
    result = ParsedDocument(source_path=str(path), file_type="pdf", parser=f"PyMuPDF {pymupdf.__version__}")
    result.encrypted = doc.is_encrypted
    if doc.is_encrypted:
        result.warnings.append("PDF 已加密，无法提取内容")
        doc.close()
        return result

    limit = doc.page_count if max_pages <= 0 else min(max_pages, doc.page_count)
    for i in range(limit):
        page = doc[i]
        text = page.get_text("text")
        stripped = text.strip()
        has_image = bool(page.get_images(full=True))
        pc = PageContent(
            index=i + 1,
            text=text,
            char_count=len(stripped),
            is_image_only=(len(stripped) < 10 and has_image),
            page_label=detect_page_label(text),
        )
        if pc.is_image_only:
            result.image_pages.append(pc.index)
        result.pages.append(pc)

    if result.image_pages:
        result.warnings.append(
            f"{len(result.image_pages)} 页疑似扫描/图片页（无文本层）："
            f"{result.image_pages[:20]}{'…' if len(result.image_pages) > 20 else ''}；OCR 未接入，暂不提取这些页面")
    zero_text = sum(1 for p in result.pages if p.char_count == 0 and not p.is_image_only)
    if zero_text:
        result.warnings.append(f"{zero_text} 页完全空白")
    doc.close()
    return result


def extract_tables_selected(path: str | Path, pages: set[int]) -> list[TableData]:
    """第二阶段：仅对指定页做表格识别（性能优化：避免全文档扫描）。"""
    if not pages:
        return []
    out: list[TableData] = []
    doc = pymupdf.open(str(path))
    try:
        for idx in sorted(p for p in pages if 1 <= p <= doc.page_count):
            page = doc[idx - 1]
            rows = extract_page_tables(page)
            if not rows:
                continue
            header = ""
            for ln in reversed([l.strip() for l in page.get_text().split("\n") if l.strip()][:6]):
                if 2 < len(ln) < 50:
                    header = ln
                    break
            out.append(TableData(page_index=idx, header=header, rows=rows))
    finally:
        doc.close()
    return out
