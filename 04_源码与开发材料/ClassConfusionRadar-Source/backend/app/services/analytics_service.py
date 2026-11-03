"""
本文件的作用是：实现困惑评分与证据汇总相关的核心业务处理。
"""
from datetime import datetime, timezone
from html import escape

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.analytics.scoring import (
    CONFIDENCE_LEVEL_TEXT,
    SCORE_FORMULA_TEXT,
    SIGNAL_RULES,
    SIGNAL_RULE_MAP,
    build_main_error_summary,
    build_overall_explanation,
    build_signal_item,
    compute_confusion_score,
    compute_data_coverage_ratio,
    compute_repeated_error_density,
    get_primary_signal,
    infer_confidence_level,
    infer_risk_level,
    readable_error_label,
    readable_error_text,
    summarize_errors,
)
from app.core.errors import bad_request, not_found
from app.models.analytics import AnalysisRun, ReteachingIntervention, SegmentConfusionScore
from app.models.enums import AnalysisStatus, ParseStatus, RiskLevel, SessionStatus
from app.models.records import InteractionRecord, QuizRecord, SessionStudent, SubmissionRecord
from app.models.session import ClassSession, KnowledgePoint, TeachingSegment, UploadedFile
from app.schemas.analytics import (
    AnalyticsOverview,
    AnalyticsSummary,
    AnalysisRunRead,
    ErrorStat,
    HeatmapCell,
    ReteachingInterventionCreate,
    ReteachingInterventionRead,
    RiskSegmentItem,
    ScoringRuleItem,
    SegmentAnalyticsDetail,
    SignalBreakdownItem,
)
from app.services.session_service import get_latest_completed_run, get_session_or_404


def run_analysis(db: Session, session_id: int) -> AnalysisRunRead:
    class_session = get_session_or_404(db, session_id)
    successful_upload_count = db.scalar(
        select(func.count(UploadedFile.id)).where(
            UploadedFile.session_id == session_id,
            UploadedFile.parse_status == ParseStatus.success,
        )
    ) or 0
    if successful_upload_count == 0:
        raise bad_request("请先上传并成功解析至少一个课堂数据文件后再运行分析。")

    segments = db.scalars(
        select(TeachingSegment)
        .where(TeachingSegment.session_id == session_id)
        .options(joinedload(TeachingSegment.knowledge_point))
        .order_by(TeachingSegment.display_order)
    ).all()
    if not segments:
        raise bad_request("请先创建教学分段后再运行分析。")

    analysis_run = AnalysisRun(
        session_id=session_id,
        status=AnalysisStatus.pending,
        config_json={"version": "ican_v2_normalized_confidence"},
        started_at=datetime.now(timezone.utc),
    )
    db.add(analysis_run)
    db.commit()
    db.refresh(analysis_run)

    try:
        for segment in segments:
            score_payload = build_segment_score_payload(db, class_session.id, segment)
            db.add(
                SegmentConfusionScore(
                    analysis_run_id=analysis_run.id,
                    segment_id=segment.id,
                    confusion_score=score_payload["confusion_score"],
                    risk_level=score_payload["risk_level"],
                    signal_breakdown_json={
                        "items": score_payload["signal_breakdown"],
                        "meta": score_payload["meta"],
                    },
                    error_summary_json={"items": score_payload["error_summary"]},
                )
            )

        analysis_run.status = AnalysisStatus.completed
        analysis_run.finished_at = datetime.now(timezone.utc)
        class_session.status = SessionStatus.analyzed
        db.commit()
        db.refresh(analysis_run)
        return AnalysisRunRead.model_validate(analysis_run, from_attributes=True)
    except Exception:
        db.rollback()
        failed_run = db.get(AnalysisRun, analysis_run.id)
        if failed_run:
            failed_run.status = AnalysisStatus.failed
            failed_run.finished_at = datetime.now(timezone.utc)
            db.commit()
        raise


