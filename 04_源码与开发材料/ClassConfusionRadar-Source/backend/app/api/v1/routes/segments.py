"""
本文件的作用是：提供教学分段相关的 HTTP 接口。
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.schemas.common import ApiMessage
from app.schemas.segment import (
    AutoSegmentBuildRequest,
    AutoSegmentBuildResult,
    TeachingSegmentCreate,
    TeachingSegmentRead,
    TeachingSegmentUpdate,
)
from app.services import segment_builder_service, segment_service

router = APIRouter()


@router.get("/sessions/{session_id}/segments", response_model=list[TeachingSegmentRead])
def list_segments(session_id: int, db: Session = Depends(get_db_session)) -> list[TeachingSegmentRead]:
    return segment_service.list_segments(db, session_id)


@router.post("/sessions/{session_id}/segments", response_model=TeachingSegmentRead, status_code=status.HTTP_201_CREATED)
def create_segment(
    session_id: int,
    payload: TeachingSegmentCreate,
    db: Session = Depends(get_db_session),
) -> TeachingSegmentRead:
    return segment_service.create_segment(db, session_id, payload.model_dump())


@router.post("/sessions/{session_id}/segments/auto-build", response_model=AutoSegmentBuildResult)
def auto_build_segments(
    session_id: int,
    payload: AutoSegmentBuildRequest,
    db: Session = Depends(get_db_session),
) -> AutoSegmentBuildResult:
    return segment_builder_service.auto_build_segments(
        db,
        session_id=session_id,
        replace_existing=payload.replace_existing,
    )


@router.patch("/segments/{segment_id}", response_model=TeachingSegmentRead)
def update_segment(
    segment_id: int,
    payload: TeachingSegmentUpdate,
    db: Session = Depends(get_db_session),
) -> TeachingSegmentRead:
    return segment_service.update_segment(db, segment_id, payload.model_dump(exclude_unset=True))


@router.delete("/segments/{segment_id}", response_model=ApiMessage)
def delete_segment(segment_id: int, db: Session = Depends(get_db_session)) -> ApiMessage:
    segment_service.delete_segment(db, segment_id)
    return ApiMessage(message="教学分段已删除。")
