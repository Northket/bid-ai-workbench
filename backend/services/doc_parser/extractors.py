# -*- coding: utf-8 -*-
"""招标文件七大类结构化规则提取器。

原则：
- 只提取原文可支撑的内容，原文整行保留，页码（PDF页序+印刷页码）与章节随行；
- 提取不到 → 不产出条目（前端显示“未提取到”，不猜不编）；
- confidence: high=章节范围内命中 / medium=全文关键词命中；
- 示例行（“例：”“如果”等计价说明）不作为时间节点/关键条款。
"""
import re
from datetime import datetime

from .models import ExtractItem, ParsedDocument
from .structure import find_chapter_ranges

# ---------- 通用正则 ----------
DATE_RE = re.compile(r"(20\d{2})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日")
TIME_RE = re.compile(r"(\d{1,2})\s*[:：]\s*(\d{2})|(\d{1,2})\s*[时点]\s*(\d{1,2})\s*分?")


def _match_time(line: str) -> str | None:
    m = TIME_RE.search(line)
    if not m:
        return None
    if m.group(1) is not None:
        return f"{int(m.group(1)):02d}:{m.group(2)}"
    return f"{int(m.group(3)):02d}:{int(m.group(4)):02d}"
SCORE_RE = re.compile(r"[（(]\s*(\d+(?:\.\d+)?)\s*分\s*[)）]|(?<![\d.])(\d+(?:\.\d+)?)\s*分(?![之秒时])")
LABEL_VALUE = re.compile(r"^([\u4e00-\u9fa5A-Za-z0-9（）()、，,／/·\s]{2,28}?)\s*[：:]\s*(.*)$")
EXAMPLE_MARK = re.compile(r"例[如：:]|示例|假如|如果是\d|假定")


def _mk(parsed, category, key, name, value, page, original, confidence="medium",
        method="rule", section_no="") -> ExtractItem:
    pl = parsed.pages[page - 1].page_label if 1 <= page <= parsed.page_count else None
    return ExtractItem(category=category, field_key=key, field_name=name,
                       value=value.strip()[:600], original_text=original.strip()[:900],
                       pdf_page=page, page_label=pl,
                       chapter=parsed.chapter_at(page), section_no=section_no,
                       method=method, source_layer="pdf_text", confidence=confidence)


def _dedupe(items: list[ExtractItem]) -> list[ExtractItem]:
    seen: set[tuple] = set()
    out = []
    for it in items:
        sig = (it.category, it.field_key, it.value[:80], it.pdf_page)
        if sig not in seen:
            seen.add(sig)
            out.append(it)
    return out


def _lines_in_ranges(parsed, keyword_groups: tuple[tuple[str, ...], ...],
                     extra_pages: int = 0):
    """在多组关键词命中的章节区间内迭代 (页, 行)。"""
    ranges = []
    for kws in keyword_groups:
        ranges.extend(find_chapter_ranges(parsed, kws))
    if not ranges and extra_pages:
        ranges = [(1, extra_pages)]
    lines = parsed.lines_with_page()
    if not ranges:
        yield from lines
        return
    for page, line in lines:
        if any(a <= page <= b for a, b in ranges):
            yield page, line


def _section_no_of(line: str) -> str:
    m = re.match(r"^(\d+(?:\.\d+){0,3})[、.．]?\s*", line)
    return m.group(1) if m else ""


# ================= 1. 项目基本信息 =================
BASIC_FIELDS = [
    ("标段编号", "标段编号", "标段编号"),
    ("项目编号", "项目编号", "项目编号"),
    ("招标项目编号", "招标项目编号", "招标项目编号"),
    ("项目名称", "项目名称", "项目名称"),
    ("标段名称", "标段名称", "标段名称"),
    ("工程名称", "工程名称", "工程名称"),
    ("招标人", "招标人", "招标人"),
    ("招标代理机构", "招标代理机构", "招标代理机构"),
    ("建设地点", "项目地址", "建设地点"),
    ("项目地址", "项目地址", "项目地址"),
    ("工程地址", "项目地址", "工程地址"),
    ("建设规模", "建设规模", "建设规模"),
    ("招标范围", "招标范围", "招标范围"),
    ("资金来源", "资金来源", "资金来源"),
    ("最高投标限价", "最高投标限价", "最高投标限价"),
    ("最高限价", "最高投标限价", "最高限价"),
    ("计划工期", "计划工期", "计划工期"),
    ("工期要求", "计划工期", "工期要求"),
    ("质量标准", "质量标准", "质量标准"),
    ("质量要求", "质量标准", "质量要求"),
    ("联系人", "项目联系人", "联系人"),
    ("联系电话", "联系方式", "联系电话"),
]