def get_overview(db: Session, session_id: int) -> AnalyticsOverview:
    get_session_or_404(db, session_id)
    latest_run = get_latest_completed_run(db, session_id)
    if not latest_run:
        return AnalyticsOverview(
            has_analysis=False,
            latest_run_id=None,
            generated_at=None,
            score_formula=SCORE_FORMULA_TEXT,
            scoring_rules=get_scoring_rules(),
            summary=AnalyticsSummary(
                average_score=0,
                high_risk_count=0,
                critical_count=0,
                total_segments=0,
                average_data_coverage_percent=0,
                low_confidence_count=0,
            ),
            heatmap_cells=[],
            top_errors=[],
            high_risk_segments=[],
        )

    score_rows = db.scalars(
        select(SegmentConfusionScore)
        .where(SegmentConfusionScore.analysis_run_id == latest_run.id)
        .options(joinedload(SegmentConfusionScore.segment).joinedload(TeachingSegment.knowledge_point))
    ).all()

    total_score = 0.0
    total_data_coverage = 0.0
    low_confidence_count = 0
    high_risk_count = 0
    critical_count = 0
    heatmap_cells: list[HeatmapCell] = []
    error_counter: dict[str, int] = {}
    high_risk_segments: list[RiskSegmentItem] = []

    for score_row in score_rows:
        total_score += score_row.confusion_score
        if score_row.risk_level == RiskLevel.critical:
            critical_count += 1

        signal_items = normalize_signal_breakdown(score_row.signal_breakdown_json)
        meta = extract_signal_meta(signal_items, score_row.signal_breakdown_json)
        total_data_coverage += float(meta["data_coverage_percent"])
        if meta["confidence_level"] == "low":
            low_confidence_count += 1

        main_error_summary = build_main_error_summary(score_row.error_summary_json.get("items", []))
        overall_explanation = build_overall_explanation(
            confusion_score=score_row.confusion_score,
            risk_level=score_row.risk_level,
            signal_breakdown=signal_items,
            main_error_summary=main_error_summary,
            data_coverage_percent=float(meta["data_coverage_percent"]),
            confidence_level=str(meta["confidence_level"]),
        )
        primary_signal = get_primary_signal(signal_items)

        if score_row.risk_level in {RiskLevel.high, RiskLevel.critical}:
            high_risk_count += 1
            high_risk_segments.append(
                RiskSegmentItem(
                    segment_score_id=score_row.id,
                    segment_id=score_row.segment_id,
                    title=score_row.segment.title,
                    knowledge_point_name=score_row.segment.knowledge_point.name if score_row.segment.knowledge_point else None,
                    start_minute=score_row.segment.start_minute,
                    end_minute=score_row.segment.end_minute,
                    confusion_score=score_row.confusion_score,
                    risk_level=score_row.risk_level,
                    data_coverage_percent=float(meta["data_coverage_percent"]),
                    confidence_level=str(meta["confidence_level"]),
                    confidence_label=str(meta["confidence_label"]),
                    primary_signal_label=str(primary_signal["label"]) if primary_signal else None,
                    primary_signal_value_percent=float(primary_signal["value_percent"]) if primary_signal else None,
                    primary_signal_contribution_score=float(primary_signal["contribution_score"]) if primary_signal else None,
                    main_error_summary=main_error_summary,
                    overall_explanation=overall_explanation,
                )
            )

        for signal_item in signal_items:
            heatmap_cells.append(
                HeatmapCell(
                    segment_id=score_row.segment_id,
                    segment_title=score_row.segment.title,
                    signal_key=str(signal_item["key"]),
                    signal_label=str(signal_item["label"]),
                    value=float(signal_item["value_percent"]),
                    is_available=bool(signal_item.get("is_available", True)),
                )
            )

        for error_item in score_row.error_summary_json.get("items", []):
            error_counter[error_item["label"]] = error_counter.get(error_item["label"], 0) + int(error_item["count"])

    high_risk_segments.sort(key=lambda item: item.confusion_score, reverse=True)
    top_errors = [
        ErrorStat(label=readable_error_label(label), count=count)
        for label, count in sorted(error_counter.items(), key=lambda item: item[1], reverse=True)[:5]
    ]

    return AnalyticsOverview(
        has_analysis=True,
        latest_run_id=latest_run.id,
        generated_at=latest_run.finished_at,
        score_formula=SCORE_FORMULA_TEXT,
        scoring_rules=get_scoring_rules(),
        summary=AnalyticsSummary(
            average_score=round(total_score / len(score_rows), 2) if score_rows else 0,
            high_risk_count=high_risk_count,
            critical_count=critical_count,
            total_segments=len(score_rows),
            average_data_coverage_percent=round(total_data_coverage / len(score_rows), 2) if score_rows else 0,
            low_confidence_count=low_confidence_count,
        ),
        heatmap_cells=heatmap_cells,
        top_errors=top_errors,
        high_risk_segments=high_risk_segments,
    )


