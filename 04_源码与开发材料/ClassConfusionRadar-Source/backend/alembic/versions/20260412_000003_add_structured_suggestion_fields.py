"""
本文件的作用是：定义当前版本的数据库结构迁移与回退步骤。
"""
"""add structured suggestion fields"""

from alembic import op
import sqlalchemy as sa


revision = "20260412_000003"
down_revision = "20260412_000002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("reteaching_suggestions", sa.Column("structured_content", sa.JSON(), nullable=True))
    op.add_column("reteaching_suggestions", sa.Column("failure_reason", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("reteaching_suggestions", "failure_reason")
    op.drop_column("reteaching_suggestions", "structured_content")