def extract_basic(parsed: ParsedDocument) -> list[ExtractItem]:
    """封面与公告/须知前附表中的“字段：值”。
    覆盖三种布局：同行“标签：值”；封面“标签：”+值在下一行；前附表纯标签行+下一行值。
    """
    head = list()
    for page, line in parsed.lines_with_page():
        if page > 30:
            break
        head.append((page, line))
    rngs = find_chapter_ranges(parsed, ("招标公告", "投标邀请书"))
    hits: dict[str, ExtractItem] = {}
    n = len(head)

    def match_label(label_norm: str):
        for kw, key, name in BASIC_FIELDS:
            ln = label_norm.rstrip("为是")
            if ln == kw or (ln.endswith(kw) and len(ln) <= len(kw) + 3):
                return kw, key, name
        return None

    for i, (page, line) in enumerate(head):
        m = LABEL_VALUE.match(line)
        label_norm = re.sub(r"\s+", "", m.group(1)) if m else None
        value = (m.group(2).strip() if m else "").strip()
        display = line
        if m and not value:
            # 封面跨行值
            if i + 1 < n and head[i + 1][0] == page and not LABEL_VALUE.match(head[i + 1][1]):
                value = head[i + 1][1]
        if not label_norm or not value or len(value) < 2:
            # 前附表纯标签行（无冒号，短）→ 值在下一行
            if not m and 2 <= len(line) <= 8 and i + 1 < n and head[i + 1][0] == page:
                hit = match_label(re.sub(r"\s+", "", line))
                if hit:
                    kw, key, name = hit
                    value = head[i + 1][1]
                    if value and not LABEL_VALUE.match(value) and len(value) >= 2 and key not in hits:
                        conf = "high" if rngs and any(a <= page <= b for a, b in rngs) else "medium"
                        hits[key] = _mk(parsed, "basic", key, name, value, page,
                                        f"{line} / {value}", conf)
            continue
        if LABEL_VALUE.match(value):  # 值本身又是“字段：”，跳过
            continue
        hit = match_label(label_norm)
        if hit:
            kw, key, name = hit
            conf = "high" if rngs and any(a <= page <= b for a, b in rngs) else "medium"
            if key not in hits:
                hits[key] = _mk(parsed, "basic", key, name, value, page,
                                display if value in display else f"{m.group(1).strip()}：{value}",
                                conf)
    return list(hits.values())


# ================= 2. 关键时间节点 =================
TIMELINE_RULES = [
    ("deadline", "投标文件递交截止时间", ("递交截止", "投标截止", "提交投标文件截止", "截止时间")),
    ("open_bid", "开标时间", ("开标",)),
    ("answer", "答疑时间", ("答疑",)),
    ("question", "提问/质疑截止", ("提问截止", "质疑截止", "疑问截止")),
    ("clarify", "澄清文件发布", ("澄清",)),
    ("deposit", "投标保证金提交截止", ("保证金",)),
    ("obtain", "招标文件获取时间", ("获取招标文件", "招标文件获取", "领取招标文件")),
    ("site", "现场踏勘", ("踏勘",)),
]


