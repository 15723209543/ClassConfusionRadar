"""
本文件的作用是：提供知识点相关的 HTTP 接口。
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.schemas.common import ApiMessage
from app.schemas.knowledge_point import KnowledgePointCreate, KnowledgePointRead, KnowledgePointUpdate
from app.services import knowledge_point_service

router = APIRouter()


@router.get("/sessions/{session_id}/knowledge-points", response_model=list[KnowledgePointRead])
def list_knowledge_points(session_id: int, db: Session = Depends(get_db_session)) -> list[KnowledgePointRead]:
    return knowledge_point_service.list_knowledge_points(db, session_id)


@router.post(
    "/sessions/{session_id}/knowledge-points",
    response_model=KnowledgePointRead,
    status_code=status.HTTP_201_CREATED,
)
def create_knowledge_point(
    session_id: int, payload: KnowledgePointCreate, db: Session = Depends(get_db_session)
) -> KnowledgePointRead:
    return knowledge_point_service.create_knowledge_point(db, session_id, payload.model_dump())


@router.patch("/knowledge-points/{knowledge_point_id}", response_model=KnowledgePointRead)
def update_knowledge_point(
    knowledge_point_id: int, payload: KnowledgePointUpdate, db: Session = Depends(get_db_session)
) -> KnowledgePointRead:
    return knowledge_point_service.update_knowledge_point(db, knowledge_point_id, payload.model_dump(exclude_unset=True))


@router.delete("/knowledge-points/{knowledge_point_id}", response_model=ApiMessage)
def delete_knowledge_point(knowledge_point_id: int, db: Session = Depends(get_db_session)) -> ApiMessage:
    knowledge_point_service.delete_knowledge_point(db, knowledge_point_id)
    return ApiMessage(message="知识点已删除。")
