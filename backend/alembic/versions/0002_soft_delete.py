"""整改 B1：tender_projects 增加 deleted_at 软删除列。

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-31
"""
import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tender_projects",
                  sa.Column("deleted_at", sa.DateTime(), nullable=True,
                            comment="软删除时间（回收站）"))


def downgrade() -> None:
    with op.batch_alter_table("tender_projects") as batch:
        batch.drop_column("deleted_at")
