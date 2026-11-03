"""数据模型定义（SQLAlchemy 2.0 风格）。"""
from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class TenderProject(Base):
    """招标项目（项目库 / 投标项目管理共用主档）。"""

    __tablename__ = "tender_projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, comment="项目编号")
    name: Mapped[str] = mapped_column(String(200), comment="项目名称")
    region: Mapped[str] = mapped_column(String(32), comment="所属区域")
    project_type: Mapped[str] = mapped_column(String(32), comment="工程类型：房建/市政/交通/水利/装饰装修/机电安装/园林绿化/其他")
    tender_method: Mapped[str] = mapped_column(String(32), default="公开招标", comment="招标方式")
    tenderer: Mapped[str] = mapped_column(String(120), default="", comment="招标人")
    agency: Mapped[str] = mapped_column(String(120), default="", comment="招标代理机构")
    budget: Mapped[float] = mapped_column(Float, default=0.0, comment="预算/招标控制价（万元）")
    publish_date: Mapped[date | None] = mapped_column(Date, nullable=True, comment="公告发布日期")
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True, comment="投标截止日期")
    stage: Mapped[str] = mapped_column(String(16), default="跟踪中", comment="跟踪中/投标中/已结束")
    participating: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否参与投标（投标项目管理）")
    favorite: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否收藏")
    description: Mapped[str] = mapped_column(Text, default="", comment="项目概况")
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="软删除时间（回收站）")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    requirements: Mapped[list["BidRequirement"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    tasks: Mapped[list["BidTask"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    milestones: Mapped[list["Milestone"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    deliverables: Mapped[list["Deliverable"]] = relationship(back_populates="project", cascade="all, delete-orphan")


class Announcement(Base):
    """招标公告（含演示数据标记，真实数据源待接入）。"""

    __tablename__ = "announcements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(300))
    ann_type: Mapped[str] = mapped_column(String(16), comment="招标公告/开标公告/中标公告/更正公告")
    project_code: Mapped[str] = mapped_column(String(64), default="", comment="关联项目编号")
    source: Mapped[str] = mapped_column(String(64), default="深圳公共资源交易平台")
    source_url: Mapped[str] = mapped_column(String(500), default="", comment="来源链接")
    publish_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    content: Mapped[str] = mapped_column(Text, default="")
    winner: Mapped[str] = mapped_column(String(120), default="", comment="中标单位（中标公告用）")
    win_amount: Mapped[float] = mapped_column(Float, default=0.0, comment="中标金额（万元）")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否演示数据")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class DocumentFile(Base):
    """招标文件与解析记录。"""

    __tablename__ = "document_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    original_name: Mapped[str] = mapped_column(String(300), comment="原始文件名")
    stored_name: Mapped[str] = mapped_column(String(200), default="", comment="存储文件名")
    file_type: Mapped[str] = mapped_column(String(16), comment="pdf/docx/其他")
    size: Mapped[int] = mapped_column(Integer, default=0, comment="字节数")
    project_id: Mapped[int | None] = mapped_column(ForeignKey("tender_projects.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="待解析", comment="待解析/解析中/解析完成/解析失败")
    parse_result: Mapped[str] = mapped_column(Text, default="", comment="解析结果 JSON（历史演示字段，真实结果见 parse 表）")
    error_message: Mapped[str] = mapped_column(String(500), default="")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, comment="演示记录无实际文件")
    # 第二阶段：导入溯源
    source_sha256: Mapped[str] = mapped_column(String(64), default="", comment="导入源文件 SHA-256（原件保护验证）")
    package_id: Mapped[str] = mapped_column(String(40), default="", comment="同一交易包导入的分组标识")
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    project: Mapped[TenderProject | None] = relationship()
    parse_tasks: Mapped[list["DocumentParseTask"]] = relationship(
        back_populates="document", cascade="all, delete-orphan")


class DocumentParseTask(Base):
    """文档解析任务（一个文件可多次解析，保留版本）。"""

    __tablename__ = "document_parse_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("document_files.id"))
    version: Mapped[int] = mapped_column(Integer, default=1, comment="解析版本号（每文件递增）")
    status: Mapped[str] = mapped_column(String(16), default="running",
                                        comment="running/completed/failed")
    engine_version: Mapped[str] = mapped_column(String(16), default="")
    parser: Mapped[str] = mapped_column(String(64), default="")
    file_sha256: Mapped[str] = mapped_column(String(64), default="", comment="解析时文件指纹")
    stats: Mapped[dict] = mapped_column(JSON, default=dict, comment="解析统计报告")
    warnings: Mapped[list] = mapped_column(JSON, default=list)
    error_message: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    document: Mapped[DocumentFile] = relationship(back_populates="parse_tasks")


class DocumentParseResult(Base):
    """结构化解析结果（一条），全程可追溯、可人工核验。"""

    __tablename__ = "document_parse_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("document_parse_tasks.id"))
    document_id: Mapped[int] = mapped_column(ForeignKey("document_files.id"))
    category: Mapped[str] = mapped_column(String(16), comment="basic/timeline/qualification/rejection/evaluation/technical/commercial")
    field_key: Mapped[str] = mapped_column(String(64), default="")
    field_name: Mapped[str] = mapped_column(String(100), default="")
    value: Mapped[str] = mapped_column(Text, default="", comment="提取结果（当前生效值）")
    original_text: Mapped[str] = mapped_column(Text, default="", comment="原始提取值（永不覆盖）")
    manual_value: Mapped[str] = mapped_column(Text, default="", comment="人工修改值（空=未修改）")
    pdf_page: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="PDF 页序号（阅读器页码）")
    page_label: Mapped[str] = mapped_column(String(16), default="", comment="印刷页码")
    chapter: Mapped[str] = mapped_column(String(200), default="")
    section_no: Mapped[str] = mapped_column(String(32), default="")
    method: Mapped[str] = mapped_column(String(16), default="rule", comment="pdf_text/ocr/rule/ai/manual")
    source_layer: Mapped[str] = mapped_column(String(16), default="pdf_text")
    confidence: Mapped[str] = mapped_column(String(8), default="medium")
    verification_status: Mapped[str] = mapped_column(String(16), default="pending",
                                                     comment="pending/confirmed/doubtful/failed")
    verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    verified_by: Mapped[str] = mapped_column(String(64), default="")
    is_carried: Mapped[bool] = mapped_column(Boolean, default=False,
                                             comment="重新解析时结转的已核验条目")
    source_task_id: Mapped[int | None] = mapped_column(Integer, nullable=True,
                                                       comment="结转来源任务")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    document: Mapped[DocumentFile] = relationship()


class BidRequirement(Base):
    """投标要求（技术标/商务标/资信标）。"""

    __tablename__ = "bid_requirements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("tender_projects.id"))
    category: Mapped[str] = mapped_column(String(8), comment="technical/business/credit")
    name: Mapped[str] = mapped_column(String(200), comment="要求名称")
    content: Mapped[str] = mapped_column(Text, default="", comment="具体内容")
    source_text: Mapped[str] = mapped_column(String(300), default="", comment="原文出处（章节）")
    page_no: Mapped[str] = mapped_column(String(32), default="", comment="文件页码（旧字段，保留兼容）")
    importance: Mapped[str] = mapped_column(String(8), default="medium", comment="high/medium/low")
    status: Mapped[str] = mapped_column(String(16), default="未开始", comment="未开始/进行中/已完成")
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False, comment="人工确认（旧字段，保留兼容）")
    remark: Mapped[str] = mapped_column(String(500), default="")
    # ---- 整改 C1：原始文件追溯字段 ----
    document_id: Mapped[int | None] = mapped_column(ForeignKey("document_files.id"), nullable=True,
                                                    comment="关联原始文件")
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="原文页码")
    chapter_title: Mapped[str] = mapped_column(String(200), default="", comment="所属章节")
    section_number: Mapped[str] = mapped_column(String(64), default="", comment="条款编号")
    original_text: Mapped[str] = mapped_column(Text, default="", comment="原始文本片段")
    extraction_method: Mapped[str] = mapped_column(String(16), default="manual",
                                                   comment="manual/rule/ai")
    verification_status: Mapped[str] = mapped_column(String(16), default="pending",
                                                     comment="pending/confirmed/rejected")
    verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="核验时间")
    verified_by: Mapped[str] = mapped_column(String(64), default="", comment="核验人员")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    project: Mapped[TenderProject] = relationship(back_populates="requirements")
    document: Mapped[DocumentFile | None] = relationship()


class HistoricalProject(Base):
    """历史项目（中标结果库，供查询与 AI 知识检索）。"""

    __tablename__ = "historical_projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_name: Mapped[str] = mapped_column(String(300))
    project_code: Mapped[str] = mapped_column(String(64), default="")
    region: Mapped[str] = mapped_column(String(32), default="深圳市")
    project_type: Mapped[str] = mapped_column(String(32), default="房建")
    tender_method: Mapped[str] = mapped_column(String(32), default="公开招标")
    tenderer: Mapped[str] = mapped_column(String(120), default="")
    winner: Mapped[str] = mapped_column(String(120), default="", comment="中标单位")
    bid_amount: Mapped[float] = mapped_column(Float, default=0.0, comment="中标金额（万元）")
    control_amount: Mapped[float] = mapped_column(Float, default=0.0, comment="招标控制价（万元）")
    participants: Mapped[list] = mapped_column(JSON, default=list, comment="投标单位列表")
    bid_open_date: Mapped[date | None] = mapped_column(Date, nullable=True, comment="开标日期")
    remarks: Mapped[str] = mapped_column(String(500), default="")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class BidTask(Base):
    """投标任务清单。"""

    __tablename__ = "bid_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("tender_projects.id"))
    title: Mapped[str] = mapped_column(String(200))
    owner: Mapped[str] = mapped_column(String(64), default="", comment="负责人")
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="待办", comment="待办/进行中/已完成")
    priority: Mapped[str] = mapped_column(String(8), default="medium")
    remark: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    project: Mapped[TenderProject] = relationship(back_populates="tasks")


class Milestone(Base):
    """重要时间节点。"""

    __tablename__ = "milestones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("tender_projects.id"))
    name: Mapped[str] = mapped_column(String(200))
    date: Mapped[date | None] = mapped_column(Date, nullable=True)
    kind: Mapped[str] = mapped_column(String(16), default="其他", comment="开标/截标/答疑/澄清/其他")
    description: Mapped[str] = mapped_column(String(500), default="")

    project: Mapped[TenderProject] = relationship(back_populates="milestones")


class Deliverable(Base):
    """成果文件与归档文件。"""

    __tablename__ = "deliverables"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("tender_projects.id"))
    name: Mapped[str] = mapped_column(String(300))
    category: Mapped[str] = mapped_column(String(32), default="投标文件", comment="投标文件/资信材料/技术方案/商务报价/其他")
    version: Mapped[str] = mapped_column(String(32), default="V1.0")
    file_path: Mapped[str] = mapped_column(String(500), default="", comment="实际文件路径（演示记录为空）")
    size: Mapped[int] = mapped_column(Integer, default=0)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    project: Mapped[TenderProject] = relationship(back_populates="deliverables")


class ChatSession(Base):
    """AI 对话会话。"""

    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), default="新对话")
    context_type: Mapped[str] = mapped_column(String(16), default="general", comment="general/project/document/history")
    context_ref: Mapped[str] = mapped_column(String(64), default="", comment="关联对象 id")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    messages: Mapped[list["ChatMessage"]] = relationship(back_populates="session", cascade="all, delete-orphan",
                                                         order_by="ChatMessage.id")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("chat_sessions.id"))
    role: Mapped[str] = mapped_column(String(16), comment="user/assistant")
    content: Mapped[str] = mapped_column(Text)
    is_mock: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否模拟回复")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    session: Mapped[ChatSession] = relationship(back_populates="messages")


class Setting(Base):
    """系统设置（键值对）。"""

    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")
    value_type: Mapped[str] = mapped_column(String(16), default="string", comment="string/number/bool/json")
    label: Mapped[str] = mapped_column(String(100), default="")
    group: Mapped[str] = mapped_column(String(32), default="basic", comment="basic/data_source/model/storage")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)


class ActivityLog(Base):
    """最近动态（工作台"最近浏览/最近上传"数据来源）。"""

    __tablename__ = "activity_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kind: Mapped[str] = mapped_column(String(16), comment="view/upload/create")
    target: Mapped[str] = mapped_column(String(64), comment="对象类型：project/document/...")
    target_id: Mapped[str] = mapped_column(Integer, default=0)
    title: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
