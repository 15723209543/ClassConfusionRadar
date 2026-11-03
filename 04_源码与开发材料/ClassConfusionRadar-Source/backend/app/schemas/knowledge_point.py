"""
本文件的作用是：定义知识点接口使用的数据结构与校验规则。
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class KnowledgePointCreate(BaseModel):
    name: str
    topic_area: Optional[str] = None
    description: Optional[str] = None
    display_order: int = 1


class KnowledgePointUpdate(BaseModel):
    name: Optional[str] = None
    topic_area: Optional[str] = None
    description: Optional[str] = None
    display_order: Optional[int] = None


class KnowledgePointRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    name: str
    topic_area: Optional[str] = None
    description: Optional[str] = None
    display_order: int
    created_at: datetime
    updated_at: datetime
