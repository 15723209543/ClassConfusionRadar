"""
本文件的作用是：定义当前版本的数据库结构迁移与回退步骤。
"""
"""add reteaching interventions"""

from alembic import op
import sqlalchemy as sa


revision = "20260418_000005"
down_revision = "20260417_000004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reteaching_interventions",
        sa.Column("segment_score_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("plan_text", sa.Text(), nullable=True),
        sa.Column("outcome_summary", sa.Text(), nullable=True),
        sa.Column("followup_score_before", sa.Float(), nullable=True),
        sa.Column("followup_score_after", sa.Float(), nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["segment_score_id"],
            ["segment_confusion_scores.id"],
            name=op.f("fk_reteaching_interventions_segment_score_id_segment_confusion_scores"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_reteaching_interventions")),
    )


def downgrade() -> None:
    op.drop_table("reteaching_interventions")
