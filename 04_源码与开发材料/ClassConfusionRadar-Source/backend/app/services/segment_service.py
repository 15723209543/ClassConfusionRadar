"""
本文件的作用是：实现教学分段相关的核心业务处理。
"""
from typing import Optional

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.core.errors import bad_request, not_found
from app.models.session import KnowledgePoint, TeachingSegment
from app.services.session_service import get_session_or_404, sync_session_status


def list_segments(db: Session, session_id: int) -> list[TeachingSegment]:
    get_session_or_404(db, session_id)
    return db.scalars(
        select(TeachingSegment).where(TeachingSegment.session_id == session_id).order_by(TeachingSegment.display_order)
    ).all()


def create_segment(db: Session, session_id: int, payload: dict) -> TeachingSegment:
    class_session = get_session_or_404(db, session_id)
    validate_segment_payload(
        db,
        session_id,
        payload["start_minute"],
        payload["end_minute"],
        None,
        class_session.duration_minutes,
    )
    validate_knowledge_point(db, session_id, payload.get("knowledge_point_id"))

    segment = TeachingSegment(session_id=session_id, **payload)
    db.add(segment)
    db.flush()
    sync_session_status(db, class_session)
    db.commit()
    db.refresh(segment)
    return segment


def update_segment(db: Session, segment_id: int, payload: dict) -> TeachingSegment:
    segment = db.get(TeachingSegment, segment_id)
    if not segment:
        raise not_found("教学分段不存在。")

    class_session = get_session_or_404(db, segment.session_id)
    start_minute = payload.get("start_minute", segment.start_minute)
    end_minute = payload.get("end_minute", segment.end_minute)
    validate_segment_payload(
        db,
        segment.session_id,
        start_minute,
        end_minute,
        segment.id,
        class_session.duration_minutes,
    )
    validate_knowledge_point(db, segment.session_id, payload.get("knowledge_point_id", segment.knowledge_point_id))

    for field, value in payload.items():
        setattr(segment, field, value)
    db.flush()
    sync_session_status(db, class_session)
    db.commit()
    db.refresh(segment)
    return segment


def delete_segment(db: Session, segment_id: int) -> None:
    segment = db.get(TeachingSegment, segment_id)
    if not segment:
        raise not_found("教学分段不存在。")

    class_session = get_session_or_404(db, segment.session_id)
    db.delete(segment)
    db.flush()
    sync_session_status(db, class_session)
    db.commit()


def validate_knowledge_point(db: Session, session_id: int, knowledge_point_id: Optional[int]) -> None:
    if knowledge_point_id is None:
        return
    knowledge_point = db.get(KnowledgePoint, knowledge_point_id)
    if not knowledge_point or knowledge_point.session_id != session_id:
        raise bad_request("所选知识点不属于当前课堂场次。")


def validate_segment_payload(
    db: Session,
    session_id: int,
    start_minute: float,
    end_minute: float,
    current_segment_id: Optional[int],
    session_duration: int,
) -> None:
    if end_minute <= start_minute:
        raise bad_request("教学分段结束时间必须大于开始时间。")
    if end_minute > session_duration:
        raise bad_request("教学分段超出了课堂总时长。")

    overlap = db.scalars(
        select(TeachingSegment).where(
            TeachingSegment.session_id == session_id,
            TeachingSegment.id != current_segment_id if current_segment_id else True,
            or_(
                and_(TeachingSegment.start_minute <= start_minute, TeachingSegment.end_minute > start_minute),
                and_(TeachingSegment.start_minute < end_minute, TeachingSegment.end_minute >= end_minute),
                and_(TeachingSegment.start_minute >= start_minute, TeachingSegment.end_minute <= end_minute),
            ),
        )
    ).first()
    if overlap:
        raise bad_request("教学分段时间区间不能重叠。")
