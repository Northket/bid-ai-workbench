# -*- coding: utf-8 -*-
"""解析引擎内部数据结构（纯内存，便于独立测试）。"""
from dataclasses import dataclass, field


@dataclass
class PageContent:
    """单页内容。index 为 PDF 页序号（1 起，即阅读器页码）。"""
    index: int
    text: str
    char_count: int = 0
    is_image_only: bool = False  # 无文本层、仅图片（疑似扫描页）
    page_label: str | None = None  # 印刷页码（如"3"，识别自页脚）


@dataclass
class TableData:
    page_index: int
    header: str  # 表格前最近的标题/说明行
    rows: list[list[str]] = field(default_factory=list)

    def to_text(self) -> str:
        lines = [f"[表·第{self.page_index}页] {self.header}"] if self.header else [f"[表·第{self.page_index}页]"]
        for r in self.rows:
            lines.append(" | ".join(c.replace("\n", " ").strip() for c in r))
        return "\n".join(lines)


@dataclass
class Chapter:
    """章节树节点。"""
    level: int  # 1=章 2=节/一、 3=（一） 4=1.
    number: str  # "第二章" / "一、" / "（三）" / "3.2"
    title: str
    start_page: int
    end_page: int | None = None
    full_title: str = ""

    def as_dict(self) -> dict:
        return {"level": self.level, "number": self.number, "title": self.title,
                "full_title": self.full_title or f"{self.number}{self.title}",
                "start_page": self.start_page, "end_page": self.end_page}


@dataclass
class ParsedDocument:
    """一次解析的完整产物（原始层，不做业务推断）。"""
    source_path: str
    file_type: str
    pages: list[PageContent] = field(default_factory=list)
    chapters: list[Chapter] = field(default_factory=list)
    tables: list[TableData] = field(default_factory=list)
    parser: str = ""
    encrypted: bool = False
    image_pages: list[int] = field(default_factory=list)  # 疑似扫描页页序
    warnings: list[str] = field(default_factory=list)

    @property
    def page_count(self) -> int:
        return len(self.pages)

    def page_text(self, index: int) -> str:
        """按页序号（1 起）取文本。"""
        return self.pages[index - 1].text if 1 <= index <= len(self.pages) else ""

    def lines_with_page(self) -> list[tuple[int, str]]:
        """(页序号, 行) 顺序流，供规则提取器使用。"""
        out = []
        for p in self.pages:
            for line in p.text.split("\n"):
                s = line.strip()
                if s:
                    out.append((p.index, s))
        return out

    def chapter_at(self, page_index: int) -> str:
        """某页所属的最深层级章节全称。"""
        best = ""
        for ch in self.chapters:
            if ch.start_page <= page_index and (ch.end_page is None or page_index <= ch.end_page):
                if len(ch.full_title or f"{ch.number}{ch.title}") > len(best):
                    best = ch.full_title or f"{ch.number}{ch.title}"
        return best


@dataclass
class ExtractItem:
    """结构化提取结果（一条）。"""
    category: str  # basic/timeline/qualification/rejection/evaluation/technical/commercial
    field_key: str
    field_name: str
    value: str
    original_text: str = ""
    pdf_page: int | None = None       # PDF 页序号（阅读器页码）
    page_label: str | None = None     # 印刷页码
    chapter: str = ""
    section_no: str = ""
    method: str = "rule"              # pdf_text/ocr/rule/ai/manual
    source_layer: str = "pdf_text"    # 原文来自文本层/OCR
    confidence: str = "medium"        # high/medium/low

    def as_dict(self) -> dict:
        return self.__dict__.copy()