def extract_timeline(parsed: ParsedDocument) -> list[ExtractItem]:
    items = []
    noted_undated: set[str] = set()
    for page, line in _lines_in_ranges(parsed, (("招标公告",), ("投标邀请书",), ("投标须知",))):
        for key, name, kws in TIMELINE_RULES:
            if not any(k in line for k in kws):
                continue
            if EXAMPLE_MARK.search(line):
                break
            d = DATE_RE.search(line)
            if not d:
                # 原文提到该节点但未载明具体日期 → 如实标注“未明确”，不猜
                if key not in noted_undated and len(line) <= 120:
                    noted_undated.add(key)
                    items.append(_mk(parsed, "timeline", key, name,
                                     "未明确（原文未载明具体日期，待人工确认）",
                                     page, line, confidence="low",
                                     section_no=_section_no_of(line)))
                break
            t = _match_time(line)
            try:
                dt = datetime(int(d.group(1)), int(d.group(2)), int(d.group(3)))
                value = dt.strftime("%Y-%m-%d") + (f" {t}" if t else "")
            except ValueError:
                break
            items.append(_mk(parsed, "timeline", key, name, value, page, line,
                             confidence="high", section_no=_section_no_of(line)))
            break
    # 同一 key 既有“未明确”又有具体日期时，删除模糊条目
    dated_keys = {i.field_key for i in items if i.confidence != "low"}
    return _dedupe([i for i in items if i.field_key not in dated_keys or i.confidence != "low"])


# ================= 3. 投标人资格条件 =================
QUAL_RULES = [
    ("qualification_cert", "企业资质要求", (r"资质等级", r"资质要求", r"具备.{0,12}资质", r"施工总承包", r"专业承包")),
    ("safety_license", "安全生产许可证", (r"安全生产许可证",)),
    ("company_performance", "企业业绩要求", (r"企业业绩", r"类似工程业绩", r"业绩要求")),
    ("manager_cert", "项目负责人资格", (r"项目负责人.{0,20}(资格|注册|建造师)", r"项目经理.{0,20}(资格|注册|建造师)", r"注册建造师")),
    ("manager_performance", "项目负责人业绩", (r"项目负责人.{0,12}业绩", r"项目经理.{0,12}业绩")),
    ("team", "项目管理人员要求", (r"项目管理人员", r"技术负责人", r"专职安全员", r"施工员", r"质量员")),
    ("consortium", "联合体投标要求", (r"联合体",)),
    ("finance_credit", "财务/信用要求", (r"财务状况", r"审计报告", r"信用.{0,6}(状况|要求|记录)", r"失信")),
    ("review_method", "资格审查方式", (r"资格审查方式", r"资格后审", r"资格预审")),
]


def extract_qualification(parsed: ParsedDocument) -> list[ExtractItem]:
    items = []
    for page, line in _lines_in_ranges(parsed, (("资格审查",), ("投标须知",), ("招标公告",))):
        if len(line) > 200:
            continue
        for key, name, kws in QUAL_RULES:
            if any(re.search(k, line) for k in kws):
                items.append(_mk(parsed, "qualification", key, name, line, page, line,
                                 confidence="high", section_no=_section_no_of(line)))
                break
    return _dedupe(items)[:80]


# ================= 4. 否决投标及实质性响应条款（重点） =================
REJECTION_KEYWORDS = ("否决", "不予受理", "无效投标", "废标", "重大偏差", "实质性响应")
REJECTION_HEAD = ("否决性条款", "否决投标", "无效投标", "开标不受理", "废标条款")
HEADING_LIKE = re.compile(r"^(第[一二三四五六七八九十百\d]+[章节]|[一二三四五六七八九十]+、|[（(][一二三四五六七八九十]+[）)]|\d+\.\d+)\s*[^。；]{0,28}$")


def _clean_cell_text(c: str) -> str:
    """单元格内清洗：换行归一、去孤立残点（表格线痕迹）、去前导重复序号。"""
    c = (c or "").replace("\n", " ").strip()
    c = " ".join(tok for tok in c.split() if tok not in {".", "。"})
    c = re.sub(r"^(\d+(?:\.\d+)*)\s+\1(?=\s|$)", r"\1", c)  # "1 1 条款…" → "1 条款…"
    return c.strip()


