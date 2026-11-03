# -*- coding: utf-8 -*-
"""历史项目统一查询与统计服务（整改 B2）。

所有历史数据筛选、统计、下浮率计算、排名都必须通过本服务完成，
路由层（history / ai / dashboard）不得各自实现统计逻辑。

下浮率 =（招标控制价 − 中标金额）÷ 招标控制价 × 100%
有效性规则：
  - 有效样本：control > 0 且 bid > 0 且 bid <= control（口径可比较）；
  - 待核验：control > 0 且 bid > 0 但 bid > control（中标价高于控制价，价格口径存疑），
    不纳入下浮率统计；
  - 无效：bid 或 control 缺失（<=0 视为缺失），不默认为零。
所有统计函数返回 valid_sample_count，前端必须展示。
"""
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import or_
from sqlalchemy.orm import Query, Session

from models import HistoricalProject


@dataclass
class HistoryFilters:
    """与列表接口一致的筛选条件，统计口径完全跟随。"""
    keyword: str = ""
    region: str = ""
    project_type: str = ""
    date_from: date | None = None
    date_to: date | None = None
    winner: str = ""
    extra_keyword_terms: list[str] = field(default_factory=list)


def normalize_company(name: str) -> str:
    """单位名称归一化：消除全/半角、空格与常见后缀差异，用于排名聚合。"""
    if not name:
        return ""
    s = name.strip()
    for full, half in (("（", "("), ("）", ")"), ("　", " "), ("，", ",")):
        s = s.replace(full, half)
    s = "".join(s.split())  # 去所有空白
    # 常见等价后缀归一（保留原文展示，仅排名聚合用）
    if s.endswith("有限责任公司"):
        s = s[: -len("有限责任公司")] + "有限公司"
    return s


def apply_filters(db: Session, f: HistoryFilters) -> Query:
    q = db.query(HistoricalProject)
    terms = [t for t in ([f.keyword] if f.keyword else []) + f.extra_keyword_terms if t]
    for t in terms:
        like = f"%{t}%"
        q = q.filter(or_(HistoricalProject.project_name.contains(t),
                         HistoricalProject.project_code.contains(t),
                         HistoricalProject.winner.contains(t),
                         HistoricalProject.tenderer.contains(t),
                         HistoricalProject.participants.contains(t)))
    if f.region:
        q = q.filter(HistoricalProject.region == f.region)
    if f.project_type:
        q = q.filter(HistoricalProject.project_type == f.project_type)
    if f.winner:
        q = q.filter(HistoricalProject.winner.contains(f.winner))
    if f.date_from:
        q = q.filter(HistoricalProject.bid_open_date >= f.date_from)
    if f.date_to:
        q = q.filter(HistoricalProject.bid_open_date <= f.date_to)
    return q


def _discount_valid(r: HistoricalProject) -> bool:
    return r.control_amount > 0 and r.bid_amount > 0 and r.bid_amount <= r.control_amount


def _discount_pending(r: HistoricalProject) -> bool:
    return r.control_amount > 0 and r.bid_amount > 0 and r.bid_amount > r.control_amount


