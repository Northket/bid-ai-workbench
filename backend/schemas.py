"""Pydantic 请求/响应模型。"""
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

ReqCategory = Literal["technical", "business", "credit"]
Importance = Literal["high", "medium", "low"]
DateT = date  # Milestone 字段名 date 会遮蔽类型名，用别名引用


# ---------- 招标项目 ----------
class ProjectBase(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    code: str = Field(min_length=1, max_length=64)
    region: str = "深圳市"
    project_type: str = "房建"
    tender_method: str = "公开招标"
    tenderer: str = ""
    agency: str = ""
    budget: float = 0.0
    publish_date: date | None = None
    deadline: date | None = None
    stage: str = "跟踪中"
    participating: bool = False
    favorite: bool = False
    description: str = ""


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: str | None = None
    code: str | None = None
    region: str | None = None
    project_type: str | None = None
    tender_method: str | None = None
    tenderer: str | None = None
    agency: str | None = None
    budget: float | None = None
    publish_date: date | None = None
    deadline: date | None = None
    stage: str | None = None
    participating: bool | None = None
    favorite: bool | None = None
    description: str | None = None


class ProjectOut(ProjectBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    deleted_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


# ---------- 公告 ----------
class AnnouncementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    ann_type: str
    project_code: str
    source: str
    source_url: str
    publish_date: date | None
    content: str
    winner: str
    win_amount: float
    is_demo: bool
    created_at: datetime


class AnnouncementCreate(BaseModel):
    title: str
    ann_type: str = "招标公告"
    project_code: str = ""
    source: str = "手动录入"
    source_url: str = ""
    publish_date: date | None = None
    content: str = ""
    winner: str = ""
    win_amount: float = 0.0


# ---------- 文件 ----------
class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    original_name: str
    stored_name: str
    file_type: str
    size: int
    project_id: int | None
    status: str
    parse_result: str
    error_message: str
    is_demo: bool
    uploaded_at: datetime
    project_name: str | None = None


class DocumentUpdate(BaseModel):
    project_id: int | None = None


# ---------- 投标要求 ----------
class RequirementBase(BaseModel):
    project_id: int
    category: ReqCategory
    name: str = Field(min_length=1, max_length=200)
    content: str = ""
    source_text: str = ""
    page_no: str = ""
    importance: Importance = "medium"
    status: str = "未开始"
    confirmed: bool = False
    remark: str = ""
    # 整改 C1：原始文件追溯
    document_id: int | None = None
    page_number: int | None = None
    chapter_title: str = ""
    section_number: str = ""
    original_text: str = ""
    extraction_method: Literal["manual", "rule", "ai"] = "manual"
    verification_status: Literal["pending", "confirmed", "rejected"] = "pending"


class RequirementCreate(RequirementBase):
    pass


class RequirementUpdate(BaseModel):
    name: str | None = None
    content: str | None = None
    source_text: str | None = None
    page_no: str | None = None
    importance: Importance | None = None
    status: str | None = None
    confirmed: bool | None = None
    remark: str | None = None
    project_id: int | None = None
    category: ReqCategory | None = None
    document_id: int | None = None
    page_number: int | None = None
    chapter_title: str | None = None
    section_number: str | None = None
    original_text: str | None = None
    extraction_method: Literal["manual", "rule", "ai"] | None = None
    verification_status: Literal["pending", "confirmed", "rejected"] | None = None


class RequirementOut(RequirementBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    verified_at: datetime | None = None
    verified_by: str = ""
    created_at: datetime
    updated_at: datetime
    project_name: str | None = None
    document_name: str | None = None


# ---------- 历史项目 ----------
class HistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_name: str
    project_code: str
    region: str
    project_type: str
    tender_method: str
    tenderer: str
    winner: str
    bid_amount: float
    control_amount: float
    participants: list[str]
    bid_open_date: date | None
    remarks: str
    is_demo: bool


class HistoryCreate(BaseModel):
    project_name: str
    project_code: str = ""
    region: str = "深圳市"
    project_type: str = "房建"
    tender_method: str = "公开招标"
    tenderer: str = ""
    winner: str = ""
    bid_amount: float = 0.0
    control_amount: float = 0.0
    participants: list[str] = []
    bid_open_date: date | None = None
    remarks: str = ""


class ImportPreview(BaseModel):
    ok: bool
    message: str
    rows: int = 0
    imported: int = 0
    errors: list[str] = []


# ---------- 任务 / 节点 / 成果 ----------
class TaskBase(BaseModel):
    project_id: int
    title: str
    owner: str = ""
    due_date: date | None = None
    status: str = "待办"
    priority: Importance = "medium"
    remark: str = ""


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: str | None = None
    owner: str | None = None
    due_date: date | None = None
    status: str | None = None
    priority: Importance | None = None
    remark: str | None = None


class TaskOut(TaskBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime


class MilestoneBase(BaseModel):
    project_id: int
    name: str
    date: DateT | None = None
    kind: str = "其他"
    description: str = ""


class MilestoneCreate(MilestoneBase):
    pass


class MilestoneOut(MilestoneBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class DeliverableBase(BaseModel):
    project_id: int
    name: str
    category: str = "投标文件"
    version: str = "V1.0"
    size: int = 0


class DeliverableOut(DeliverableBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    file_path: str
    uploaded_at: datetime


# ---------- AI 对话 ----------
class ChatSessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    context_type: str
    context_ref: str
    created_at: datetime


class ChatMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    session_id: int
    role: str
    content: str
    is_mock: bool
    created_at: datetime


class ChatSessionDetail(ChatSessionOut):
    messages: list[ChatMessageOut] = []


class ChatRequest(BaseModel):
    session_id: int | None = None
    context_type: str = "general"
    context_ref: str = ""
    message: str = Field(min_length=1, max_length=4000)


class ChatReply(BaseModel):
    session_id: int
    reply: str
    is_mock: bool = True
    note: str = "当前为演示阶段：回复由规则引擎基于本地数据库生成，已明确标注为模拟回复。"


# ---------- 设置 ----------
class SettingItem(BaseModel):
    key: str
    value: str


class SettingsOut(BaseModel):
    settings: dict[str, dict[str, Any]]


# ---------- 工作台 ----------
class DashboardOut(BaseModel):
    project_count: int
    participating_count: int
    favorite_count: int
    pending_task_count: int
    document_count: int
    requirement_pending: int
    announcement_count: int
    history_count: int
    type_distribution: list[dict[str, Any]]
    win_trend: list[dict[str, Any]]
    recent_projects: list[ProjectOut]
    recent_documents: list[DocumentOut]
    bid_progress: list[dict[str, Any]]
    upcoming_milestones: list[dict[str, Any]]
