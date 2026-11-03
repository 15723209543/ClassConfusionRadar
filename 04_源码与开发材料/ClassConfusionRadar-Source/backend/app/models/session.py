"""
本文件的作用是：定义课堂场次相关的数据库模型或枚举。
"""
from typing import Optional

from sqlalchemy import CheckConstraint, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IdMixin, TimestampMixin
from app.models.enums import FileKind, ParseStatus, SessionStatus


class ClassSession(Base, IdMixin, TimestampMixin):
    __tablename__ = "class_sessions"

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    course_type: Mapped[str] = mapped_column(String(50), nullable=False)
    class_date: Mapped[str] = mapped_column(String(20), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[SessionStatus] = mapped_column(
        Enum(SessionStatus, name="session_status"),
        default=SessionStatus.draft,
        nullable=False,
    )
    notes: Mapped[Optional[str]] = mapped_column(Text)

    uploaded_files = relationship("UploadedFile", back_populates="session", cascade="all, delete-orphan")
    knowledge_points = relationship("KnowledgePoint", back_populates="session", cascade="all, delete-orphan")
    segments = relationship("TeachingSegment", back_populates="session", cascade="all, delete-orphan")
    analysis_runs = relationship("AnalysisRun", back_populates="session", cascade="all, delete-orphan")
    session_students = relationship("SessionStudent", back_populates="session", cascade="all, delete-orphan")


class UploadedFile(Base, IdMixin, TimestampMixin):
    __tablename__ = "uploaded_files"

    session_id: Mapped[int] = mapped_column(ForeignKey("class_sessions.id", ondelete="CASCADE"), nullable=False)
    file_kind: Mapped[FileKind] = mapped_column(Enum(FileKind, name="file_kind"), nullable=False)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    parse_status: Mapped[ParseStatus] = mapped_column(
        Enum(ParseStatus, name="parse_status"),
        default=ParseStatus.pending,
        nullable=False,
    )
    row_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text)

    session = relationship("ClassSession", back_populates="uploaded_files")
    quiz_records = relationship("QuizRecord", back_populates="source_file", cascade="all, delete-orphan")
    submission_records = relationship("SubmissionRecord", back_populates="source_file", cascade="all, delete-orphan")
    interaction_records = relationship("InteractionRecord", back_populates="source_file", cascade="all, delete-orphan")


class KnowledgePoint(Base, IdMixin, TimestampMixin):
    __tablename__ = "knowledge_points"
    __table_args__ = (
        UniqueConstraint("session_id", "name", name="uq_knowledge_points_session_id_name"),
    )

    session_id: Mapped[int] = mapped_column(ForeignKey("class_sessions.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    topic_area: Mapped[Optional[str]] = mapped_column(String(120))
    description: Mapped[Optional[str]] = mapped_column(Text)
    display_order: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    session = relationship("ClassSession", back_populates="knowledge_points")
    segments = relationship("TeachingSegment", back_populates="knowledge_point")


class TeachingSegment(Base, IdMixin, TimestampMixin):
    __tablename__ = "teaching_segments"
    __table_args__ = (
        CheckConstraint("start_minute >= 0", name="segment_start_non_negative"),
        CheckConstraint("end_minute > start_minute", name="segment_end_after_start"),
    )

    session_id: Mapped[int] = mapped_column(ForeignKey("class_sessions.id", ondelete="CASCADE"), nullable=False)
    knowledge_point_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("knowledge_points.id", ondelete="SET NULL")
    )
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    start_minute: Mapped[float] = mapped_column(nullable=False)
    end_minute: Mapped[float] = mapped_column(nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    teacher_notes: Mapped[Optional[str]] = mapped_column(Text)

    session = relationship("ClassSession", back_populates="segments")
    knowledge_point = relationship("KnowledgePoint", back_populates="segments")
    confusion_scores = relationship("SegmentConfusionScore", back_populates="segment", cascade="all, delete-orphan")
