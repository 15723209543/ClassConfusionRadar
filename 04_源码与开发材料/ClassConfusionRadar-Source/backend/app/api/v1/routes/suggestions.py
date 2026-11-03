"""
本文件的作用是：提供再教学建议相关的 HTTP 接口。
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.schemas.suggestion import ReteachingSuggestionRead
from app.services import suggestion_service

router = APIRouter()


@router.post(
    "/segment-scores/{segment_score_id}/suggestions",
    response_model=ReteachingSuggestionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_suggestion(segment_score_id: int, db: Session = Depends(get_db_session)) -> ReteachingSuggestionRead:
    return suggestion_service.generate_suggestion(db, segment_score_id)


@router.get("/segment-scores/{segment_score_id}/suggestions", response_model=ReteachingSuggestionRead)
def get_suggestion(segment_score_id: int, db: Session = Depends(get_db_session)) -> ReteachingSuggestionRead:
    return suggestion_service.get_latest_suggestion(db, segment_score_id)
