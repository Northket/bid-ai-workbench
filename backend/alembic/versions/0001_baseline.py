"""第一阶段原始结构基线（create_all 时代的库标记到此版本）。

Revision ID: 0001
Revises:
Create Date: 2026-10-31
"""
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 基线：第一阶段通过 Base.metadata.create_all() 创建的完整结构，
    # 历史库 stamp 到此版本即可；全新库由启动流程 create_all + stamp(head)。
    pass


def downgrade() -> None:
    pass
