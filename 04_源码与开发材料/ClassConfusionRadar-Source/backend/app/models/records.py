"""
本文件的作用是：定义records相关的数据库模型或枚举。
"""
from typing import Optional

from sqlalchemy import Boolean, Enum, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IdMixin, TimestampMixin
from app.models.enums import AttendanceStatus


class Student(Base, IdMixin, TimestampMixin):
    __tablename__ = "students"

    student_code: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)

    sessions = relationship("SessionStudent", back_populates="student", cascade="all, delete-orphan")
    quiz_records = relationship("QuizRecord", back_populates="student", cascade="all, delete-orphan")
    submission_records = relationship("SubmissionRecord", back_populates="student", cascade="all, delete-orphan")
    interaction_records = relationship("InteractionRecord", back_populates="student", cascade="all, delete-orphan")


class SessionStudent(Base, IdMixin, TimestampMixin):
    __tablename__ = "session_students"
    __table_args__ = (
        UniqueConstraint("session_id", "student_id", name="uq_session_students_session_id_student_id"),
    )

    session_id: Mapped[int] = mapped_column(ForeignKey("class_sessions.id", ondelete="CASCADE"), nullable=False)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    attendance_status: Mapped[AttendanceStatus] = mapped_column(
        Enum(AttendanceStatus, name="attendance_status"),
        default=AttendanceStatus.present,
        nullable=False,
    )
    group_name: Mapped[Optional[str]] = mapped_column(String(120))

    session = relationship("ClassSession", back_populates="session_students")
    student = relationship("Student", back_populates="sessions")


class QuizRecord(Base, IdMixin, TimestampMixin):
    __tablename__ = "quiz_records"

    session_id: Mapped[int] = mapped_column(ForeignKey("class_sessions.id", ondelete="CASCADE"), nullable=False)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    source_file_id: Mapped[Optional[int]] = mapped_column(ForeignKey("uploaded_files.id", ondelete="CASCADE"))
    question_code: Mapped[str] = mapped_column(String(120), nullable=False)
    score: Mapped[Optional[float]] = mapped_column(Float)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    event_minute: Mapped[float] = mapped_column(Float, nullable=False)

    student = relationship("Student", back_populates="quiz_records")
    source_file = relationship("UploadedFile", back_populates="quiz_records")


class SubmissionRecord(Base, IdMixin, TimestampMixin):
    __tablename__ = "submission_records"

    session_id: Mapped[int] = mapped_column(ForeignKey("class_sessions.id", ondelete="CASCADE"), nullable=False)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    source_file_id: Mapped[Optional[int]] = mapped_column(ForeignKey("uploaded_files.id", ondelete="CASCADE"))
    task_name: Mapped[str] = mapped_column(String(120), nullable=False)
    language: Mapped[str] = mapped_column(String(50), nullable=False)
    result_status: Mapped[str] = mapped_column(String(50), nullable=False)
    error_type: Mapped[Optional[str]] = mapped_column(String(120))
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    event_minute: Mapped[float] = mapped_column(Float, nullable=False)

    student = relationship("Student", back_populates="submission_records")
    source_file = relationship("UploadedFile", back_populates="submission_records")


class InteractionRecord(Base, IdMixin, TimestampMixin):
    __tablename__ = "interaction_records"

    session_id: Mapped[int] = mapped_column(ForeignKey("class_sessions.id", ondelete="CASCADE"), nullable=False)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    source_file_id: Mapped[Optional[int]] = mapped_column(ForeignKey("uploaded_files.id", ondelete="CASCADE"))
    event_type: Mapped[str] = mapped_column(String(120), nullable=False)
    value: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    event_minute: Mapped[float] = mapped_column(Float, nullable=False)

    student = relationship("Student", back_populates="interaction_records")
    source_file = relationship("UploadedFile", back_populates="interaction_records")
