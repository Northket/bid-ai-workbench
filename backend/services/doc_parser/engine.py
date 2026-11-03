# -*- coding: utf-8 -*-
"""解析引擎编排：文件类型分派 → 原始解析 → 章节识别 → 定向表格 → 结构化提取 → 报告。

不猜不编：提取不到就留空并标注，原文始终保留。
两阶段设计（性能）：先全文文本+章节（秒级），再仅对业务相关章节页做表格识别。
"""
from pathlib import Path

from . import extractors
from .docx_parser import parse_docx, parse_legacy_unsupported, parse_xlsx
from .models import ExtractItem, ParsedDocument
from .pdf_parser import extract_tables_selected, parse_pdf
from .structure import detect_chapters, find_chapter_ranges

ENGINE_VERSION = "2.0.1"

# 需要表格识别的章节关键词（否决条款表/评分表/前附表等集中在这些章节）
TABLE_CHAPTER_KEYWORDS: tuple[tuple[str, ...], ...] = (
    ("否决",), ("评标",), ("评定",), ("定标",), ("评分",), ("前附表",),
    ("资格",), ("资信标",), ("技术标",), ("商务标",), ("工程量清单",), ("投标文件格式",),
)
TABLE_HEAD_PAGES = 26  # 封面/公告/须知前附表通常在前 26 页


class ParseEngineError(Exception):
    """解析失败（损坏/不支持/空文件），message 面向用户。"""


def _wanted_table_pages(parsed: ParsedDocument) -> set[int]:
    pages: set[int] = set(range(1, min(TABLE_HEAD_PAGES, parsed.page_count) + 1))
    for kws in TABLE_CHAPTER_KEYWORDS:
        for start, end in find_chapter_ranges(parsed, kws):
            pages.update(range(start, min(end, start + 60) + 1))
    return {p for p in pages if 1 <= p <= parsed.page_count}


def parse_document(path: str | Path, ext: str | None = None,
                   max_pages: int = 0, want_tables: bool = True) -> ParsedDocument:
    """按扩展名分派解析器，返回原始解析产物（含章节与定向表格）。"""
    p = Path(path)
    if not p.exists():
        raise ParseEngineError(f"文件不存在：{p}")
    suffix = (ext or p.suffix).lower().lstrip(".")
    if p.stat().st_size == 0:
        raise ParseEngineError("文件为空（0 字节），无法解析")

    if suffix == "pdf":
        parsed = parse_pdf(p, max_pages=max_pages)
        if not parsed.encrypted:
            detect_chapters(parsed)
            if want_tables and parsed.page_count:
                parsed.tables = extract_tables_selected(p, _wanted_table_pages(parsed))
    elif suffix == "docx":
        parsed = parse_docx(p)
    elif suffix == "xlsx":
        parsed = parse_xlsx(p)
    elif suffix in ("doc", "xls"):
        parsed = parse_legacy_unsupported(p)
    else:
        raise ParseEngineError(f"暂不支持解析的文件类型：.{suffix}")
    return parsed


def extract_structured(parsed: ParsedDocument) -> list[ExtractItem]:
    """在原始解析产物上执行七大类规则提取。"""
    if parsed.encrypted:
        raise ParseEngineError("PDF 已加密，无法提取内容")
    if not any(p.char_count for p in parsed.pages) and not parsed.image_pages:
        raise ParseEngineError("未提取到任何文本内容（文件可能损坏或为空）")
    if parsed.file_type in ("doc", "xls"):
        raise ParseEngineError(parsed.warnings[0] if parsed.warnings else "该格式暂不支持")
    items: list[ExtractItem] = []
    items += extractors.extract_basic(parsed)
    items += extractors.extract_timeline(parsed)
    items += extractors.extract_qualification(parsed)
    items += extractors.extract_rejection(parsed)
    items += extractors.extract_evaluation(parsed)
    items += extractors.extract_technical(parsed)
    items += extractors.extract_commercial(parsed)
    return items


def build_report(parsed: ParsedDocument, items: list[ExtractItem]) -> dict:
    """解析统计报告（任务记录用）。"""
    by_cat: dict[str, int] = {}
    for it in items:
        by_cat[it.category] = by_cat.get(it.category, 0) + 1
    label_pages = sum(1 for p in parsed.pages if p.page_label)
    return {
        "engine_version": ENGINE_VERSION,
        "parser": parsed.parser,
        "file_type": parsed.file_type,
        "page_count": parsed.page_count,
        "char_count": sum(p.char_count for p in parsed.pages),
        "chapter_count": len(parsed.chapters),
        "table_count": len(parsed.tables),
        "image_pages": parsed.image_pages,
        "page_label_detected": label_pages,
        "extracted_items": by_cat,
        "warnings": parsed.warnings,
    }
