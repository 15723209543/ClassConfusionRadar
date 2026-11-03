"""
本文件的作用是：定义课堂文件接口使用的数据结构与校验规则。
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import FileKind, ParseStatus


class UploadedFileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    file_kind: FileKind
    original_name: str
    storage_path: str
    parse_status: ParseStatus
    row_count: int
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime


class DatasetImportRead(BaseModel):
    uploaded_files: list[UploadedFileRead]
    knowledge_points_created: int = 0
    skipped_files: list[str] = Field(default_factory=list)
    manifest_found: bool = False
