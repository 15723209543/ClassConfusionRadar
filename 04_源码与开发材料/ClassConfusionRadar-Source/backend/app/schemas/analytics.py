"""
本文件的作用是：定义困惑评分与证据汇总接口使用的数据结构与校验规则。
"""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict

from app.models.enums import AnalysisStatus, RiskLevel


class AnalysisRunRead(BaseModel):
    id: int
    session_id: int
    status: AnalysisStatus
    started_at: Optional[datetime]
    finished_at: Optional[datetime]


class HeatmapCell(BaseModel):
    segment_id: int
    segment_title: str
    signal_key: str
    signal_label: str
    value: float
    is_available: bool = True


class ErrorStat(BaseModel):
    label: str
    count: int


class ScoringRuleItem(BaseModel):
    key: str
    label: str
    weight_percent: float
    description: str


class SignalBreakdownItem(BaseModel):
    key: str
    label: str
    weight_percent: float
    effective_weight_percent: float = 0.0
    raw_value: float
    value_percent: float
    contribution_score: float
    samples: int
    is_available: bool = True
    description: str
    evidence_summary: str


class RiskSegmentItem(BaseModel):
    segment_score_id: int
    segment_id: int
    title: str
    knowledge_point_name: Optional[str] = None
    start_minute: float
    end_minute: float
    confusion_score: float
    risk_level: RiskLevel
    data_coverage_percent: float = 0.0
    confidence_level: str = "low"
    confidence_label: str = "低可信"
    primary_signal_label: Optional[str] = None
    primary_signal_value_percent: Optional[float] = None
    primary_signal_contribution_score: Optional[float] = None
    main_error_summary: str
    overall_explanation: str


class AnalyticsSummary(BaseModel):
    average_score: float
    high_risk_count: int
    critical_count: int
    total_segments: int
    average_data_coverage_percent: float = 0.0
    low_confidence_count: int = 0


class AnalyticsOverview(BaseModel):
    has_analysis: bool
    latest_run_id: Optional[int] = None
    generated_at: Optional[datetime] = None
    score_formula: str
    scoring_rules: list[ScoringRuleItem]
    summary: AnalyticsSummary
    heatmap_cells: list[HeatmapCell]
    top_errors: list[ErrorStat]
    high_risk_segments: list[RiskSegmentItem]


class SegmentAnalyticsDetail(BaseModel):
    segment_score_id: int
    segment_id: int
    session_id: int
    title: str
    knowledge_point_name: Optional[str] = None
    start_minute: float
    end_minute: float
    teacher_notes: Optional[str] = None
    confusion_score: float
    risk_level: RiskLevel
    data_coverage_percent: float = 0.0
    confidence_level: str = "low"
    confidence_label: str = "低可信"
    score_formula: str
    signal_breakdown: list[SignalBreakdownItem]
    error_summary: list[ErrorStat]
    main_error_summary: str
    overall_explanation: str
    generated_at: Optional[datetime] = None


class ReteachingInterventionCreate(BaseModel):
    status: Literal["planned", "executed", "verified"] = "executed"
    plan_text: Optional[str] = None
    outcome_summary: Optional[str] = None
    followup_score_before: Optional[float] = None
    followup_score_after: Optional[float] = None


class ReteachingInterventionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    segment_score_id: int
    status: str
    plan_text: Optional[str] = None
    outcome_summary: Optional[str] = None
    followup_score_before: Optional[float] = None
    followup_score_after: Optional[float] = None
    executed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