def get_segment_detail(db: Session, segment_id: int) -> SegmentAnalyticsDetail:
    segment = db.get(TeachingSegment, segment_id)
    if not segment:
        raise not_found("教学分段不存在。")

    latest_run = get_latest_completed_run(db, segment.session_id)
    if not latest_run:
        raise bad_request("当前课堂尚未生成分析结果。")

    score_row = db.scalars(
        select(SegmentConfusionScore)
        .where(
            SegmentConfusionScore.analysis_run_id == latest_run.id,
            SegmentConfusionScore.segment_id == segment_id,
        )
        .options(joinedload(SegmentConfusionScore.segment).joinedload(TeachingSegment.knowledge_point))
    ).first()
    if not score_row:
        raise not_found("未找到该分段的分析结果。")

    signal_items = sort_signal_breakdown(normalize_signal_breakdown(score_row.signal_breakdown_json))
    meta = extract_signal_meta(signal_items, score_row.signal_breakdown_json)
    error_summary = [
        ErrorStat(label=readable_error_label(str(item["label"])), count=int(item["count"]))
        for item in score_row.error_summary_json.get("items", [])
    ]
    main_error_summary = build_main_error_summary(score_row.error_summary_json.get("items", []))

    return SegmentAnalyticsDetail(
        segment_score_id=score_row.id,
        segment_id=segment.id,
        session_id=segment.session_id,
        title=segment.title,
        knowledge_point_name=score_row.segment.knowledge_point.name if score_row.segment.knowledge_point else None,
        start_minute=segment.start_minute,
        end_minute=segment.end_minute,
        teacher_notes=segment.teacher_notes,
        confusion_score=score_row.confusion_score,
        risk_level=score_row.risk_level,
        data_coverage_percent=float(meta["data_coverage_percent"]),
        confidence_level=str(meta["confidence_level"]),
        confidence_label=str(meta["confidence_label"]),
        score_formula=SCORE_FORMULA_TEXT,
        signal_breakdown=[SignalBreakdownItem(**item) for item in signal_items],
        error_summary=error_summary,
        main_error_summary=main_error_summary,
        overall_explanation=build_overall_explanation(
            confusion_score=score_row.confusion_score,
            risk_level=score_row.risk_level,
            signal_breakdown=signal_items,
            main_error_summary=main_error_summary,
            data_coverage_percent=float(meta["data_coverage_percent"]),
            confidence_level=str(meta["confidence_level"]),
        ),
        generated_at=latest_run.finished_at,
    )


