"""
本文件的作用是：定义教学分段接口使用的数据结构与校验规则。
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class TeachingSegmentCreate(BaseModel):
    knowledge_point_id: Optional[int] = None
    title: str
    start_minute: float = Field(ge=0)
    end_minute: float = Field(gt=0)
    display_order: int = 1
    teacher_notes: Optional[str] = None


class TeachingSegmentUpdate(BaseModel):
    knowledge_point_id: Optional[int] = None
    title: Optional[str] = None
    start_minute: Optional[float] = Field(default=None, ge=0)
    end_minute: Optional[float] = Field(default=None, gt=0)
    display_order: Optional[int] = None
    teacher_notes: Optional[str] = None


class AutoSegmentBuildRequest(BaseModel):
    replace_existing: bool = False


class AutoSegmentSourceInfo(BaseModel):
    transcript_file_id: int
    transcript_filename: str
    ppt_timeline_file_id: int
    ppt_timeline_filename: str


class TeachingSegmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    knowledge_point_id: Optional[int]
    title: str
    start_minute: float
    end_minute: float
    display_order: int
    teacher_notes: Optional[str]
    created_at: datetime
    updated_at: datetime


class AutoSegmentBuildResult(BaseModel):
    created_count: int
    replaced_existing: bool
    transcript_chunk_count: int
    slide_window_count: int
    source_files: AutoSegmentSourceInfo
    message: str
    segments: list[TeachingSegmentRead]
