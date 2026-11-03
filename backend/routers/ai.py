"""AI 知识中心 API。

第一阶段：未接入真实大模型 API。/chat 由规则引擎基于本地数据库生成
【模拟回复】（is_mock=True，前端明确标注）。真实模型接口在设置中预留。
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import (BidRequirement, ChatMessage, ChatSession, HistoricalProject, Setting,
                    TenderProject)
from schemas import ChatMessageOut, ChatReply, ChatRequest, ChatSessionDetail, ChatSessionOut

router = APIRouter(prefix="/api/ai", tags=["ai"])

MOCK_NOTE = "（模拟回复 · 演示阶段未接入真实大模型，内容基于本地数据库规则生成）"


@router.get("/sessions", response_model=list[ChatSessionOut])
def list_sessions(db: Session = Depends(get_db)):
    return db.query(ChatSession).order_by(ChatSession.id.desc()).all()


@router.post("/sessions", response_model=ChatSessionOut)
def create_session(context_type: str = "general", context_ref: str = "",
                   title: str = "新对话", db: Session = Depends(get_db)):
    s = ChatSession(title=title, context_type=context_type, context_ref=context_ref)
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


@router.get("/sessions/{session_id}", response_model=ChatSessionDetail)
def get_session(session_id: int, db: Session = Depends(get_db)):
    s = db.get(ChatSession, session_id)
    if not s:
        raise HTTPException(404, "会话不存在")
    return s


@router.delete("/sessions/{session_id}")
def delete_session(session_id: int, db: Session = Depends(get_db)):
    s = db.get(ChatSession, session_id)
    if not s:
        raise HTTPException(404, "会话不存在")
    db.delete(s)
    db.commit()
    return {"ok": True}


@router.get("/config")
def ai_config(db: Session = Depends(get_db)):
    """模型配置状态（用于前端标注；密钥只报有无，绝不回传明文）。"""
    from routers.settings_api import effective_value

    provider = db.query(Setting).filter(Setting.key == "model.provider").first()
    return {
        "provider": provider.value if provider else "",
        "connected": False,
        "message": "演示阶段未接入真实大模型 API，请在「系统设置 → 模型配置」中预留并配置接口。",
        "has_api_key": bool(effective_value(db, "model.api_key")),
    }


# ---------------- 模拟回复规则引擎 ----------------

def _reply_for_project(db: Session, ref: str, question: str) -> str:
    q = db.query(TenderProject)
    project = q.filter(TenderProject.id == int(ref)).first() if ref.isdigit() else \
        q.filter(TenderProject.name.contains(ref)).first()
    if not project:
        return f"未在项目库中找到「{ref}」。请确认项目编号或名称后重试。" + MOCK_NOTE
    reqs = db.query(BidRequirement).filter(BidRequirement.project_id == project.id).all()
    lines = [
        f"项目「{project.name}」要点：",
        f"· 项目编号：{project.code}｜区域：{project.region}｜类型：{project.project_type}",
        f"· 招标人：{project.tenderer or '暂无'}｜代理：{project.agency or '暂无'}",
        f"· 预算/控制价：{project.budget:.0f} 万元｜投标截止：{project.deadline or '待定'}",
        f"· 当前阶段：{project.stage}",
        f"· 已登记投标要求 {len(reqs)} 项（技术/商务/资信），"
        f"其中已完成 {sum(1 for r in reqs if r.status == '已完成')} 项。",
    ]
    return "\n".join(lines) + "\n" + MOCK_NOTE


def _reply_for_history(db: Session, question: str) -> str:
    """整改 B2：复用统一统计服务，口径与历史数据库页面完全一致。"""
    from services.history_service import HistoryFilters, compute_stats, extract_keywords

    filters = extract_keywords(db, question)
    stats = compute_stats(db, filters, top_n=3)
    if stats["total"] == 0:
        return "历史项目库中没有符合当前问题范围的记录，请调整地区/类型/年份等描述后重试。" + MOCK_NOTE

    scope_desc = "、".join(v for v in [
        f"地区={filters.region}" if filters.region else "",
        f"类型={filters.project_type}" if filters.project_type else "",
        f"关键词={'/'.join(filters.extra_keyword_terms)}" if filters.extra_keyword_terms else "",
        f"年份={filters.date_from.year}" if filters.date_from else "",
    ] if v) or "全部记录"
    amount, discount = stats["amount"], stats["discount"]
    top = stats["winner_ranking"]
    lines = [
        f"基于历史项目库筛选范围（{scope_desc}，共 {stats['total']} 条记录）的统计：",
        (f"· 中标均价：{amount['avg']:.0f} 万元（有效样本 {amount['valid_count']} 条，"
         f"最高 {amount['max']:.0f} / 最低 {amount['min']:.0f} 万元）") if amount["valid_count"] else "· 暂无有效报价数据",
    ]
    if discount["valid_count"]:
        lines.append(f"· 平均下浮率：{discount['avg']:.1f}%（有效样本 {discount['valid_count']} 条，"
                     f"区间 {discount['min']:.1f}% ~ {discount['max']:.1f}%）")
        if discount["pending_verification_count"]:
            lines.append(f"· ⚠ {discount['pending_verification_note']}")
    else:
        lines.append("· 下浮率：有效样本不足（控制价与中标价需均大于 0 且口径可比）")
    if top:
        lines.append("· 中标次数最多：" + "、".join(f"{w['name']}（{w['count']}次）" for w in top))
    return "\n".join(lines) + "\n" + MOCK_NOTE


def _reply_general(db: Session, question: str) -> str:
    projects = db.query(TenderProject).count()
    hist = db.query(HistoricalProject).count()
    reqs = db.query(BidRequirement).count()
    return (
        f"收到你的问题：「{question[:60]}」\n\n"
        f"当前平台数据规模：招标项目 {projects} 个、历史中标项目 {hist} 条、投标要求 {reqs} 项。\n"
        "你可以：\n"
        "1. 在「项目问答」模式下输入项目名称，获取项目要点摘要；\n"
        "2. 切换「历史项目检索」模式，询问某类工程的中标价格水平；\n"
        "3. 切换「招标文件问答」模式，查询已解析文件的结构化结果。\n"
        + MOCK_NOTE
    )


def _reply_for_document(db: Session, ref: str, question: str) -> str:
    from models import DocumentFile
    docs = db.query(DocumentFile).all()
    done = [d for d in docs if d.status == "解析完成"]
    lines = [
        f"已解析文件 {len(done)} 份（共 {len(docs)} 份上传记录）。",
        "演示阶段解析结果包含：文件信息、占位章节结构、建议提取的投标要求条目。",
        "接入真实解析服务后，可针对文件内容回答评标办法、废标条款等问题。",
    ]
    return "\n".join(lines) + "\n" + MOCK_NOTE


@router.post("/chat", response_model=ChatReply)
def chat(payload: ChatRequest, db: Session = Depends(get_db)):
    if payload.session_id:
        session = db.get(ChatSession, payload.session_id)
        if not session:
            raise HTTPException(404, "会话不存在")
    else:
        session = ChatSession(
            title=payload.message[:20],
            context_type=payload.context_type,
            context_ref=payload.context_ref,
        )
        db.add(session)
        db.flush()

    db.add(ChatMessage(session_id=session.id, role="user", content=payload.message, is_mock=False))

    if payload.context_type == "project":
        reply = _reply_for_project(db, payload.context_ref, payload.message)
    elif payload.context_type == "history":
        reply = _reply_for_history(db, payload.message)
    elif payload.context_type == "document":
        reply = _reply_for_document(db, payload.context_ref, payload.message)
    else:
        reply = _reply_general(db, payload.message)

    db.add(ChatMessage(session_id=session.id, role="assistant", content=reply, is_mock=True))
    db.commit()
    return ChatReply(session_id=session.id, reply=reply, is_mock=True)