def build_segment_score_payload(db: Session, session_id: int, segment: TeachingSegment) -> dict:
    quiz_records = db.scalars(
        select(QuizRecord).where(
            QuizRecord.session_id == session_id,
            QuizRecord.event_minute >= segment.start_minute,
            QuizRecord.event_minute < segment.end_minute,
        )
    ).all()
    submission_records = db.scalars(
        select(SubmissionRecord).where(
            SubmissionRecord.session_id == session_id,
            SubmissionRecord.event_minute >= segment.start_minute,
            SubmissionRecord.event_minute < segment.end_minute,
        )
    ).all()
    interaction_records = db.scalars(
        select(InteractionRecord).where(
            InteractionRecord.session_id == session_id,
            InteractionRecord.event_minute >= segment.start_minute,
            InteractionRecord.event_minute < segment.end_minute,
        )
    ).all()
    session_interaction_count = db.scalar(
        select(func.count(InteractionRecord.id)).where(InteractionRecord.session_id == session_id)
    ) or 0

    quiz_total = len(quiz_records)
    incorrect_count = sum(1 for record in quiz_records if not record.is_correct)
    quiz_incorrect_rate = incorrect_count / quiz_total if quiz_total else 0.0

    submission_total = len(submission_records)
    failure_count = sum(1 for record in submission_records if record.result_status != "success")
    error_records = [
        record
        for record in submission_records
        if record.result_status != "success" or record.error_type or record.error_message
    ]
    affected_students = {record.student_id for record in error_records}
    error_keys = [
        (record.student_id, record.error_type or record.result_status or "unknown")
        for record in error_records
    ]
    error_density, repeated_error_count = compute_repeated_error_density(error_keys, submission_total)
    error_count = len(error_records)
    submission_failure_rate = failure_count / submission_total if submission_total else 0.0

    roster_size = db.scalar(select(func.count(SessionStudent.id)).where(SessionStudent.session_id == session_id)) or 0
    active_students = len({record.student_id for record in interaction_records})
    has_interaction_signal = session_interaction_count > 0
    interaction_silence = (
        max(0.0, 1 - (active_students / roster_size))
        if has_interaction_signal and roster_size
        else 0.0
    )

    available_signals = {
        "quiz_incorrect_rate": quiz_total > 0,
        "submission_failure_rate": submission_total > 0,
        "error_density": submission_total > 0,
        "interaction_silence": has_interaction_signal and roster_size > 0,
    }
    available_weight_sum = sum(
        SIGNAL_RULE_MAP[key]["weight_ratio"]
        for key, is_available in available_signals.items()
        if is_available and key in SIGNAL_RULE_MAP
    )
    data_coverage_ratio = compute_data_coverage_ratio(available_signals)
    data_coverage_percent = round(data_coverage_ratio * 100, 2)
    confidence_level = infer_confidence_level(data_coverage_ratio)

    confusion_score = compute_confusion_score(
        quiz_incorrect_rate=quiz_incorrect_rate,
        submission_failure_rate=submission_failure_rate,
        error_density=error_density,
        interaction_silence=interaction_silence,
        available_signals=available_signals,
    )
    risk_level = infer_risk_level(confusion_score)

    signal_breakdown = [
        build_signal_item(
            key="quiz_incorrect_rate",
            raw_value=quiz_incorrect_rate,
            samples=quiz_total,
            is_available=available_signals["quiz_incorrect_rate"],
            available_weight_sum=available_weight_sum,
            evidence_summary=(
                f"本段测验作答 {quiz_total} 次，其中错误 {incorrect_count} 次。"
                if quiz_total
                else "本段没有测验数据，该信号不参与本次加权，并计入数据完整度。"
            ),
        ),
        build_signal_item(
            key="submission_failure_rate",
            raw_value=submission_failure_rate,
            samples=submission_total,
            is_available=available_signals["submission_failure_rate"],
            available_weight_sum=available_weight_sum,
            evidence_summary=(
                f"本段编程提交 {submission_total} 次，其中失败 {failure_count} 次。"
                if submission_total
                else "本段没有编程提交数据，该信号不参与本次加权，并计入数据完整度。"
            ),
        ),
        build_signal_item(
            key="error_density",
            raw_value=error_density,
            samples=submission_total,
            is_available=available_signals["error_density"],
            available_weight_sum=available_weight_sum,
            evidence_summary=(
                f"本段编程提交 {submission_total} 次，其中重复错误 {repeated_error_count} 次，涉及错误学生 {len(affected_students)} 人。"
                if submission_total
                else "本段没有编程提交数据，重复错误密度不参与本次加权，并计入数据完整度。"
            ),
        ),
        build_signal_item(
            key="interaction_silence",
            raw_value=interaction_silence,
            samples=len(interaction_records),
            is_available=available_signals["interaction_silence"],
            available_weight_sum=available_weight_sum,
            evidence_summary=(
                "本段没有 classroom interaction 数据，该信号不参与本次加权，并计入数据完整度。"
                if not has_interaction_signal
                else f"课堂名册 {roster_size} 人，本段有互动记录的学生 {active_students} 人。"
                if roster_size
                else "本段没有可用名册数据，互动沉默度不参与本次加权，并计入数据完整度。"
            ),
        ),
    ]

    error_summary = summarize_errors(
        [
            record.error_type or record.result_status
            for record in submission_records
            if record.result_status != "success" or record.error_type
        ]
    )

    return {
        "confusion_score": confusion_score,
        "risk_level": risk_level,
        "signal_breakdown": signal_breakdown,
        "error_summary": error_summary,
        "meta": {
            "data_coverage_ratio": data_coverage_ratio,
            "data_coverage_percent": data_coverage_percent,
            "confidence_level": confidence_level,
            "confidence_label": CONFIDENCE_LEVEL_TEXT[confidence_level],
        },
    }