def _clean_table_cells(cells: list[str]) -> list[str]:
    """清洗表格单元格：去残留/相邻重复/条款内重复序号，返回拼接文本。"""
    out: list[str] = []
    for c in cells:
        c = _clean_cell_text(c)
        if not c:
            continue
        if out and c == out[-1]:
            continue
        # 序号列(纯数字) + 条款内重复该序号 → 去条款内前导序号
        if out and re.fullmatch(r"\d+(?:\.\d+)*", out[-1]):
            c = re.sub(rf"^{re.escape(out[-1])}\s+", "", c) or c
        out.append(c)
    return out


def _rejection_from_tables(parsed: ParsedDocument) -> list[ExtractItem]:
    """否决性条款表格（附表/正文中的序号-条款表）。"""
    items = []
    for tbl in parsed.tables:
        head = ((tbl.header or "") + " " + " ".join(tbl.rows[0] if tbl.rows else [])).strip()
        if not any(k in head for k in REJECTION_HEAD):
            continue
        for row in tbl.rows[1:]:
            raw_cells = [c for c in row if c]
            cells = _clean_table_cells(raw_cells)
            if not cells or sum(len(c) for c in cells) < 6:
                continue
            text = " ".join(cells)
            if any(k in text for k in REJECTION_KEYWORDS) or re.match(r"^\d+", cells[0]):
                sec = cells[0].strip()[:10] if re.match(r"^[\d.]+", cells[0].strip()) else ""
                items.append(_mk(parsed, "rejection", "rejection_clause", "否决性条款",
                                 text, tbl.page_index, text, confidence="high", section_no=sec))
    return items


def extract_rejection(parsed: ParsedDocument) -> list[ExtractItem]:
    items = _rejection_from_tables(parsed)
    seen_text = {i.original_text[:60] for i in items}
    # 章节内条款行（排除提示语与标题行）
    for page, line in _lines_in_ranges(parsed, (("否决性条款",), ("否决投标",), ("无效投标",), ("开标不受理",))):
        if not (8 < len(line) <= 200):
            continue
        if line.startswith("【提示") or HEADING_LIKE.match(line):
            continue
        if line[:60] in seen_text:
            continue
        seen_text.add(line[:60])
        items.append(_mk(parsed, "rejection", "rejection_clause", "否决/无效投标情形",
                         line, page, line, confidence="high", section_no=_section_no_of(line)))
    # 全文兜底（限量）
    if len(items) < 8:
        for page, line in parsed.lines_with_page():
            if any(k in line for k in REJECTION_KEYWORDS) and 8 < len(line) <= 160 \
                    and not line.startswith("【提示") and line[:60] not in seen_text:
                seen_text.add(line[:60])
                items.append(_mk(parsed, "rejection", "rejection_clause", "否决/无效投标情形",
                                 line, page, line, confidence="medium"))
                if len(items) >= 40:
                    break
    return _dedupe(items)[:120]


# ================= 5. 评标办法及评分标准 =================
EVAL_HEAD = ("评标办法", "评定办法", "评标方法", "定标", "评审", "评分")
EVAL_METHOD_PAT = re.compile(
    r"^(评定分离|综合评估法|经评审的最低投标价法|定性评审|定量评审|"
    r"直接票决定标法|逐轮票决定标法|集体议事定标法|票决|评审方法|评标方法|定标方法)")


def extract_evaluation(parsed: ParsedDocument) -> list[ExtractItem]:
    items = []
    # 方法/程序（评定分离类文本常见“43.1 直接票决定标法”）
    for page, line in _lines_in_ranges(parsed, EVAL_HEAD):
        m = EVAL_METHOD_PAT.search(line)
        if m:
            items.append(_mk(parsed, "evaluation", "method", "评标/定标方法",
                             line, page, line, confidence="high",
                             section_no=_section_no_of(line)))
            if sum(1 for i in items if i.field_key == "method") >= 5:
                break
    # 评分项：行内含 X 分（综合评估法类文本）
    idx = 0
    for page, line in _lines_in_ranges(parsed, EVAL_HEAD):
        for m in SCORE_RE.finditer(line):
            score = m.group(1) or m.group(2)
            name = line[:m.start()].strip(" ，,；;：:（()）") or line[:40]
            if len(name) < 2:
                continue
            idx += 1
            items.append(_mk(parsed, "evaluation", f"score_{idx}",
                             f"评分项（{score}分）", f"{name} —— {score} 分", page, line,
                             confidence="high", section_no=_section_no_of(line)))
            break
    return _dedupe(items)[:150]


