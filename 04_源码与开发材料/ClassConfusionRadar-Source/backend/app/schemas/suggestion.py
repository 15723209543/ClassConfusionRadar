"""
本文件的作用是：定义再教学建议接口使用的数据结构与校验规则。
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import SuggestionStatus


class StructuredSuggestionContent(BaseModel):
    diagnosis: str = Field(min_length=1)
    reteach_script: list[str] = Field(min_length=1)
    board_plan: list[str] = Field(min_length=1)
    micro_exercises: list[str] = Field(min_length=1)
    followup_task: str = Field(min_length=1)

    @field_validator("diagnosis", "followup_task")
    @classmethod
    def validate_text_field(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("文本内容不能为空。")
        return cleaned

    @field_validator("reteach_script", "board_plan", "micro_exercises")
    @classmethod
    def validate_list_field(cls, values: list[str]) -> list[str]:
        cleaned_items = [item.strip() for item in values if item and item.strip()]
        if not cleaned_items:
            raise ValueError("列表内容不能为空。")
        return cleaned_items


class ReteachingSuggestionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    segment_score_id: int
    status: SuggestionStatus
    model_name: str
    generation_mode: str
    generation_mode_label: str
    prompt_version: str
    structured_content: Optional[StructuredSuggestionContent] = None
    suggestion_markdown: Optional[str] = None
    failure_reason: Optional[str] = None
    generated_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
