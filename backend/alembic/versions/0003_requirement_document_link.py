"""整改 C1：投标要求关联原始招标文件（9 个追溯字段 + 存量数据回填）。

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-31
"""
import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

NEW_COLUMNS = [
    sa.Column("document_id", sa.Integer(), nullable=True, comment="关联原始文件"),
    sa.Column("page_number", sa.Integer(), nullable=True, comment="原文页码"),
    sa.Column("chapter_title", sa.String(200), server_default="", comment="所属章节"),
    sa.Column("section_number", sa.String(64), server_default="", comment="条款编号"),
    sa.Column("original_text", sa.Text(), server_default="", comment="原始文本片段"),
    sa.Column("extraction_method", sa.String(16), server_default="manual",
              comment="manual/rule/ai"),
    sa.Column("verification_status", sa.String(16), server_default="pending",
              comment="pending/confirmed/rejected"),
    sa.Column("verified_at", sa.DateTime(), nullable=True, comment="核验时间"),
    sa.Column("verified_by", sa.String(64), server_default="", comment="核验人员"),
]


def upgrade() -> None:
    # SQLite：batch 模式（重建表+拷贝数据）以带上 document_files 外键
    with op.batch_alter_table("bid_requirements") as batch:
        for col in NEW_COLUMNS:
            batch.add_column(col)
        batch.create_foreign_key("fk_requirement_document", "document_files",
                                 ["document_id"], ["id"])
    # 存量回填：原 confirmed=True 的要求映射为已确认核验状态（原内容全部保留）
    op.execute("""
        UPDATE bid_requirements
        SET verification_status = 'confirmed',
            verified_at = updated_at,
            verified_by = '系统迁移'
        WHERE confirmed = 1 AND verification_status = 'pending'
    """)


def downgrade() -> None:
    names = ["document_id", "page_number", "chapter_title", "section_number",
             "original_text", "extraction_method", "verification_status",
             "verified_at", "verified_by"]
    with op.batch_alter_table("bid_requirements") as batch:
        for n in names:
            batch.drop_column(n)