# ================= 6. 技术标要求 =================
TECH_HEAD = (("技术标",), ("施工组织设计",), ("投标文件格式",), ("技术要求",))
TECH_RULES = [
    ("structure", "技术标组成/章节要求", (r"技术标.{0,6}(组成|包括|应包括|内容)", r"技术标部分")),
    ("design", "施工组织设计要求", (r"施工组织设计",)),
    ("scheme", "施工方案要求", (r"施工方案", r"专项施工", r"重点部位")),
    ("schedule", "进度计划要求", (r"进度计划", r"工期.{0,4}计划", r"总工期", r"网络图", r"横道图")),
    ("quality", "质量管理要求", (r"质量.{0,6}(措施|保证|管理)",)),
    ("safety", "安全文明施工要求", (r"安全.{0,8}措施", r"文明施工", r"危大工程")),
    ("env", "环境保护要求", (r"环境保护", r"绿色施工", r"扬尘", r"噪声")),
    ("difficulty", "重点难点分析要求", (r"重点难点", r"重难点", r"难点分析")),
    ("bim", "BIM/智慧工地要求", (r"BIM", r"智慧工地", r"实名制", r"信息化管理")),
]


def extract_technical(parsed: ParsedDocument) -> list[ExtractItem]:
    items = []
    for page, line in _lines_in_ranges(parsed, TECH_HEAD):
        if len(line) > 220 or HEADING_LIKE.match(line) and len(line) < 12:
            continue
        for key, name, kws in TECH_RULES:
            if any(re.search(k, line, re.IGNORECASE) for k in kws):
                items.append(_mk(parsed, "technical", key, name, line, page, line,
                                 confidence="high", section_no=_section_no_of(line)))
                break
    return _dedupe(items)[:100]


# ================= 7. 商务标及资信标要求 =================
COM_HEAD = (("商务标",), ("投标报价",), ("工程量清单",), ("资信标",), ("投标须知",))
COM_RULES = [
    ("price_scope", "投标报价组成", (r"投标报价.{0,6}组成", r"报价.{0,4}(包括|范围)", r"报价范围")),
    ("price_method", "报价方式", (r"报价方式", r"固定单价", r"固定总价", r"综合单价")),
    ("bill", "工程量清单要求", (r"工程量清单", r"暂列金额", r"暂估价", r"计日工")),
    ("basis", "计价依据", (r"计价依据", r"计价标准", r"信息价", r"定额")),
    ("price_limit", "投标报价限制", (r"最高投标限价", r"不得高于", r"低于成本")),
    ("cert_company", "企业资质证明材料", (r"资质证书", r"营业执照", r"安全生产许可证")),
    ("cert_performance", "企业业绩证明材料", (r"业绩.{0,8}证明", r"中标通知书", r"竣工验收")),
    ("cert_staff", "人员证明材料", (r"建造师.{0,8}证书", r"职称证", r"社保证明", r"劳动合同")),
    ("cert_finance", "财务/信用证明材料", (r"财务报表", r"审计报告", r"信用.{0,6}报告", r"失信.{0,8}查询")),
]


def extract_commercial(parsed: ParsedDocument) -> list[ExtractItem]:
    items = []
    for page, line in _lines_in_ranges(parsed, COM_HEAD):
        if len(line) > 220:
            continue
        for key, name, kws in COM_RULES:
            if any(re.search(k, line) for k in kws):
                items.append(_mk(parsed, "commercial", key, name, line, page, line,
                                 confidence="high", section_no=_section_no_of(line)))
                break
    return _dedupe(items)[:100]