def get_scoring_rules() -> list[ScoringRuleItem]:
    return [
        ScoringRuleItem(
            key=item["key"],
            label=item["label"],
            weight_percent=item["weight_percent"],
            description=item["description"],
        )
        for item in SIGNAL_RULES
    ]


def extract_signal_meta(signal_items: list[dict], signal_breakdown_json: dict) -> dict[str, float | str]:
    meta = signal_breakdown_json.get("meta") if isinstance(signal_breakdown_json, dict) else None
    if isinstance(meta, dict):
        coverage_percent = float(meta.get("data_coverage_percent", 0) or 0)
        confidence_level = str(meta.get("confidence_level") or infer_confidence_level(coverage_percent / 100))
        return {
            "data_coverage_percent": coverage_percent,
            "confidence_level": confidence_level,
            "confidence_label": str(meta.get("confidence_label") or CONFIDENCE_LEVEL_TEXT.get(confidence_level, confidence_level)),
        }

    available_signals = {str(item["key"]): bool(item.get("is_available", True)) for item in signal_items}
    coverage_ratio = compute_data_coverage_ratio(available_signals)
    confidence_level = infer_confidence_level(coverage_ratio)
    return {
        "data_coverage_percent": round(coverage_ratio * 100, 2),
        "confidence_level": confidence_level,
        "confidence_label": CONFIDENCE_LEVEL_TEXT[confidence_level],
    }


def normalize_signal_breakdown(signal_breakdown_json: dict) -> list[dict]:
    items = signal_breakdown_json.get("items") if isinstance(signal_breakdown_json, dict) else None
    if isinstance(items, list):
        normalized_items: list[dict] = []
        available_weight_sum = sum(
            SIGNAL_RULE_MAP[str(item.get("key"))]["weight_ratio"]
            for item in items
            if str(item.get("key")) in SIGNAL_RULE_MAP and bool(item.get("is_available", True))
        )
        for item in items:
            key = str(item.get("key"))
            if key not in SIGNAL_RULE_MAP:
                continue
            if "effective_weight_percent" not in item or "is_available" not in item:
                item = build_signal_item(
                    key=key,
                    raw_value=float(item.get("raw_value", 0.0) or 0.0),
                    samples=int(item.get("samples", 0) or 0),
                    evidence_summary=str(item.get("evidence_summary", "")),
                    is_available=bool(item.get("is_available", True)),
                    available_weight_sum=available_weight_sum,
                )
            normalized_items.append(item)
        return normalized_items

    # Backward compatibility for old analysis rows stored as keyed dict payloads.
    quiz = signal_breakdown_json.get("quiz", {})
    submission = signal_breakdown_json.get("submission", {})
    interaction = signal_breakdown_json.get("interaction", {})

    quiz_samples = int(quiz.get("samples", 0) or 0)
    quiz_incorrect_count = int(quiz.get("incorrect_count", 0) or 0)
    submission_samples = int(submission.get("samples", 0) or 0)
    submission_failure_count = int(submission.get("failure_count", 0) or 0)
    submission_error_count = int(submission.get("error_count", 0) or 0)
    interaction_samples = int(interaction.get("samples", 0) or 0)
    interaction_active_students = int(interaction.get("active_students", 0) or 0)
    interaction_roster_size = int(interaction.get("roster_size", 0) or 0)

    available_signals = {
        "quiz_incorrect_rate": quiz_samples > 0,
        "submission_failure_rate": submission_samples > 0,
        "error_density": submission_samples > 0,
        "interaction_silence": interaction_roster_size > 0,
    }
    available_weight_sum = sum(
        SIGNAL_RULE_MAP[key]["weight_ratio"]
        for key, is_available in available_signals.items()
        if is_available and key in SIGNAL_RULE_MAP
    )

    return [
        build_signal_item(
            key="quiz_incorrect_rate",
            raw_value=float(quiz.get("value", 0.0) or 0.0),
            samples=quiz_samples,
            is_available=available_signals["quiz_incorrect_rate"],
            available_weight_sum=available_weight_sum,
            evidence_summary=(
                f"本段测验作答 {quiz_samples} 次，其中错误 {quiz_incorrect_count} 次。"
                if quiz_samples
                else "本段没有测验数据，该信号不参与本次加权，并计入数据完整度。"
            ),
        ),
        build_signal_item(
            key="submission_failure_rate",
            raw_value=float(submission.get("value", 0.0) or 0.0),
            samples=submission_samples,
            is_available=available_signals["submission_failure_rate"],
            available_weight_sum=available_weight_sum,
            evidence_summary=(
                f"本段编程提交 {submission_samples} 次，其中失败 {submission_failure_count} 次。"
                if submission_samples
                else "本段没有编程提交数据，该信号不参与本次加权，并计入数据完整度。"
            ),
        ),
        build_signal_item(
            key="error_density",
            raw_value=float(submission.get("error_density", 0.0) or 0.0),
            samples=submission_samples,
            is_available=available_signals["error_density"],
            available_weight_sum=available_weight_sum,
            evidence_summary=(
                f"本段编程提交 {submission_samples} 次，其中错误相关记录 {submission_error_count} 次。"
                if submission_samples
                else "本段没有编程提交数据，重复错误密度不参与本次加权，并计入数据完整度。"
            ),
        ),
        build_signal_item(
            key="interaction_silence",
            raw_value=float(interaction.get("value", 0.0) or 0.0),
            samples=interaction_samples,
            is_available=available_signals["interaction_silence"],
            available_weight_sum=available_weight_sum,
            evidence_summary=(
                f"课堂名册 {interaction_roster_size} 人，本段有互动记录的学生 {interaction_active_students} 人。"
                if interaction_roster_size
                else "本段没有可用名册数据，互动沉默度不参与本次加权，并计入数据完整度。"
            ),
        ),
    ]


