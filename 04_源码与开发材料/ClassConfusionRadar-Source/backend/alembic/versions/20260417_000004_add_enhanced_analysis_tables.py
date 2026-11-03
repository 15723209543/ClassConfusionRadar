"""
本文件的作用是：定义当前版本的数据库结构迁移与回退步骤。
"""
"""add enhanced analysis tables"""

from alembic import op
import sqlalchemy as sa


revision = "20260417_000004"
down_revision = "20260412_000003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    enhanced_analysis_status = sa.Enum(
        "processing",
        "ready",
        "failed",
        name="enhanced_analysis_status",
    )
    enhanced_analysis_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "enhanced_session_analyses",
        sa.Column("analysis_run_id", sa.Integer(), nullable=False),
        sa.Column("status", enhanced_analysis_status, nullable=False),
        sa.Column("model_name", sa.String(), nullable=False),
        sa.Column("prompt_version", sa.String(), nullable=False),
        sa.Column("structured_content", sa.JSON(), nullable=True),
        sa.Column("citations", sa.JSON(), nullable=True),
        sa.Column("memory_notes", sa.JSON(), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["analysis_run_id"],
            ["analysis_runs.id"],
            name=op.f("fk_enhanced_session_analyses_analysis_run_id_analysis_runs"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_enhanced_session_analyses")),
    )

    op.create_table(
        "enhanced_segment_analyses",
        sa.Column("segment_score_id", sa.Integer(), nullable=False),
        sa.Column("status", enhanced_analysis_status, nullable=False),
        sa.Column("model_name", sa.String(), nullable=False),
        sa.Column("prompt_version", sa.String(), nullable=False),
        sa.Column("structured_content", sa.JSON(), nullable=True),
        sa.Column("citations", sa.JSON(), nullable=True),
        sa.Column("memory_notes", sa.JSON(), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["segment_score_id"],
            ["segment_confusion_scores.id"],
            name=op.f("fk_enhanced_segment_analyses_segment_score_id_segment_confusion_scores"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_enhanced_segment_analyses")),
    )


def downgrade() -> None:
    op.drop_table("enhanced_segment_analyses")
    op.drop_table("enhanced_session_analyses")
    sa.Enum(name="enhanced_analysis_status").drop(op.get_bind(), checkfirst=True)
