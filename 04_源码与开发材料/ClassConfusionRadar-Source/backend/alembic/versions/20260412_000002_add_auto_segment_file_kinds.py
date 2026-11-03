"""
本文件的作用是：定义当前版本的数据库结构迁移与回退步骤。
"""
"""add transcript and ppt timeline file kinds"""

from alembic import op


revision = "20260412_000002"
down_revision = "20260411_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE file_kind ADD VALUE IF NOT EXISTS 'transcript'")
        op.execute("ALTER TYPE file_kind ADD VALUE IF NOT EXISTS 'ppt_timeline'")


def downgrade() -> None:
    # PostgreSQL enums cannot safely remove values in-place.
    pass
