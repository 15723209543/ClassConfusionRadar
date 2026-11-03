"""
本文件的作用是：定义课堂场次接口使用的数据结构与校验规则。
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import SessionStatus
from app.schemas.file import UploadedFileRead
from app.schemas.knowledge_point import KnowledgePointRead
from app.schemas.segment import TeachingSegmentRead


class SessionCreate(BaseModel):
    title: str
    course_type: str
    class_date: str
    duration_minutes: int = Field(gt=0)
    notes: Optional[str] = None


class SessionUpdate(BaseModel):
    title: Optional[str] = None
    course_type: Optional[str] = None
    class_date: Optional[str] = None
    duration_minutes: Optional[int] = Field(default=None, gt=0)
    status: Optional[SessionStatus] = None
    notes: Optional[str] = None


class SessionSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    course_type: str
    class_date: str
    duration_minutes: int
    status: SessionStatus
    notes: Optional[str]
    segment_count: int
    knowledge_point_count: int
    upload_count: int
    high_risk_count: int
    created_at: datetime
    updated_at: datetime


class SessionDetail(BaseModel):
    id: int
    title: str
    course_type: str
    class_date: str
    duration_minutes: int
    status: SessionStatus
    notes: Optional[str]
    upload_count: int
    segment_count: int
    knowledge_point_count: int
    high_risk_count: int
    latest_analysis_run_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    uploaded_files: list[UploadedFileRead]
    knowledge_points: list[KnowledgePointRead]
    segments: list[TeachingSegmentRead]