def sort_signal_breakdown(signal_items: list[dict]) -> list[dict]:
    return sorted(
        signal_items,
        key=lambda item: (
            not bool(item.get("is_available", True)),
            -float(item["contribution_score"]),
            -float(item["effective_weight_percent"]),
            str(item["label"]),
        ),
    )


def create_reteaching_intervention(
    db: Session,
    segment_score_id: int,
    payload: ReteachingInterventionCreate,
) -> ReteachingInterventionRead:
    segment_score = db.get(SegmentConfusionScore, segment_score_id)
    if not segment_score:
        raise not_found("分段分析结果不存在，无法记录再教学干预。")

    intervention = ReteachingIntervention(
        segment_score_id=segment_score_id,
        status=payload.status,
        plan_text=payload.plan_text,
        outcome_summary=payload.outcome_summary,
        followup_score_before=payload.followup_score_before,
        followup_score_after=payload.followup_score_after,
        executed_at=datetime.now(timezone.utc) if payload.status in {"executed", "verified"} else None,
    )
    db.add(intervention)
    db.commit()
    db.refresh(intervention)
    return ReteachingInterventionRead.model_validate(intervention, from_attributes=True)


def get_latest_reteaching_intervention(db: Session, segment_score_id: int) -> ReteachingInterventionRead:
    segment_score = db.get(SegmentConfusionScore, segment_score_id)
    if not segment_score:
        raise not_found("分段分析结果不存在。")

    intervention = db.scalars(
        select(ReteachingIntervention)
        .where(ReteachingIntervention.segment_score_id == segment_score_id)
        .order_by(ReteachingIntervention.id.desc())
    ).first()
    if not intervention:
        raise not_found("当前分段还没有记录再教学干预。")
    return ReteachingInterventionRead.model_validate(intervention, from_attributes=True)


