# -*- coding: utf-8 -*-
"""DOCX / XLSX 解析器。

DOCX：python-docx 提取段落（保留 Heading 样式）与表格；
     无固定分页 → 页码记 None，条目定位改用“段落序号”（anchor=para:N）。
XLSX：openpyxl 按 sheet 汇总（前若干行），供清单类附件概览。
DOC/XLS（97-2003）：明确不支持，返回错误提示（可后续接 LibreOffice 转换）。
"""
from pathlib import Path

from .models import Chapter, PageContent, ParsedDocument, TableData

SUPPORTED_DOCX = ".docx"
SUPPORTED_XLSX = ".xlsx"


def parse_docx(path: str | Path) -> ParsedDocument:
    import docx  # python-docx

    d = docx.Document(str(path))
    result = ParsedDocument(source_path=str(path), file_type="docx", parser="python-docx")
    result.warnings.append("DOCX 无固定分页，pdf_page 为空；条目以段落序号（第N段）定位")

    # 以 500 段为一“逻辑页”，便于前端分段展示
    para_idx = 0
    current_chunk: list[str] = []
    chunk_no = 0

    def flush():
        nonlocal current_chunk, chunk_no
        chunk_no += 1
        result.pages.append(PageContent(
            index=chunk_no, text="\n".join(current_chunk),
            char_count=sum(len(x) for x in current_chunk)))

    for block in d.element.body.iterchildren():
        tag = block.tag.split("}")[-1]
        if tag == "p":
            from docx.text.paragraph import Paragraph
            para = Paragraph(block, d)
            txt = (para.text or "").strip()
            para_idx += 1
            style = (para.style.name if para.style is not None else "") or ""
            if txt:
                current_chunk.append(txt)
            # Heading 样式 → 章节层级（页 = 当前逻辑块）
            if style.startswith(("Heading", "标题")) or txt.startswith("第") and "章" in txt[:8]:
                level = 1
                for ch_num in "一二三四五六七八九十":
                    if ch_num in style:
                        level = 2
                number = ""
                title = txt
                if txt.startswith("第") and "章" in txt[:8]:
                    number = txt.split("章", 1)[0] + "章"
                    title = txt.split("章", 1)[1].strip() or title
                result.chapters.append(Chapter(
                    level=level, number=number or style, title=title[:80],
                    start_page=chunk_no + 1, full_title=txt[:120]))
            if len(current_chunk) >= 500:
                flush()
                current_chunk = []
        elif tag == "tbl":
            from docx.table import Table
            tbl = Table(block, d)
            rows = [[(c.text or "").replace("\n", " ").strip() for c in r.cells] for r in tbl.rows]
            rows = [r for r in rows if any(r)]
            if rows:
                current_chunk.append(f"[表格 {len(rows)} 行] " + " | ".join(rows[0][:8]))
                result.tables.append(TableData(page_index=chunk_no + 1,
                                               header=(current_chunk[-2] if len(current_chunk) > 1 else ""),
                                               rows=rows[:200]))
    if current_chunk:
        flush()
    return result


def parse_xlsx(path: str | Path, max_rows_per_sheet: int = 50) -> ParsedDocument:
    from openpyxl import load_workbook

    wb = load_workbook(str(path), read_only=True, data_only=True)
    result = ParsedDocument(source_path=str(path), file_type="xlsx", parser="openpyxl")
    page_no = 0
    for ws in wb.worksheets:
        page_no += 1
        rows: list[list[str]] = []
        for i, row in enumerate(ws.iter_rows(values_only=True)):
            if i >= max_rows_per_sheet:
                result.warnings.append(f"工作表「{ws.title}」仅读取前 {max_rows_per_sheet} 行（共超过）")
                break
            rows.append(["" if v is None else str(v).strip() for v in row])
        text = "\n".join(" | ".join(r) for r in rows if any(r))
        result.pages.append(PageContent(index=page_no, text=text,
                                        char_count=len(text)))
        result.tables.append(TableData(page_index=page_no, header=f"工作表：{ws.title}", rows=rows))
    wb.close()
    return result


def parse_legacy_unsupported(path: str | Path) -> ParsedDocument:
    """DOC/XLS（97-2003 二进制格式）：当前明确不支持。"""
    result = ParsedDocument(source_path=str(path), file_type=Path(str(path)).suffix.lstrip("."),
                            parser="none")
    result.warnings.append("DOC/XLS（97-2003）格式暂不支持解析，请另存为 DOCX/XLSX 后重试"
                           "（后续可接入 LibreOffice 转换）")
    return result