def compute_stats(db: Session, f: HistoryFilters, top_n: int = 5) -> dict:
    """对「应用了当前筛选」的记录集合做全量统计。"""
    rows = apply_filters(db, f).all()

    valid_amounts = [r.bid_amount for r in rows if r.bid_amount > 0]
    discounts = [(r.control_amount - r.bid_amount) / r.control_amount * 100
                 for r in rows if _discount_valid(r)]
    pending = [r for r in rows if _discount_pending(r)]
    invalid = [r for r in rows
               if not _discount_valid(r) and not _discount_pending(r)]

    def _group(key_fn):
        grouped: dict[str, list[float]] = {}
        for r in rows:
            k = key_fn(r)
            if k is None:
                continue
            grouped.setdefault(k, []).append(r.bid_amount if r.bid_amount > 0 else None)
        out = {}
        for k, vals in grouped.items():
            amounts = [v for v in vals if v is not None]
            out[k] = {"count": len(vals),
                      "avg_amount": round(sum(amounts) / len(amounts), 2) if amounts else None}
        return out

    # 单位排名：按归一化名称聚合，展示原名取出现次数最多的写法
    def _rank(get_names):
        counter: dict[str, dict] = {}
        for r in rows:
            for raw in get_names(r):
                if not raw:
                    continue
                key = normalize_company(raw)
                entry = counter.setdefault(key, {"display": raw, "count": 0, "total": 0.0})
                entry["count"] += 1
                if r.bid_amount > 0:
                    entry["total"] = round(entry["total"] + r.bid_amount, 2)
        ranked = sorted(counter.values(), key=lambda e: (-e["count"], -e["total"]))[:top_n]
        return [{"name": e["display"], "count": e["count"], "total_amount": e["total"]} for e in ranked]

    return {
        "total": len(rows),
        "filters": {"keyword": f.keyword, "region": f.region,
                    "project_type": f.project_type, "winner": f.winner,
                    "date_from": str(f.date_from or ""), "date_to": str(f.date_to or "")},
        "amount": {
            "valid_count": len(valid_amounts),
            "avg": round(sum(valid_amounts) / len(valid_amounts), 2) if valid_amounts else None,
            "max": max(valid_amounts) if valid_amounts else None,
            "min": min(valid_amounts) if valid_amounts else None,
        },
        "control": {"valid_count": sum(1 for r in rows if r.control_amount > 0)},
        "discount": {
            "valid_count": len(discounts),
            "avg": round(sum(discounts) / len(discounts), 2) if discounts else None,
            "max": round(max(discounts), 2) if discounts else None,
            "min": round(min(discounts), 2) if discounts else None,
            "pending_verification_count": len(pending),
            "pending_verification_note": (
                f"{len(pending)} 条记录中标价高于控制价，价格口径存疑，已标记待核验并排除出下浮率统计"
                if pending else ""),
            "invalid_count": len(invalid),
            "invalid_note": f"{len(invalid)} 条记录缺失中标价或控制价，不纳入下浮率统计",
        },
        "by_year": _group(lambda r: str(r.bid_open_date.year) if r.bid_open_date else None),
        "by_region": _group(lambda r: r.region or None),
        "by_type": _group(lambda r: r.project_type or None),
        "winner_ranking": _rank(lambda r: [r.winner]),
        "participant_ranking": _rank(lambda r: r.participants or []),
    }


def extract_keywords(db: Session, question: str) -> HistoryFilters:
    """从自然语言问题中提取实际存在于库中的关键词（AI 模块专用）。

    逐字符匹配会命中几乎所有记录（等于没筛），这里只提取
    真实出现的地区/工程类型/单位名/年份等词汇。
    """
    f = HistoryFilters()
    if not question:
        return f
    regions = {r.region for r in db.query(HistoricalProject.region).distinct() if r.region}
    types = {r.project_type for r in db.query(HistoricalProject.project_type).distinct() if r.project_type}
    winners = {r.winner for r in db.query(HistoricalProject.winner).distinct() if r.winner}
    for region in regions:
        if region and region in question:
            f.region = region
            break
    for t in types:
        if t and t in question:
            f.project_type = t
            break
    for w in winners:
        if w and w in question:
            f.winner = w
            break
    # 年份：4 位数字且在库内
    for tok in question.replace("年", " ").split():
        if len(tok) == 4 and tok.isdigit():
            years = {str(r.bid_open_date.year) for r in db.query(HistoricalProject).all()
                     if r.bid_open_date}
            if tok in years:
                f.date_from = date(int(tok), 1, 1)
                f.date_to = date(int(tok), 12, 31)
    # 工程主题词：问题中出现常见工程主题时，按项目名关键词过滤
    for theme in ("学校", "医院", "道路", "污水", "装修", "幕墙", "景观", "停车", "市政"):
        if theme in question:
            f.extra_keyword_terms.append(theme)
            break
    return f
