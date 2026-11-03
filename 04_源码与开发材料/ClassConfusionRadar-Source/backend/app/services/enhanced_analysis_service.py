"""
本文件的作用是：实现增强课堂解读相关的核心业务处理。
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy import false, select
from sqlalchemy.orm import Session, joinedload

from app.ai.enhanced_provider import (
    EnhancedAnalysisGenerationError,
    EnhancedSegmentContext,
    EnhancedSessionContext,
    LocalCitationCandidate,
    get_enhanced_analysis_provider,
)
from app.analytics.scoring import build_main_error_summary, build_overall_explanation, get_primary_signal
from app.core.errors import bad_request, not_found
from app.models.analytics import (
    AnalysisRun,
    EnhancedSegmentAnalysis,
    EnhancedSessionAnalysis,
    SegmentConfusionScore,
)
from app.models.enums import EnhancedAnalysisStatus, ParseStatus
from app.models.session import TeachingSegment, UploadedFile
from app.parsers.tabular import read_tabular_rows
from app.schemas.enhanced_analysis import (
    AnalysisCitation,
    EnhanceAnalysisRequest,
    EnhancedSegmentAnalysisRead,
    EnhancedSessionAnalysisRead,
    TopSegmentInsight,
)
from app.services.analytics_service import get_overview, normalize_signal_breakdown
from app.services.session_service import get_latest_completed_run, get_session_or_404


def generate_session_enhancement(
    db: Session,
    session_id: int,
    payload: EnhanceAnalysisRequest,
) -> EnhancedSessionAnalysisRead:
    class_session = get_session_or_404(db, session_id)
    latest_run = get_latest_completed_run(db, session_id)
    if not latest_run:
        raise bad_request("请先运行规则分析，再生成 API 增强分析。")

    if not payload.force_refresh:
        existing = _get_latest_ready_session_enhancement(db, latest_run.id)
        if existing:
            return _build_session_read(existing)

    provider = get_enhanced_analysis_provider()
    enhancement = EnhancedSessionAnalysis(
        analysis_run_id=latest_run.id,
        status=EnhancedAnalysisStatus.processing,
        model_name=provider.get_model_name(),
        prompt_version="v1_enhanced_session",
    )
    db.add(enhancement)
    db.commit()
    db.refresh(enhancement)

    overview = get_overview(db, session_id)
    top_segment_payloads = _build_top_segment_payloads(db, latest_run.id, overview)
    transcript_rows = _read_uploaded_material_rows(db, session_id, "transcript")
    slide_rows = _read_uploaded_material_rows(db, session_id, "ppt_timeline")
    memory_notes = _collect_session_memory_notes(db, session_id) if payload.include_memory else []

    try:
        structured_content = provider.generate_session(
            EnhancedSessionContext(
                session_title=class_session.title,
                course_type=class_session.course_type,
                class_date=class_session.class_date,
                duration_minutes=class_session.duration_minutes,
                notes=class_session.notes,
                score_formula=overview.score_formula,
                average_score=overview.summary.average_score,
                high_risk_count=overview.summary.high_risk_count,
                critical_count=overview.summary.critical_count,
                total_segments=overview.summary.total_segments,
                top_segments=top_segment_payloads,
                transcript_excerpt=_build_session_transcript_excerpt(transcript_rows),
                slide_window_summary=_build_slide_window_summary(slide_rows),
                memory_notes=memory_notes,
                citation_candidates=_build_session_citation_candidates(
                    session_id=session_id,
                    transcript_rows=transcript_rows,
                    slide_rows=slide_rows,
                    top_segments=top_segment_payloads,
                ),
                allow_web_search=payload.allow_web_search,
            )
        )
    except Exception as exc:
        db.rollback()
        failed = db.get(EnhancedSessionAnalysis, enhancement.id)
        if not failed:
            raise
        failed.status = EnhancedAnalysisStatus.failed
        failed.failure_reason = _get_failure_reason(exc)
        failed.structured_content = None
        failed.citations = []
        failed.memory_notes = []
        db.commit()
        db.refresh(failed)
        return _build_session_read(failed)

    enhancement = db.get(EnhancedSessionAnalysis, enhancement.id)
    if not enhancement:
        raise not_found("课堂增强分析记录不存在。")

    enhancement.status = EnhancedAnalysisStatus.ready
    enhancement.structured_content = structured_content.model_dump(mode="json", exclude={"citations", "memory_notes"})
    enhancement.citations = [item.model_dump(mode="json") for item in structured_content.citations]
    enhancement.memory_notes = structured_content.memory_notes
    enhancement.failure_reason = None
    enhancement.generated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(enhancement)
    return _build_session_read(enhancement)


def get_latest_session_enhancement(db: Session, session_id: int) -> EnhancedSessionAnalysisRead:
    latest_run = get_latest_completed_run(db, session_id)
    if not latest_run:
        raise not_found("当前课堂尚未生成规则分析结果。")

    enhancement = _get_latest_session_enhancement_row(db, latest_run.id)
    if not enhancement:
        raise not_found("当前课堂尚未生成 API 增强分析结果。")
    return _build_session_read(enhancement)


def generate_segment_enhancement(
    db: Session,
    segment_score_id: int,
    payload: EnhanceAnalysisRequest,
) -> EnhancedSegmentAnalysisRead:
    score_row = _get_segment_score_or_404(db, segment_score_id)
    session_id = score_row.segment.session_id

    if not payload.force_refresh:
        existing = _get_latest_ready_segment_enhancement(db, segment_score_id)
        if existing:
            return _build_segment_read(existing)

    provider = get_enhanced_analysis_provider()
    enhancement = EnhancedSegmentAnalysis(
        segment_score_id=segment_score_id,
        status=EnhancedAnalysisStatus.processing,
        model_name=provider.get_model_name(),
        prompt_version="v1_enhanced_segment",
    )
    db.add(enhancement)
    db.commit()
    db.refresh(enhancement)

    signal_breakdown = normalize_signal_breakdown(score_row.signal_breakdown_json)
    transcript_rows = _read_uploaded_material_rows(db, session_id, "transcript")
    slide_rows = _read_uploaded_material_rows(db, session_id, "ppt_timeline")
    segment_transcript_rows = _filter_material_rows_by_segment(transcript_rows, score_row.segment)
    segment_slide_rows = _filter_material_rows_by_segment(slide_rows, score_row.segment)
    memory_notes = _collect_segment_memory_notes(db, session_id, segment_score_id) if payload.include_memory else []

    try:
        structured_content = provider.generate_segment(
            EnhancedSegmentContext(
                segment_title=score_row.segment.title,
                knowledge_point_name=score_row.segment.knowledge_point.name if score_row.segment.knowledge_point else None,
                risk_level=score_row.risk_level.value,
                confusion_score=score_row.confusion_score,
                score_formula=get_overview(db, session_id).score_formula,
                signal_breakdown=signal_breakdown,
                error_summary=score_row.error_summary_json.get("items", []),
                teacher_notes=score_row.segment.teacher_notes,
                transcript_excerpt=_build_segment_transcript_excerpt(segment_transcript_rows),
                slide_window_summary=_build_slide_window_summary(segment_slide_rows),
                memory_notes=memory_notes,
                citation_candidates=_build_segment_citation_candidates(
                    segment_score_id=segment_score_id,
                    segment=score_row.segment,
                    signal_breakdown=signal_breakdown,
                    transcript_rows=segment_transcript_rows,
                    slide_rows=segment_slide_rows,
                ),
                allow_web_search=payload.allow_web_search,
            )
        )
    except Exception as exc:
        db.rollback()
        failed = db.get(EnhancedSegmentAnalysis, enhancement.id)
        if not failed:
            raise
        failed.status = EnhancedAnalysisStatus.failed
        failed.failure_reason = _get_failure_reason(exc)
        failed.structured_content = None
        failed.citations = []
        failed.memory_notes = []
        db.commit()
        db.refresh(failed)
        return _build_segment_read(failed)

    enhancement = db.get(EnhancedSegmentAnalysis, enhancement.id)
    if not enhancement:
        raise not_found("分段增强分析记录不存在。")

    enhancement.status = EnhancedAnalysisStatus.ready
    enhancement.structured_content = structured_content.model_dump(mode="json", exclude={"citations", "memory_notes"})
    enhancement.citations = [item.model_dump(mode="json") for item in structured_content.citations]
    enhancement.memory_notes = structured_content.memory_notes
    enhancement.failure_reason = None
    enhancement.generated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(enhancement)
    return _build_segment_read(enhancement)


def get_latest_segment_enhancement(db: Session, segment_score_id: int) -> EnhancedSegmentAnalysisRead:
    _get_segment_score_or_404(db, segment_score_id)
    enhancement = _get_latest_segment_enhancement_row(db, segment_score_id)
    if not enhancement:
        raise not_found("当前分段尚未生成 API 增强分析结果。")
    return _build_segment_read(enhancement)


def _get_segment_score_or_404(db: Session, segment_score_id: int) -> SegmentConfusionScore:
    score_row = db.scalars(
        select(SegmentConfusionScore)
        .where(SegmentConfusionScore.id == segment_score_id)
        .options(joinedload(SegmentConfusionScore.segment).joinedload(TeachingSegment.knowledge_point))
    ).first()
    if not score_row:
        raise not_found("分析分数记录不存在。")
    return score_row


def _get_latest_session_enhancement_row(db: Session, analysis_run_id: int) -> Optional[EnhancedSessionAnalysis]:
    return db.scalars(
        select(EnhancedSessionAnalysis)
        .where(EnhancedSessionAnalysis.analysis_run_id == analysis_run_id)
        .order_by(EnhancedSessionAnalysis.id.desc())
    ).first()


def _get_latest_ready_session_enhancement(db: Session, analysis_run_id: int) -> Optional[EnhancedSessionAnalysis]:
    return db.scalars(
        select(EnhancedSessionAnalysis)
        .where(
            EnhancedSessionAnalysis.analysis_run_id == analysis_run_id,
            EnhancedSessionAnalysis.status == EnhancedAnalysisStatus.ready,
        )
        .order_by(EnhancedSessionAnalysis.id.desc())
    ).first()


def _get_latest_segment_enhancement_row(db: Session, segment_score_id: int) -> Optional[EnhancedSegmentAnalysis]:
    return db.scalars(
        select(EnhancedSegmentAnalysis)
        .where(EnhancedSegmentAnalysis.segment_score_id == segment_score_id)
        .order_by(EnhancedSegmentAnalysis.id.desc())
    ).first()


def _get_latest_ready_segment_enhancement(
    db: Session, segment_score_id: int
) -> Optional[EnhancedSegmentAnalysis]:
    return db.scalars(
        select(EnhancedSegmentAnalysis)
        .where(
            EnhancedSegmentAnalysis.segment_score_id == segment_score_id,
            EnhancedSegmentAnalysis.status == EnhancedAnalysisStatus.ready,
        )
        .order_by(EnhancedSegmentAnalysis.id.desc())
    ).first()


def _read_uploaded_material_rows(db: Session, session_id: int, file_kind: str) -> list[dict]:
    uploaded_file = db.scalars(
        select(UploadedFile)
        .where(
            UploadedFile.session_id == session_id,
            UploadedFile.file_kind == file_kind,
            UploadedFile.parse_status == ParseStatus.success,
        )
        .order_by(UploadedFile.id.desc())
    ).first()
    if not uploaded_file:
        return []

    file_path = Path(uploaded_file.storage_path)
    if not file_path.exists():
        return []

    return read_tabular_rows(uploaded_file.original_name, file_path.read_bytes())


def _build_session_transcript_excerpt(transcript_rows: list[dict]) -> str:
    if not transcript_rows:
        return "当前课堂没有 transcript 材料。"

    excerpts = [str(row.get("text", "")).strip() for row in transcript_rows[:3]]
    return " ".join(text for text in excerpts if text)[:800]


def _build_segment_transcript_excerpt(transcript_rows: list[dict]) -> str:
    if not transcript_rows:
        return "当前分段没有 transcript 片段。"

    excerpts = [str(row.get("text", "")).strip() for row in transcript_rows[:3]]
    return " ".join(text for text in excerpts if text)[:600]


def _build_slide_window_summary(slide_rows: list[dict]) -> str:
    if not slide_rows:
        return "当前课堂没有 slide window 材料。"

    summaries = []
    for row in slide_rows[:4]:
        title = str(row.get("slide_title") or f"Slide {row.get('slide_index', '?')}").strip()
        start_minute = row.get("start_minute", "?")
        end_minute = row.get("end_minute", "?")
        summaries.append(f"{title}（{start_minute}-{end_minute} 分钟）")
    return "；".join(summaries)


def _build_session_citation_candidates(
    session_id: int,
    transcript_rows: list[dict],
    slide_rows: list[dict],
    top_segments: list[dict],
) -> list[LocalCitationCandidate]:
    candidates: list[LocalCitationCandidate] = []

    for index, row in enumerate(transcript_rows[:2], start=1):
        text = str(row.get("text", "")).strip()
        if text:
            candidates.append(
                LocalCitationCandidate(
                    title=f"Transcript 片段 {index}",
                    source_type="uploaded_transcript",
                    url=f"local://sessions/{session_id}/transcript",
                    excerpt=text[:220],
                )
            )

    for row in slide_rows[:2]:
        title = str(row.get("slide_title") or f"Slide {row.get('slide_index', '?')}").strip()
        candidates.append(
            LocalCitationCandidate(
                title=title,
                source_type="uploaded_slide_window",
                url=f"local://sessions/{session_id}/ppt_timeline",
                excerpt=f"{title}，时间窗 {row.get('start_minute')} - {row.get('end_minute')} 分钟。",
            )
        )

    for item in top_segments[:2]:
        explanation = str(item.get("overall_explanation", "")).strip()
        if explanation:
            candidates.append(
                LocalCitationCandidate(
                    title=str(item.get("title", "高风险分段")),
                    source_type="rule_signal",
                    url=f"local://sessions/{session_id}/segment-scores/{item.get('segment_score_id', 'unknown')}",
                    excerpt=explanation[:220],
                )
            )

    return candidates


def _build_top_segment_payloads(db: Session, analysis_run_id: int, overview) -> list[dict]:
    top_segments = [item.model_dump(mode="json") for item in overview.high_risk_segments[:3]]
    if top_segments:
        return top_segments

    score_rows = db.scalars(
        select(SegmentConfusionScore)
        .where(SegmentConfusionScore.analysis_run_id == analysis_run_id)
        .options(joinedload(SegmentConfusionScore.segment).joinedload(TeachingSegment.knowledge_point))
        .order_by(SegmentConfusionScore.confusion_score.desc())
    ).all()

    payloads: list[dict] = []
    for score_row in score_rows[:3]:
        signal_items = normalize_signal_breakdown(score_row.signal_breakdown_json)
        primary_signal = get_primary_signal(signal_items)
        main_error_summary = build_main_error_summary(score_row.error_summary_json.get("items", []))
        payloads.append(
            {
                "segment_score_id": score_row.id,
                "segment_id": score_row.segment_id,
                "title": score_row.segment.title,
                "knowledge_point_name": score_row.segment.knowledge_point.name
                if score_row.segment.knowledge_point
                else None,
                "start_minute": score_row.segment.start_minute,
                "end_minute": score_row.segment.end_minute,
                "confusion_score": score_row.confusion_score,
                "risk_level": score_row.risk_level.value,
                "primary_signal_label": str(primary_signal["label"]) if primary_signal else None,
                "primary_signal_value_percent": float(primary_signal["value_percent"]) if primary_signal else None,
                "primary_signal_contribution_score": float(primary_signal["contribution_score"])
                if primary_signal
                else None,
                "main_error_summary": main_error_summary,
                "overall_explanation": build_overall_explanation(
                    confusion_score=score_row.confusion_score,
                    risk_level=score_row.risk_level,
                    signal_breakdown=signal_items,
                    main_error_summary=main_error_summary,
                ),
            }
        )
    return payloads


def _build_segment_citation_candidates(
    segment_score_id: int,
    segment: TeachingSegment,
    signal_breakdown: list[dict],
    transcript_rows: list[dict],
    slide_rows: list[dict],
) -> list[LocalCitationCandidate]:
    candidates: list[LocalCitationCandidate] = []

    for row in transcript_rows[:2]:
        text = str(row.get("text", "")).strip()
        if text:
            candidates.append(
                LocalCitationCandidate(
                    title=f"{segment.title} transcript 证据",
                    source_type="uploaded_transcript",
                    url=f"local://segment-scores/{segment_score_id}/transcript",
                    excerpt=text[:220],
                )
            )

    for row in slide_rows[:2]:
        title = str(row.get("slide_title") or f"Slide {row.get('slide_index', '?')}").strip()
        candidates.append(
            LocalCitationCandidate(
                title=title,
                source_type="uploaded_slide_window",
                url=f"local://segment-scores/{segment_score_id}/ppt_timeline",
                excerpt=f"{title}，时间窗 {row.get('start_minute')} - {row.get('end_minute')} 分钟。",
            )
        )

    primary_signal = get_primary_signal(signal_breakdown)
    if primary_signal:
        candidates.append(
            LocalCitationCandidate(
                title=str(primary_signal["label"]),
                source_type="rule_signal",
                url=f"local://segment-scores/{segment_score_id}/rule-signal",
                excerpt=str(primary_signal.get("evidence_summary") or ""),
            )
        )

    return [candidate for candidate in candidates if candidate.excerpt]


def _collect_session_memory_notes(db: Session, session_id: int) -> list[str]:
    latest_run = get_latest_completed_run(db, session_id)
    if not latest_run:
        return []

    ready_session_analyses = db.scalars(
        select(EnhancedSessionAnalysis)
        .where(
            EnhancedSessionAnalysis.analysis_run_id == latest_run.id,
            EnhancedSessionAnalysis.status == EnhancedAnalysisStatus.ready,
        )
        .order_by(EnhancedSessionAnalysis.id.desc())
    ).all()

    score_ids = db.scalars(
        select(SegmentConfusionScore.id)
        .join(AnalysisRun, AnalysisRun.id == SegmentConfusionScore.analysis_run_id)
        .where(AnalysisRun.session_id == session_id)
    ).all()
    ready_segment_analyses = db.scalars(
        select(EnhancedSegmentAnalysis)
        .where(
            EnhancedSegmentAnalysis.segment_score_id.in_(score_ids) if score_ids else false(),
            EnhancedSegmentAnalysis.status == EnhancedAnalysisStatus.ready,
        )
        .order_by(EnhancedSegmentAnalysis.id.desc())
    ).all()

    notes: list[str] = []
    for item in ready_session_analyses[:3]:
        notes.extend(item.memory_notes or [])
    for item in ready_segment_analyses[:3]:
        notes.extend(item.memory_notes or [])
    return _deduplicate_memory_notes(notes)[:8]


def _collect_segment_memory_notes(db: Session, session_id: int, segment_score_id: int) -> list[str]:
    latest_session_memory = _collect_session_memory_notes(db, session_id)
    sibling_analyses = db.scalars(
        select(EnhancedSegmentAnalysis)
        .join(SegmentConfusionScore, SegmentConfusionScore.id == EnhancedSegmentAnalysis.segment_score_id)
        .join(AnalysisRun, AnalysisRun.id == SegmentConfusionScore.analysis_run_id)
        .where(
            AnalysisRun.session_id == session_id,
            EnhancedSegmentAnalysis.segment_score_id != segment_score_id,
            EnhancedSegmentAnalysis.status == EnhancedAnalysisStatus.ready,
        )
        .order_by(EnhancedSegmentAnalysis.id.desc())
    ).all()

    notes = list(latest_session_memory)
    for item in sibling_analyses[:3]:
        notes.extend(item.memory_notes or [])
    return _deduplicate_memory_notes(notes)[:8]


def _filter_material_rows_by_segment(rows: list[dict], segment: TeachingSegment) -> list[dict]:
    filtered: list[dict] = []
    for row in rows:
        start_value = row.get("start_minute")
        end_value = row.get("end_minute")
        if start_value is None or end_value is None:
            continue
        try:
            start_minute = float(start_value)
            end_minute = float(end_value)
        except (TypeError, ValueError):
            continue
        if end_minute > segment.start_minute and start_minute < segment.end_minute:
            filtered.append(row)
    return filtered


def _build_session_read(item: EnhancedSessionAnalysis) -> EnhancedSessionAnalysisRead:
    structured_content = item.structured_content or {}
    return EnhancedSessionAnalysisRead(
        id=item.id,
        analysis_run_id=item.analysis_run_id,
        status=item.status,
        model_name=item.model_name,
        generation_mode=item.generation_mode,
        generation_mode_label=item.generation_mode_label,
        prompt_version=item.prompt_version,
        summary=structured_content.get("summary"),
        teacher_takeaways=structured_content.get("teacher_takeaways") or [],
        top_segment_insights=[
            TopSegmentInsight.model_validate(row) for row in structured_content.get("top_segment_insights") or []
        ],
        citations=[AnalysisCitation.model_validate(row) for row in item.citations or []],
        memory_notes=item.memory_notes or [],
        generated_at=item.generated_at,
        failure_reason=item.failure_reason,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _build_segment_read(item: EnhancedSegmentAnalysis) -> EnhancedSegmentAnalysisRead:
    structured_content = item.structured_content or {}
    return EnhancedSegmentAnalysisRead(
        id=item.id,
        segment_score_id=item.segment_score_id,
        status=item.status,
        model_name=item.model_name,
        generation_mode=item.generation_mode,
        generation_mode_label=item.generation_mode_label,
        prompt_version=item.prompt_version,
        diagnosis=structured_content.get("diagnosis"),
        evidence_story=structured_content.get("evidence_story"),
        teacher_focus=structured_content.get("teacher_focus") or [],
        recommended_checks=structured_content.get("recommended_checks") or [],
        citations=[AnalysisCitation.model_validate(row) for row in item.citations or []],
        memory_notes=item.memory_notes or [],
        generated_at=item.generated_at,
        failure_reason=item.failure_reason,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _deduplicate_memory_notes(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        cleaned = value.strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        result.append(cleaned)
    return result


def _get_failure_reason(exc: Exception) -> str:
    if isinstance(exc, EnhancedAnalysisGenerationError):
        return exc.message
    return f"增强分析服务异常：{exc}"
