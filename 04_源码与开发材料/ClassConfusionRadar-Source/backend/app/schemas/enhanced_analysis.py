"""
本文件的作用是：定义增强课堂解读接口使用的数据结构与校验规则。
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import EnhancedAnalysisStatus


class EnhanceAnalysisRequest(BaseModel):
    force_refresh: bool = False
    allow_web_search: bool = True
    include_memory: bool = True


class AnalysisCitation(BaseModel):
    title: str = Field(min_length=1)
    url: Optional[str] = None
    source_type: str = Field(min_length=1)
    excerpt: str = Field(min_length=1)

    @field_validator("title", "source_type", "excerpt")
    @classmethod
    def validate_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("字段内容不能为空。")
        return cleaned


class TopSegmentInsight(BaseModel):
    segment_score_id: int
    segment_id: Optional[int] = None
    title: str = Field(min_length=1)
    why_high_risk: str = Field(min_length=1)
    teacher_focus: str = Field(min_length=1)

    @field_validator("title", "why_high_risk", "teacher_focus")
    @classmethod
    def validate_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("字段内容不能为空。")
        return cleaned


class EnhancedSessionAnalysisContent(BaseModel):
    summary: str = Field(min_length=1)
    teacher_takeaways: list[str] = Field(min_length=1)
    top_segment_insights: list[TopSegmentInsight] = Field(min_length=1)
    citations: list[AnalysisCitation] = Field(default_factory=list)
    memory_notes: list[str] = Field(default_factory=list)

    @field_validator("summary")
    @classmethod
    def validate_summary(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("summary 不能为空。")
        return cleaned

    @field_validator("teacher_takeaways", "memory_notes")
    @classmethod
    def validate_list_items(cls, values: list[str]) -> list[str]:
        cleaned = [item.strip() for item in values if item and item.strip()]
        if cleaned or values == []:
            return cleaned
        raise ValueError("列表字段不能为空。")


class EnhancedSegmentAnalysisContent(BaseModel):
    diagnosis: str = Field(min_length=1)
    evidence_story: str = Field(min_length=1)
    teacher_focus: list[str] = Field(min_length=1)
    recommended_checks: list[str] = Field(min_length=1)
    citations: list[AnalysisCitation] = Field(default_factory=list)
    memory_notes: list[str] = Field(default_factory=list)

    @field_validator("diagnosis", "evidence_story")
    @classmethod
    def validate_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("文本字段不能为空。")
        return cleaned

    @field_validator("teacher_focus", "recommended_checks", "memory_notes")
    @classmethod
    def validate_list(cls, values: list[str]) -> list[str]:
        cleaned = [item.strip() for item in values if item and item.strip()]
        if cleaned or values == []:
            return cleaned
        raise ValueError("列表字段不能为空。")


class EnhancedSessionAnalysisRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    analysis_run_id: int
    status: EnhancedAnalysisStatus
    model_name: str
    generation_mode: str
    generation_mode_label: str
    prompt_version: str
    summary: Optional[str] = None
    teacher_takeaways: list[str] = Field(default_factory=list)
    top_segment_insights: list[TopSegmentInsight] = Field(default_factory=list)
    citations: list[AnalysisCitation] = Field(default_factory=list)
    memory_notes: list[str] = Field(default_factory=list)
    generated_at: Optional[datetime] = None
    failure_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class EnhancedSegmentAnalysisRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    segment_score_id: int
    status: EnhancedAnalysisStatus
    model_name: str
    generation_mode: str
    generation_mode_label: str
    prompt_version: str
    diagnosis: Optional[str] = None
    evidence_story: Optional[str] = None
    teacher_focus: list[str] = Field(default_factory=list)
    recommended_checks: list[str] = Field(default_factory=list)
    citations: list[AnalysisCitation] = Field(default_factory=list)
    memory_notes: list[str] = Field(default_factory=list)
    generated_at: Optional[datetime] = None
    failure_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime
