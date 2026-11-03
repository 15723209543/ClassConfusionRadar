"""
本文件的作用是：实现课堂场次相关的核心业务处理。
"""
import shutil
from pathlib import Path
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.core.errors import not_found
from app.models.analytics import AnalysisRun, SegmentConfusionScore
from app.models.enums import AnalysisStatus, ParseStatus, RiskLevel, SessionStatus
from app.models.records import SessionStudent, Student
from app.models.session import ClassSession, TeachingSegment, UploadedFile
from app.schemas.session import SessionCreate, SessionDetail, SessionSummary, SessionUpdate


def list_sessions(db: Session) -> list[SessionSummary]:
    sessions = db.scalars(select(ClassSession).order_by(ClassSession.created_at.desc())).all()
    return [build_session_summary(db, session) for session in sessions]


def create_session(db: Session, payload: SessionCreate) -> ClassSession:
    class_session = ClassSession(**payload.model_dump())
    db.add(class_session)
    db.commit()
    db.refresh(class_session)
    return class_session


def get_session_or_404(db: Session, session_id: int) -> ClassSession:
    class_session = db.scalars(
        select(ClassSession)
        .where(ClassSession.id == session_id)
        .options(
            joinedload(ClassSession.uploaded_files),
            joinedload(ClassSession.knowledge_points),
            joinedload(ClassSession.segments),
        )
    ).unique().first()
    if not class_session:
        raise not_found("课堂场次不存在。")
    return class_session


def get_session_detail(db: Session, session_id: int) -> SessionDetail:
    class_session = get_session_or_404(db, session_id)
    latest_run = get_latest_completed_run(db, session_id)
    summary = build_session_summary(db, class_session)
    return SessionDetail(
        **summary.model_dump(exclude={"segment_count", "knowledge_point_count", "upload_count", "high_risk_count"}),
        upload_count=summary.upload_count,
        segment_count=summary.segment_count,
        knowledge_point_count=summary.knowledge_point_count,
        high_risk_count=summary.high_risk_count,
        latest_analysis_run_id=latest_run.id if latest_run else None,
        uploaded_files=sorted(class_session.uploaded_files, key=lambda item: item.created_at, reverse=True),
        knowledge_points=sorted(class_session.knowledge_points, key=lambda item: item.display_order),
        segments=sorted(class_session.segments, key=lambda item: item.display_order),
    )


def update_session(db: Session, session_id: int, payload: SessionUpdate) -> ClassSession:
    class_session = get_session_or_404(db, session_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(class_session, field, value)
    db.commit()
    db.refresh(class_session)
    return class_session


def delete_session(db: Session, session_id: int) -> None:
    class_session = get_session_or_404(db, session_id)
    student_ids = [item.student_id for item in class_session.session_students]

    db.delete(class_session)
    db.flush()

    for student_id in student_ids:
        still_used = db.scalar(
            select(func.count(SessionStudent.id)).where(SessionStudent.student_id == student_id)
        ) or 0
        if still_used == 0:
            student = db.get(Student, student_id)
            if student:
                db.delete(student)

    db.commit()

    session_dir = Path(get_settings().storage_dir) / f"session_{session_id}"
    shutil.rmtree(session_dir, ignore_errors=True)


def get_latest_completed_run(db: Session, session_id: int) -> Optional[AnalysisRun]:
    return db.scalars(
        select(AnalysisRun)
        .where(AnalysisRun.session_id == session_id, AnalysisRun.status == AnalysisStatus.completed)
        .order_by(AnalysisRun.id.desc())
    ).first()


def sync_session_status(db: Session, class_session: ClassSession) -> SessionStatus:
    db.flush()
    successful_upload_count = db.scalar(
        select(func.count(UploadedFile.id)).where(
            UploadedFile.session_id == class_session.id,
            UploadedFile.parse_status == ParseStatus.success,
        )
    ) or 0
    segment_count = db.scalar(
        select(func.count(TeachingSegment.id)).where(TeachingSegment.session_id == class_session.id)
    ) or 0

    class_session.status = (
        SessionStatus.ready if successful_upload_count > 0 and segment_count > 0 else SessionStatus.draft
    )
    db.flush()
    return class_session.status


def build_session_summary(db: Session, class_session: ClassSession) -> SessionSummary:
    latest_run = get_latest_completed_run(db, class_session.id)
    high_risk_count = 0
    if latest_run:
        high_risk_count = db.scalar(
            select(func.count(SegmentConfusionScore.id)).where(
                SegmentConfusionScore.analysis_run_id == latest_run.id,
                SegmentConfusionScore.risk_level.in_([RiskLevel.high, RiskLevel.critical]),
            )
        ) or 0

    return SessionSummary(
        id=class_session.id,
        title=class_session.title,
        course_type=class_session.course_type,
        class_date=class_session.class_date,
        duration_minutes=class_session.duration_minutes,
        status=class_session.status,
        notes=class_session.notes,
        segment_count=len(class_session.segments),
        knowledge_point_count=len(class_session.knowledge_points),
        upload_count=len(class_session.uploaded_files),
        high_risk_count=high_risk_count,
        created_at=class_session.created_at,
        updated_at=class_session.updated_at,
    )
