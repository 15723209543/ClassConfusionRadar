"""
本文件的作用是：定义困惑评分与证据汇总相关的数据库模型或枚举。
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, Float, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IdMixin, TimestampMixin
from app.models.enums import AnalysisStatus, EnhancedAnalysisStatus, RiskLevel, SuggestionStatus


class AnalysisRun(Base, IdMixin, TimestampMixin):
    __tablename__ = "analysis_runs"

    session_id: Mapped[int] = mapped_column(ForeignKey("class_sessions.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[AnalysisStatus] = mapped_column(
        Enum(AnalysisStatus, name="analysis_status"),
        default=AnalysisStatus.pending,
        nullable=False,
    )
    config_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    session = relationship("ClassSession", back_populates="analysis_runs")
    segment_scores = relationship("SegmentConfusionScore", back_populates="analysis_run", cascade="all, delete-orphan")
    enhanced_analyses = relationship(
        "EnhancedSessionAnalysis", back_populates="analysis_run", cascade="all, delete-orphan"
    )


class SegmentConfusionScore(Base, IdMixin, TimestampMixin):
    __tablename__ = "segment_confusion_scores"

    analysis_run_id: Mapped[int] = mapped_column(ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False)
    segment_id: Mapped[int] = mapped_column(ForeignKey("teaching_segments.id", ondelete="CASCADE"), nullable=False)
    confusion_score: Mapped[float] = mapped_column(nullable=False)
    risk_level: Mapped[RiskLevel] = mapped_column(Enum(RiskLevel, name="risk_level"), nullable=False)
    signal_breakdown_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    error_summary_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    analysis_run = relationship("AnalysisRun", back_populates="segment_scores")
    segment = relationship("TeachingSegment", back_populates="confusion_scores")
    suggestions = relationship("ReteachingSuggestion", back_populates="segment_score", cascade="all, delete-orphan")
    interventions = relationship("ReteachingIntervention", back_populates="segment_score", cascade="all, delete-orphan")
    enhanced_analyses = relationship(
        "EnhancedSegmentAnalysis", back_populates="segment_score", cascade="all, delete-orphan"
    )


class ReteachingSuggestion(Base, IdMixin, TimestampMixin):
    __tablename__ = "reteaching_suggestions"

    segment_score_id: Mapped[int] = mapped_column(
        ForeignKey("segment_confusion_scores.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[SuggestionStatus] = mapped_column(
        Enum(SuggestionStatus, name="suggestion_status"),
        default=SuggestionStatus.processing,
        nullable=False,
    )
    model_name: Mapped[str] = mapped_column(nullable=False)
    prompt_version: Mapped[str] = mapped_column(nullable=False, default="v1")
    structured_content: Mapped[Optional[dict]] = mapped_column(JSON)
    suggestion_markdown: Mapped[Optional[str]] = mapped_column(Text)
    failure_reason: Mapped[Optional[str]] = mapped_column(Text)
    generated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    segment_score = relationship("SegmentConfusionScore", back_populates="suggestions")

    @property
    def generation_mode(self) -> str:
        return "offline_rule" if self.model_name.startswith("offline-") else "ai"

    @property
    def generation_mode_label(self) -> str:
        return "离线可解释建议" if self.generation_mode == "offline_rule" else "AI 增强建议"


class EnhancedSessionAnalysis(Base, IdMixin, TimestampMixin):
    __tablename__ = "enhanced_session_analyses"

    analysis_run_id: Mapped[int] = mapped_column(ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[EnhancedAnalysisStatus] = mapped_column(
        Enum(EnhancedAnalysisStatus, name="enhanced_analysis_status"),
        default=EnhancedAnalysisStatus.processing,
        nullable=False,
    )
    model_name: Mapped[str] = mapped_column(nullable=False)
    prompt_version: Mapped[str] = mapped_column(nullable=False, default="v1")
    structured_content: Mapped[Optional[dict]] = mapped_column(JSON)
    citations: Mapped[Optional[list]] = mapped_column(JSON)
    memory_notes: Mapped[Optional[list]] = mapped_column(JSON)
    failure_reason: Mapped[Optional[str]] = mapped_column(Text)
    generated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    analysis_run = relationship("AnalysisRun", back_populates="enhanced_analyses")

    @property
    def generation_mode(self) -> str:
        return "offline_rule" if self.model_name.startswith("offline-") else "ai"

    @property
    def generation_mode_label(self) -> str:
        return "离线解释" if self.generation_mode == "offline_rule" else "AI 增强"


class EnhancedSegmentAnalysis(Base, IdMixin, TimestampMixin):
    __tablename__ = "enhanced_segment_analyses"

    segment_score_id: Mapped[int] = mapped_column(
        ForeignKey("segment_confusion_scores.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[EnhancedAnalysisStatus] = mapped_column(
        Enum(EnhancedAnalysisStatus, name="enhanced_analysis_status"),
        default=EnhancedAnalysisStatus.processing,
        nullable=False,
    )
    model_name: Mapped[str] = mapped_column(nullable=False)
    prompt_version: Mapped[str] = mapped_column(nullable=False, default="v1")
    structured_content: Mapped[Optional[dict]] = mapped_column(JSON)
    citations: Mapped[Optional[list]] = mapped_column(JSON)
    memory_notes: Mapped[Optional[list]] = mapped_column(JSON)
    failure_reason: Mapped[Optional[str]] = mapped_column(Text)
    generated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    segment_score = relationship("SegmentConfusionScore", back_populates="enhanced_analyses")

    @property
    def generation_mode(self) -> str:
        return "offline_rule" if self.model_name.startswith("offline-") else "ai"

    @property
    def generation_mode_label(self) -> str:
        return "离线解释" if self.generation_mode == "offline_rule" else "AI 增强"


class ReteachingIntervention(Base, IdMixin, TimestampMixin):
    __tablename__ = "reteaching_interventions"

    segment_score_id: Mapped[int] = mapped_column(
        ForeignKey("segment_confusion_scores.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), default="executed", nullable=False)
    plan_text: Mapped[Optional[str]] = mapped_column(Text)
    outcome_summary: Mapped[Optional[str]] = mapped_column(Text)
    followup_score_before: Mapped[Optional[float]] = mapped_column(Float)
    followup_score_after: Mapped[Optional[float]] = mapped_column(Float)
    executed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    segment_score = relationship("SegmentConfusionScore", back_populates="interventions")
