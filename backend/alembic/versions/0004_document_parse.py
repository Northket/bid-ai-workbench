"""Phase 2: document parsing tables (tasks, results) and document_files provenance columns.

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-01
"""
import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("document_files",
                  sa.Column("source_sha256", sa.String(length=64), server_default="",
                            comment="导入源文件 SHA-256（原件保护验证）"))
    op.add_column("document_files",
                  sa.Column("package_id", sa.String(length=40), server_default="",
                            comment="同一交易包导入的分组标识"))

    op.create_table(
        "document_parse_tasks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("document_id", sa.Integer(),
                  sa.ForeignKey("document_files.id"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="running"),
        sa.Column("engine_version", sa.String(length=16), server_default=""),
        sa.Column("parser", sa.String(length=64), server_default=""),
        sa.Column("file_sha256", sa.String(length=64), server_default=""),
        sa.Column("stats", sa.JSON(), nullable=True),
        sa.Column("warnings", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), server_default=""),
        sa.Column("started_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_parse_tasks_document", "document_parse_tasks", ["document_id"])

    op.create_table(
        "document_parse_results",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("task_id", sa.Integer(),
                  sa.ForeignKey("document_parse_tasks.id"), nullable=False),
        sa.Column("document_id", sa.Integer(),
                  sa.ForeignKey("document_files.id"), nullable=False),
        sa.Column("category", sa.String(length=16), nullable=False),
        sa.Column("field_key", sa.String(length=64), server_default=""),
        sa.Column("field_name", sa.String(length=100), server_default=""),
        sa.Column("value", sa.Text(), server_default=""),
        sa.Column("original_text", sa.Text(), server_default=""),
        sa.Column("manual_value", sa.Text(), server_default=""),
        sa.Column("pdf_page", sa.Integer(), nullable=True),
        sa.Column("page_label", sa.String(length=16), server_default=""),
        sa.Column("chapter", sa.String(length=200), server_default=""),
        sa.Column("section_no", sa.String(length=32), server_default=""),
        sa.Column("method", sa.String(length=16), server_default="rule"),
        sa.Column("source_layer", sa.String(length=16), server_default="pdf_text"),
        sa.Column("confidence", sa.String(length=8), server_default="medium"),
        sa.Column("verification_status", sa.String(length=16), server_default="pending"),
        sa.Column("verified_at", sa.DateTime(), nullable=True),
        sa.Column("verified_by", sa.String(length=64), server_default=""),
        sa.Column("is_carried", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("source_task_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_parse_results_task", "document_parse_results", ["task_id"])
    op.create_index("ix_parse_results_document", "document_parse_results", ["document_id"])


def downgrade() -> None:
    op.drop_index("ix_parse_results_document", table_name="document_parse_results")
    op.drop_index("ix_parse_results_task", table_name="document_parse_results")
    op.drop_table("document_parse_results")
    op.drop_index("ix_parse_tasks_document", table_name="document_parse_tasks")
    op.drop_table("document_parse_tasks")
    with op.batch_alter_table("document_files") as batch:
        batch.drop_column("package_id")
        batch.drop_column("source_sha256")
