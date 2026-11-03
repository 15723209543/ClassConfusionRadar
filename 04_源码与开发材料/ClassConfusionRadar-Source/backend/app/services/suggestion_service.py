"""
本文件的作用是：实现再教学建议相关的核心业务处理。
"""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.ai.provider import (
    SuggestionContext,
    SuggestionGenerationError,
    get_suggestion_provider,
    render_structured_suggestion_markdown,
)
from app.core.errors import not_found
from app.models.analytics import ReteachingSuggestion, SegmentConfusionScore
from app.models.enums import SuggestionStatus
from app.models.session import TeachingSegment
from app.services.analytics_service import normalize_signal_breakdown


def generate_suggestion(db: Session, segment_score_id: int) -> ReteachingSuggestion:
    score_row = db.scalars(
        select(SegmentConfusionScore)
        .where(SegmentConfusionScore.id == segment_score_id)
        .options(joinedload(SegmentConfusionScore.segment).joinedload(TeachingSegment.knowledge_point))
    ).first()
    if not score_row:
        raise not_found("分析分数记录不存在。")

    provider = get_suggestion_provider()
    suggestion = ReteachingSuggestion(
        segment_score_id=segment_score_id,
        status=SuggestionStatus.processing,
        model_name=provider.get_model_name(),
        prompt_version="v2_structured",
    )
    db.add(suggestion)
    db.commit()
    db.refresh(suggestion)

    signal_breakdown = normalize_signal_breakdown(score_row.signal_breakdown_json)

    try:
        structured_content = provider.generate(
            SuggestionContext(
                segment_title=score_row.segment.title,
                knowledge_point_name=score_row.segment.knowledge_point.name if score_row.segment.knowledge_point else None,
                risk_level=score_row.risk_level.value,
                confusion_score=score_row.confusion_score,
                signal_breakdown=signal_breakdown,
                error_summary=score_row.error_summary_json.get("items", []),
                teacher_notes=score_row.segment.teacher_notes,
            )
        )
    except Exception as exc:
        db.rollback()
        failed = db.get(ReteachingSuggestion, suggestion.id)
        if not failed:
            raise

        failure_reason = _get_failure_reason(exc)
        failed.status = SuggestionStatus.failed
        failed.failure_reason = failure_reason
        failed.structured_content = None
        failed.suggestion_markdown = f"建议生成失败：{failure_reason}"
        db.commit()
        db.refresh(failed)
        return failed

    suggestion = db.get(ReteachingSuggestion, suggestion.id)
    if not suggestion:
        raise not_found("建议记录不存在。")

    suggestion.status = SuggestionStatus.ready
    suggestion.structured_content = structured_content.model_dump(mode="json")
    suggestion.suggestion_markdown = render_structured_suggestion_markdown(structured_content)
    suggestion.failure_reason = None
    suggestion.generated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(suggestion)
    return suggestion


def get_latest_suggestion(db: Session, segment_score_id: int) -> ReteachingSuggestion:
    suggestion = db.scalars(
        select(ReteachingSuggestion)
        .where(ReteachingSuggestion.segment_score_id == segment_score_id)
        .order_by(ReteachingSuggestion.id.desc())
    ).first()
    if not suggestion:
        raise not_found("当前分段尚未生成教学建议。")
    return suggestion


def _get_failure_reason(exc: Exception) -> str:
    if isinstance(exc, SuggestionGenerationError):
        return exc.message
    return f"生成服务异常：{exc}"