def verify_reteaching_intervention(db: Session, intervention_id: int) -> ReteachingInterventionRead:
    intervention = db.get(ReteachingIntervention, intervention_id)
    if not intervention:
        raise not_found("再教学干预记录不存在。")

    source_score = db.get(SegmentConfusionScore, intervention.segment_score_id)
    if not source_score:
        raise not_found("原始分段分析结果不存在。")
    source_segment = db.get(TeachingSegment, source_score.segment_id)
    if not source_segment or not source_segment.knowledge_point_id:
        raise bad_request("原始分段没有绑定知识点，暂时无法自动匹配后续课堂。")

    source_point = db.get(KnowledgePoint, source_segment.knowledge_point_id)
    source_session = db.get(ClassSession, source_segment.session_id)
    if not source_point or not source_session:
        raise bad_request("原始课堂信息不完整，无法自动核验。")

    later_sessions = db.scalars(
        select(ClassSession)
        .where(
            ClassSession.id != source_session.id,
            ClassSession.course_type == source_session.course_type,
            ClassSession.class_date > source_session.class_date,
        )
        .order_by(ClassSession.class_date.asc(), ClassSession.id.asc())
    ).all()

    matched_session = None
    followup_scores: list[float] = []
    for candidate in later_sessions:
        latest_run = get_latest_completed_run(db, candidate.id)
        if not latest_run:
            continue
        rows = db.scalars(
            select(SegmentConfusionScore)
            .join(TeachingSegment, TeachingSegment.id == SegmentConfusionScore.segment_id)
            .join(KnowledgePoint, KnowledgePoint.id == TeachingSegment.knowledge_point_id)
            .where(
                SegmentConfusionScore.analysis_run_id == latest_run.id,
                KnowledgePoint.name == source_point.name,
            )
        ).all()
        if rows:
            matched_session = candidate
            followup_scores = [row.confusion_score for row in rows]
            break

    if not matched_session or not followup_scores:
        raise bad_request(
            f"还没有找到后续课堂中“{source_point.name}”的分析结果。完成下一次同课程分析后再核验即可。"
        )

    before = source_score.confusion_score
    after = round(sum(followup_scores) / len(followup_scores), 2)
    change = round(after - before, 2)
    if change < 0:
        outcome = f"后续课堂困惑得分由 {before} 降至 {after}，下降 {abs(change)} 分。"
    elif change > 0:
        outcome = f"后续课堂困惑得分由 {before} 升至 {after}，上升 {change} 分，建议继续复盘。"
    else:
        outcome = f"后续课堂困惑得分仍为 {after}，暂未观察到明显变化。"

    intervention.status = "verified"
    intervention.followup_score_before = before
    intervention.followup_score_after = after
    intervention.outcome_summary = f"{matched_session.class_date} · {matched_session.title}：{outcome}"
    if not intervention.executed_at:
        intervention.executed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(intervention)
    return ReteachingInterventionRead.model_validate(intervention, from_attributes=True)


