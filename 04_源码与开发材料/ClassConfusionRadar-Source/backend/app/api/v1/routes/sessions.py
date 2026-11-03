"""
本文件的作用是：提供课堂场次相关的 HTTP 接口。
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.schemas.common import ApiMessage
from app.schemas.session import SessionCreate, SessionDetail, SessionSummary, SessionUpdate
from app.services import session_service

router = APIRouter(prefix="/sessions")


@router.get("", response_model=list[SessionSummary])
def list_sessions(db: Session = Depends(get_db_session)) -> list[SessionSummary]:
    return session_service.list_sessions(db)


@router.post("", response_model=SessionSummary, status_code=status.HTTP_201_CREATED)
def create_session(payload: SessionCreate, db: Session = Depends(get_db_session)) -> SessionSummary:
    created = session_service.create_session(db, payload)
    return session_service.build_session_summary(db, created)


@router.get("/{session_id}", response_model=SessionDetail)
def get_session(session_id: int, db: Session = Depends(get_db_session)) -> SessionDetail:
    return session_service.get_session_detail(db, session_id)


@router.patch("/{session_id}", response_model=SessionSummary)
def update_session(
    session_id: int, payload: SessionUpdate, db: Session = Depends(get_db_session)
) -> SessionSummary:
    updated = session_service.update_session(db, session_id, payload)
    return session_service.build_session_summary(db, updated)


@router.delete("/{session_id}", response_model=ApiMessage)
def delete_session(session_id: int, db: Session = Depends(get_db_session)) -> ApiMessage:
    session_service.delete_session(db, session_id)
    return ApiMessage(message="课堂场次已删除。")
