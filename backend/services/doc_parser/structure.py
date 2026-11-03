# -*- coding: utf-8 -*-
"""章节层级识别（PDF 文本流）。

层级约定（建设工程招标文件惯例）：
  1 = 第X章            2 = 第X节 / 一、二、…
  3 = （一）（二）…      4 = 1.1 / 3.2 等编号条
保守策略：行独立、较短、无句读（。；），宁可漏判不可误判；
第X章 标题为空时取下一非空短行（跨行标题）。
"""
import re

from .models import Chapter, ParsedDocument

CH_CHAPTER = re.compile(r"^第\s*([一二三四五六七八九十百\d]+)\s*章\s*(.*)$")
CH_SECTION = re.compile(r"^第\s*([一二三四五六七八九十\d]+)\s*节\s*(.*)$")
CH_CN_LIST = re.compile(r"^([一二三四五六七八九十]+)、\s*(.*)$")
CH_PAREN = re.compile(r"^[（(]([一二三四五六七八九十]+)[）)]\s*(.*)$")
CH_NUM = re.compile(r"^(\d+(?:\.\d+){0,2})\s*[、.．]?\s*(.*)$")

MAX_TITLE_LEN = 50
_SENTENCE_STOP = ("。", "；", "，", "：：")


def _clean_heading(line: str) -> bool:
    """标题行守卫：短、非句读结尾（允许以“：”结尾）。"""
    if not (0 < len(line) <= MAX_TITLE_LEN):
        return False
    if line.rstrip("：:") == "":
        return False
    body = line.rstrip("：:")
    return not any(ch in body for ch in _SENTENCE_STOP)


def _page_lines(parsed: ParsedDocument) -> list[tuple[int, str]]:
    out = []
    for p in parsed.pages:
        for raw in p.text.split("\n"):
            s = raw.replace("　", " ").strip()
            if s:
                out.append((p.index, s))
    return out


def detect_chapters(parsed: ParsedDocument) -> ParsedDocument:
    lines = _page_lines(parsed)
    chapters: list[Chapter] = []
    n = len(lines)
    for i in range(n):
        page, line = lines[i]
        m = CH_CHAPTER.match(line)
        if m and _clean_heading(line):
            title = m.group(2).strip()
            if not title and i + 1 < n and lines[i + 1][0] == page \
                    and _clean_heading(lines[i + 1][1]) and not CH_CHAPTER.match(lines[i + 1][1]):
                title = lines[i + 1][1][:50]
            chapters.append(Chapter(level=1, number=f"第{m.group(1)}章", title=title[:50],
                                    start_page=page, full_title=line[:100]))
            continue
        m = CH_SECTION.match(line)
        if m and _clean_heading(line):
            chapters.append(Chapter(level=2, number=f"第{m.group(1)}节",
                                    title=(m.group(2) or "").strip()[:50],
                                    start_page=page, full_title=line[:100]))
            continue
        m = CH_CN_LIST.match(line)
        if m and _clean_heading(line) and len(m.group(2) or "") >= 2:
            chapters.append(Chapter(level=2, number=f"{m.group(1)}、", title=m.group(2)[:50],
                                    start_page=page, full_title=line[:100]))
            continue
        m = CH_PAREN.match(line)
        if m and _clean_heading(line) and len(m.group(2) or "") >= 2:
            chapters.append(Chapter(level=3, number=f"（{m.group(1)}）", title=m.group(2)[:50],
                                    start_page=page, full_title=line[:100]))
            continue
        m = CH_NUM.match(line)
        if m and _clean_heading(line) and len(m.group(2) or "") >= 4:
            chapters.append(Chapter(level=4, number=m.group(1), title=m.group(2)[:50],
                                    start_page=page, full_title=line[:100]))

    for i, ch in enumerate(chapters):
        for nxt in chapters[i + 1:]:
            if nxt.level <= ch.level:
                ch.end_page = max(ch.start_page, nxt.start_page - 1)
                break
        if ch.end_page is None:
            ch.end_page = parsed.page_count

    stack: list[Chapter] = []
    for ch in chapters:
        while stack and stack[-1].level >= ch.level:
            stack.pop()
        ch.full_title = " > ".join([*(f"{p.number}{p.title}" for p in stack),
                                    f"{ch.number}{ch.title}"])[:160]
        stack.append(ch)

    parsed.chapters = chapters
    return parsed


def find_chapter_range(parsed: ParsedDocument, keywords: tuple[str, ...],
                       min_level: int = 1) -> tuple[int, int] | None:
    """按标题关键词定位章节页码区间（取第一个命中）。"""
    ranges = find_chapter_ranges(parsed, keywords, min_level)
    return ranges[0] if ranges else None


def find_chapter_ranges(parsed: ParsedDocument, keywords: tuple[str, ...],
                        min_level: int = 1) -> list[tuple[int, int]]:
    """所有命中关键词的章/节区间（可重叠，供提取器合并使用）。"""
    out = []
    for ch in parsed.chapters:
        if ch.level > min_level + 1:
            continue
        head = (ch.number + ch.title)[:32]
        if any(k in head for k in keywords):
            out.append((ch.start_page, ch.end_page or parsed.page_count))
    return out