def export_session_report_html(db: Session, session_id: int) -> str:
    session = get_session_or_404(db, session_id)
    overview = get_overview(db, session_id)
    if not overview.has_analysis:
        raise bad_request("当前课堂尚未生成分析结果，无法导出打印版报告。")

    risk_rows = []
    for item in overview.high_risk_segments:
        risk_rows.append(
            "<tr>"
            f"<td>{escape(item.title)}</td>"
            f"<td>{item.start_minute}-{item.end_minute}</td>"
            f"<td>{item.confusion_score}</td>"
            f"<td>{escape(item.confidence_label)}</td>"
            f"<td>{escape(readable_error_text(item.main_error_summary))}</td>"
            "</tr>"
        )
    if not risk_rows:
        risk_rows.append('<tr><td colspan="5">本次课堂没有高风险或极高风险分段。</td></tr>')

    error_items = "".join(
        f"<li>{escape(readable_error_label(item.label))}：{item.count} 次</li>" for item in overview.top_errors
    ) or "<li>暂无明显聚集性提交错误。</li>"

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>{escape(session.title)} 课堂复盘报告</title>
<style>
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Microsoft YaHei',sans-serif;color:#222;max-width:980px;margin:32px auto;line-height:1.65;padding:0 24px}}
h1,h2{{color:#1f2937}} .meta{{background:#f6f7f9;padding:14px 18px;border-radius:8px}}
table{{width:100%;border-collapse:collapse;margin:12px 0 24px}} th,td{{border:1px solid #d9dde3;padding:8px 10px;text-align:left}} th{{background:#f3f4f6}}
.note{{font-size:13px;color:#666}} @media print{{body{{margin:0;max-width:none}} .no-print{{display:none}}}}
</style>
</head>
<body>
<button class="no-print" onclick="window.print()">打印 / 另存为 PDF</button>
<h1>{escape(session.title)} 课堂复盘报告</h1>
<div class="meta">
课程类型：{escape(session.course_type)}<br>
课堂日期：{escape(session.class_date)}<br>
课堂时长：{session.duration_minutes} 分钟<br>
平均困惑得分：{overview.summary.average_score}<br>
平均数据完整度：{overview.summary.average_data_coverage_percent}%
</div>
<h2>高风险分段</h2>
<table><thead><tr><th>分段</th><th>时间</th><th>得分</th><th>可信度</th><th>主要错误</th></tr></thead><tbody>{''.join(risk_rows)}</tbody></table>
<h2>主要错误</h2><ul>{error_items}</ul>
<h2>评分说明</h2><p>{escape(overview.score_formula)}</p>
<p class="note">本报告由本地课堂数据生成。对外分享前请检查其中是否包含敏感信息。</p>
</body></html>"""


def export_session_report_markdown(db: Session, session_id: int) -> str:
    session = get_session_or_404(db, session_id)
    overview = get_overview(db, session_id)
    if not overview.has_analysis:
        raise bad_request("当前课堂尚未生成分析结果，无法导出复盘报告。")

    lines: list[str] = [
        f"# {session.title} 课堂复盘报告",
        "",
        "> 本报告由课堂困惑雷达在本地生成，用于课堂复盘和教学改进。",
        "",
        "## 一、课堂基本信息",
        "",
        f"- 课程类型：{session.course_type}",
        f"- 课堂日期：{session.class_date}",
        f"- 课堂时长：{session.duration_minutes} 分钟",
        f"- 分析生成时间：{overview.generated_at}",
        "",
        "## 二、分析摘要",
        "",
        f"- 平均困惑得分：{overview.summary.average_score}",
        f"- 已分析分段：{overview.summary.total_segments}",
        f"- 高风险分段：{overview.summary.high_risk_count}",
        f"- 极高风险分段：{overview.summary.critical_count}",
        f"- 平均数据完整度：{overview.summary.average_data_coverage_percent}%",
        f"- 低可信分段数：{overview.summary.low_confidence_count}",
        "",
        "## 三、评分规则",
        "",
        overview.score_formula,
        "",
    ]

    for rule in overview.scoring_rules:
        lines.append(f"- {rule.label}（基础权重 {rule.weight_percent}%）：{rule.description}")

    lines.extend(["", "## 四、高风险分段与证据", ""])
    if not overview.high_risk_segments:
        lines.append("本次课堂未识别出高风险或极高风险分段。")
    else:
        for index, item in enumerate(overview.high_risk_segments, start=1):
            lines.extend(
                [
                    f"### {index}. {item.title}",
                    "",
                    f"- 时间区间：{item.start_minute}-{item.end_minute} 分钟",
                    f"- 知识点：{item.knowledge_point_name or '-'}",
                    f"- 困惑得分：{item.confusion_score}",
                    f"- 风险等级：{item.risk_level.value if hasattr(item.risk_level, 'value') else item.risk_level}",
                    f"- 数据完整度：{item.data_coverage_percent}%（{item.confidence_label}）",
                    f"- 主导信号：{item.primary_signal_label or '-'}",
                    f"- 主要错误：{readable_error_text(item.main_error_summary)}",
                    f"- 解释：{readable_error_text(item.overall_explanation)}",
                    "",
                ]
            )

    lines.extend(["## 五、主要错误统计", ""])
    if overview.top_errors:
        for item in overview.top_errors:
            lines.append(f"- {readable_error_label(item.label)}：{item.count} 次")
    else:
        lines.append("暂无明显聚集性提交错误。")

    lines.extend(
        [
            "",
            "## 六、教师后续处理建议",
            "",
            "1. 优先复盘极高风险和高风险分段，先核对样本量与数据完整度，再决定是否重讲。",
            "2. 对主导信号为提交失败率或重复错误密度的分段，建议补充 1-2 个微练习并观察二次提交结果。",
            "3. 对主导信号为互动沉默度的分段，建议在下一次课堂加入低门槛提问、选择题或匿名反馈。",
            "4. 执行再教学后，可在系统中记录“已采纳建议/已执行干预”，形成发现—解释—干预—验证闭环。",
            "",
            "## 七、分享前检查",
            "",
            "对外分享报告或截图前，请检查姓名、学号、单位等敏感信息。",
        ]
    )
    return "\n".join(lines).strip() + "\n"
