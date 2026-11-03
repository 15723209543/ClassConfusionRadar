"""
本文件的作用是：定义当前版本的数据库结构迁移与回退步骤。
"""
"""initial schema"""

from alembic import op
import sqlalchemy as sa


revision = "20260411_000001"
down_revision = None
branch_labels = None
depends_on = None


session_status = sa.Enum("draft", "ready", "analyzed", name="session_status")
file_kind = sa.Enum("quiz", "submission", "interaction", name="file_kind")
parse_status = sa.Enum("pending", "processing", "success", "failed", name="parse_status")
attendance_status = sa.Enum("present", "absent", "late", name="attendance_status")
analysis_status = sa.Enum("pending", "completed", "failed", name="analysis_status")
risk_level = sa.Enum("low", "medium", "high", "critical", name="risk_level")
suggestion_status = sa.Enum("processing", "ready", "failed", name="suggestion_status")


def upgrade() -> None:
    bind = op.get_bind()
    session_status.create(bind, checkfirst=True)
    file_kind.create(bind, checkfirst=True)
    parse_status.create(bind, checkfirst=True)
    attendance_status.create(bind, checkfirst=True)
    analysis_status.create(bind, checkfirst=True)
    risk_level.create(bind, checkfirst=True)
    suggestion_status.create(bind, checkfirst=True)

    op.create_table(
        "class_sessions",
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("course_type", sa.String(length=50), nullable=False),
        sa.Column("class_date", sa.String(length=20), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("status", session_status, nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_class_sessions")),
    )
    op.create_table(
        "students",
        sa.Column("student_code", sa.String(length=80), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_students")),
        sa.UniqueConstraint("student_code", name=op.f("uq_students_student_code")),
    )
    op.create_table(
        "uploaded_files",
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("file_kind", file_kind, nullable=False),
        sa.Column("original_name", sa.String(length=255), nullable=False),
        sa.Column("storage_path", sa.String(length=500), nullable=False),
        sa.Column("parse_status", parse_status, nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["class_sessions.id"], name=op.f("fk_uploaded_files_session_id_class_sessions"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_uploaded_files")),
    )
    op.create_table(
        "knowledge_points",
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("topic_area", sa.String(length=120), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["class_sessions.id"], name=op.f("fk_knowledge_points_session_id_class_sessions"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_knowledge_points")),
        sa.UniqueConstraint("session_id", "name", name=op.f("uq_knowledge_points_session_id_name")),
    )
    op.create_table(
        "analysis_runs",
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("status", analysis_status, nullable=False),
        sa.Column("config_json", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["class_sessions.id"], name=op.f("fk_analysis_runs_session_id_class_sessions"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_analysis_runs")),
    )
    op.create_table(
        "session_students",
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("attendance_status", attendance_status, nullable=False),
        sa.Column("group_name", sa.String(length=120), nullable=True),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["class_sessions.id"], name=op.f("fk_session_students_session_id_class_sessions"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], name=op.f("fk_session_students_student_id_students"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_session_students")),
        sa.UniqueConstraint("session_id", "student_id", name=op.f("uq_session_students_session_id_student_id")),
    )
    op.create_table(
        "teaching_segments",
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("knowledge_point_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("start_minute", sa.Float(), nullable=False),
        sa.Column("end_minute", sa.Float(), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("teacher_notes", sa.Text(), nullable=True),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("end_minute > start_minute", name="segment_end_after_start"),
        sa.CheckConstraint("start_minute >= 0", name="segment_start_non_negative"),
        sa.ForeignKeyConstraint(["knowledge_point_id"], ["knowledge_points.id"], name=op.f("fk_teaching_segments_knowledge_point_id_knowledge_points"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["session_id"], ["class_sessions.id"], name=op.f("fk_teaching_segments_session_id_class_sessions"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_teaching_segments")),
    )
    op.create_table(
        "quiz_records",
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("source_file_id", sa.Integer(), nullable=True),
        sa.Column("question_code", sa.String(length=120), nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        sa.Column("event_minute", sa.Float(), nullable=False),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["source_file_id"], ["uploaded_files.id"], name=op.f("fk_quiz_records_source_file_id_uploaded_files"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], name=op.f("fk_quiz_records_student_id_students"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["class_sessions.id"], name=op.f("fk_quiz_records_session_id_class_sessions"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_quiz_records")),
    )
    op.create_table(
        "submission_records",
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("source_file_id", sa.Integer(), nullable=True),
        sa.Column("task_name", sa.String(length=120), nullable=False),
        sa.Column("language", sa.String(length=50), nullable=False),
        sa.Column("result_status", sa.String(length=50), nullable=False),
        sa.Column("error_type", sa.String(length=120), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("event_minute", sa.Float(), nullable=False),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["source_file_id"], ["uploaded_files.id"], name=op.f("fk_submission_records_source_file_id_uploaded_files"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], name=op.f("fk_submission_records_student_id_students"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["class_sessions.id"], name=op.f("fk_submission_records_session_id_class_sessions"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_submission_records")),
    )
    op.create_table(
        "interaction_records",
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("source_file_id", sa.Integer(), nullable=True),
        sa.Column("event_type", sa.String(length=120), nullable=False),
        sa.Column("value", sa.Float(), nullable=False, server_default="1"),
        sa.Column("event_minute", sa.Float(), nullable=False),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["source_file_id"], ["uploaded_files.id"], name=op.f("fk_interaction_records_source_file_id_uploaded_files"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], name=op.f("fk_interaction_records_student_id_students"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["class_sessions.id"], name=op.f("fk_interaction_records_session_id_class_sessions"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_interaction_records")),
    )
    op.create_table(
        "segment_confusion_scores",
        sa.Column("analysis_run_id", sa.Integer(), nullable=False),
        sa.Column("segment_id", sa.Integer(), nullable=False),
        sa.Column("confusion_score", sa.Float(), nullable=False),
        sa.Column("risk_level", risk_level, nullable=False),
        sa.Column("signal_breakdown_json", sa.JSON(), nullable=False),
        sa.Column("error_summary_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["analysis_run_id"], ["analysis_runs.id"], name=op.f("fk_segment_confusion_scores_analysis_run_id_analysis_runs"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["segment_id"], ["teaching_segments.id"], name=op.f("fk_segment_confusion_scores_segment_id_teaching_segments"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_segment_confusion_scores")),
    )
    op.create_table(
        "reteaching_suggestions",
        sa.Column("segment_score_id", sa.Integer(), nullable=False),
        sa.Column("status", suggestion_status, nullable=False),
        sa.Column("model_name", sa.String(), nullable=False),
        sa.Column("prompt_version", sa.String(), nullable=False),
        sa.Column("suggestion_markdown", sa.Text(), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["segment_score_id"], ["segment_confusion_scores.id"], name=op.f("fk_reteaching_suggestions_segment_score_id_segment_confusion_scores"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_reteaching_suggestions")),
    )


def downgrade() -> None:
    op.drop_table("reteaching_suggestions")
    op.drop_table("segment_confusion_scores")
    op.drop_table("interaction_records")
    op.drop_table("submission_records")
    op.drop_table("quiz_records")
    op.drop_table("teaching_segments")
    op.drop_table("session_students")
    op.drop_table("analysis_runs")
    op.drop_table("knowledge_points")
    op.drop_table("uploaded_files")
    op.drop_table("students")
    op.drop_table("class_sessions")

    bind = op.get_bind()
    suggestion_status.drop(bind, checkfirst=True)
    risk_level.drop(bind, checkfirst=True)
    analysis_status.drop(bind, checkfirst=True)
    attendance_status.drop(bind, checkfirst=True)
    parse_status.drop(bind, checkfirst=True)
    file_kind.drop(bind, checkfirst=True)
    session_status.drop(bind, checkfirst=True)
