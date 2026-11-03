"""
本文件的作用是：提供困惑评分与证据汇总相关的 HTTP 接口。
"""
from fastapi import APIRouter, Depends, status
from fastapi.responses import HTMLResponse, PlainTextResponse
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.schemas.analytics import (
    AnalyticsOverview,
    AnalysisRunRead,
    ReteachingInterventionCreate,
    ReteachingInterventionRead,
    SegmentAnalyticsDetail,
)
from app.schemas.enhanced_analysis import (
    EnhanceAnalysisRequest,
    EnhancedSegmentAnalysisRead,
    EnhancedSessionAnalysisRead,
)
from app.services import analytics_service, enhanced_analysis_service

router = APIRouter()


@router.post("/sessions/{session_id}/analytics/run", response_model=AnalysisRunRead)
def run_analysis(session_id: int, db: Session = Depends(get_db_session)) -> AnalysisRunRead:
    return analytics_service.run_analysis(db, session_id)


@router.get("/sessions/{session_id}/analytics/overview", response_model=AnalyticsOverview)
def get_overview(session_id: int, db: Session = Depends(get_db_session)) -> AnalyticsOverview:
    return analytics_service.get_overview(db, session_id)


@router.get("/sessions/{session_id}/analytics/report.md", response_class=PlainTextResponse)
def export_session_report(session_id: int, db: Session = Depends(get_db_session)) -> PlainTextResponse:
    content = analytics_service.export_session_report_markdown(db, session_id)
    return PlainTextResponse(
        content,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="class_confusion_radar_report.md"'},
    )


@router.get("/sessions/{session_id}/analytics/report.html", response_class=HTMLResponse)
def export_session_print_report(session_id: int, db: Session = Depends(get_db_session)) -> HTMLResponse:
    content = analytics_service.export_session_report_html(db, session_id)
    return HTMLResponse(content, media_type="text/html; charset=utf-8")


@router.get("/segments/{segment_id}/analytics", response_model=SegmentAnalyticsDetail)
def get_segment_detail(segment_id: int, db: Session = Depends(get_db_session)) -> SegmentAnalyticsDetail:
    return analytics_service.get_segment_detail(db, segment_id)


@router.post(
    "/segment-scores/{segment_score_id}/interventions",
    response_model=ReteachingInterventionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_reteaching_intervention(
    segment_score_id: int,
    payload: ReteachingInterventionCreate,
    db: Session = Depends(get_db_session),
) -> ReteachingInterventionRead:
    return analytics_service.create_reteaching_intervention(db, segment_score_id, payload)


@router.get("/segment-scores/{segment_score_id}/interventions/latest", response_model=ReteachingInterventionRead)
def get_latest_reteaching_intervention(
    segment_score_id: int,
    db: Session = Depends(get_db_session),
) -> ReteachingInterventionRead:
    return analytics_service.get_latest_reteaching_intervention(db, segment_score_id)


@router.post(
    "/interventions/{intervention_id}/verify",
    response_model=ReteachingInterventionRead,
)
def verify_reteaching_intervention(
    intervention_id: int,
    db: Session = Depends(get_db_session),
) -> ReteachingInterventionRead:
    return analytics_service.verify_reteaching_intervention(db, intervention_id)


@router.post("/sessions/{session_id}/analytics/enhance", response_model=EnhancedSessionAnalysisRead)
def create_session_enhancement(
    session_id: int,
    payload: EnhanceAnalysisRequest,
    db: Session = Depends(get_db_session),
) -> EnhancedSessionAnalysisRead:
    return enhanced_analysis_service.generate_session_enhancement(db, session_id, payload)


@router.get("/sessions/{session_id}/analytics/enhance", response_model=EnhancedSessionAnalysisRead)
def get_session_enhancement(
    session_id: int,
    db: Session = Depends(get_db_session),
) -> EnhancedSessionAnalysisRead:
    return enhanced_analysis_service.get_latest_session_enhancement(db, session_id)


@router.post("/segment-scores/{segment_score_id}/analytics/enhance", response_model=EnhancedSegmentAnalysisRead)
def create_segment_enhancement(
    segment_score_id: int,
    payload: EnhanceAnalysisRequest,
    db: Session = Depends(get_db_session),
) -> EnhancedSegmentAnalysisRead:
    return enhanced_analysis_service.generate_segment_enhancement(db, segment_score_id, payload)


@router.get("/segment-scores/{segment_score_id}/analytics/enhance", response_model=EnhancedSegmentAnalysisRead)
def get_segment_enhancement(
    segment_score_id: int,
    db: Session = Depends(get_db_session),
) -> EnhancedSegmentAnalysisRead:
    return enhanced_analysis_service.get_latest_segment_enhancement(db, segment_score_id)
