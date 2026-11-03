"""
本文件的作用是：实现知识点相关的核心业务处理。
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import conflict, not_found
from app.models.session import KnowledgePoint
from app.services.session_service import get_session_or_404


def list_knowledge_points(db: Session, session_id: int) -> list[KnowledgePoint]:
    get_session_or_404(db, session_id)
    return db.scalars(
        select(KnowledgePoint).where(KnowledgePoint.session_id == session_id).order_by(KnowledgePoint.display_order)
    ).all()


def create_knowledge_point(db: Session, session_id: int, payload: dict) -> KnowledgePoint:
    get_session_or_404(db, session_id)
    duplicate = db.scalars(
        select(KnowledgePoint).where(
            KnowledgePoint.session_id == session_id,
            KnowledgePoint.name == payload["name"],
        )
    ).first()
    if duplicate:
        raise conflict("同一课堂场次下知识点名称不能重复。")

    knowledge_point = KnowledgePoint(session_id=session_id, **payload)
    db.add(knowledge_point)
    db.commit()
    db.refresh(knowledge_point)
    return knowledge_point


def update_knowledge_point(db: Session, knowledge_point_id: int, payload: dict) -> KnowledgePoint:
    knowledge_point = db.get(KnowledgePoint, knowledge_point_id)
    if not knowledge_point:
        raise not_found("知识点不存在。")

    next_name = payload.get("name")
    if next_name and next_name != knowledge_point.name:
        duplicate = db.scalars(
            select(KnowledgePoint).where(
                KnowledgePoint.session_id == knowledge_point.session_id,
                KnowledgePoint.name == next_name,
                KnowledgePoint.id != knowledge_point_id,
            )
        ).first()
        if duplicate:
            raise conflict("同一课堂场次下知识点名称不能重复。")

    for field, value in payload.items():
        setattr(knowledge_point, field, value)
    db.commit()
    db.refresh(knowledge_point)
    return knowledge_point


def delete_knowledge_point(db: Session, knowledge_point_id: int) -> None:
    knowledge_point = db.get(KnowledgePoint, knowledge_point_id)
    if not knowledge_point:
        raise not_found("知识点不存在。")
    db.delete(knowledge_point)
    db.commit()
