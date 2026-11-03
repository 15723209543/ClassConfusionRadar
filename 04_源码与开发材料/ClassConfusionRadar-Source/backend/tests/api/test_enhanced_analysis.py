"""
本文件的作用是：验证增强课堂解读相关功能在典型与异常场景下的行为。
"""
from app.ai.enhanced_provider import EnhancedAnalysisGenerationError
from app.api.v1.routes import analytics as analytics_routes


def create_session_with_segment(client, *, title: str = "Public Demo Session"):
    session_response = client.post(
        "/api/v1/sessions",
        json={
            "title": title,
            "course_type": "python",
            "class_date": "2026-04-17",
            "duration_minutes": 60,
            "notes": "public demo enhanced analysis test",
        },
    )
    assert session_response.status_code == 201
    session_id = session_response.json()["id"]

    knowledge_point_response = client.post(
        f"/api/v1/sessions/{session_id}/knowledge-points",
        json={
            "name": "Loops",
            "topic_area": "Control Flow",
            "display_order": 1,
        },
    )
    assert knowledge_point_response.status_code == 201
    knowledge_point_id = knowledge_point_response.json()["id"]

    segment_response = client.post(
        f"/api/v1/sessions/{session_id}/segments",
        json={
            "title": "Loop practice window",
            "knowledge_point_id": knowledge_point_id,
            "start_minute": 10,
            "end_minute": 30,
            "display_order": 1,
        },
    )
    assert segment_response.status_code == 201
    return session_id, segment_response.json()["id"]


def upload_public_demo_minimum(client, session_id: int):
    transcript_csv = (
        "start_minute,end_minute,speaker,text\n"
        '0,4,David,"Today we will look at loops and repeated actions in Python."\n'
        '4,8,David,"We will compare while loops and for loops with simple examples."\n'
        '8,12,David,"Notice how a loop condition decides when the repetition stops."\n'
    )
    ppt_csv = (
        "slide_index,start_minute,end_minute,slide_title\n"
        "1,0,6,Introduction to Loops\n"
        "2,6,12,While and For Comparisons\n"
        "3,12,20,Practice and Common Mistakes\n"
    )
    submission_csv = (
        "student_code,student_name,task_name,language,result_status,error_type,error_message,event_minute\n"
        "A01,A01,ITP1_3_A Hello World,python,wrong_answer,Wrong Answer,expected repeated output,14\n"
        "A02,A02,ITP1_3_B Print Test Cases,python,success,,,18\n"
        "A03,A03,ITP1_2_B Range Check,python,runtime_error,Runtime Error,bad loop boundary,22\n"
    )

    for file_kind, content in [
        ("transcript", transcript_csv),
        ("ppt_timeline", ppt_csv),
        ("submission", submission_csv),
    ]:
        response = client.post(
            f"/api/v1/sessions/{session_id}/files",
            files={"file": (f"{file_kind}.csv", content, "text/csv")},
            data={"file_kind": file_kind},
        )
        assert response.status_code == 201
        assert response.json()["parse_status"] == "success"


def test_public_demo_style_inputs_treat_missing_signals_as_unavailable(client):
    session_id, segment_id = create_session_with_segment(client)
    upload_public_demo_minimum(client, session_id)

    analysis_response = client.post(f"/api/v1/sessions/{session_id}/analytics/run")
    assert analysis_response.status_code == 200

    detail_response = client.get(f"/api/v1/segments/{segment_id}/analytics")
    assert detail_response.status_code == 200
    payload = detail_response.json()

    signals = {item["key"]: item for item in payload["signal_breakdown"]}
    assert signals["quiz_incorrect_rate"]["value_percent"] == 0
    assert signals["quiz_incorrect_rate"]["is_available"] is False
    assert "不参与本次加权" in signals["quiz_incorrect_rate"]["evidence_summary"]
    assert signals["interaction_silence"]["value_percent"] == 0
    assert signals["interaction_silence"]["is_available"] is False
    assert "不参与本次加权" in signals["interaction_silence"]["evidence_summary"]
    assert signals["submission_failure_rate"]["value_percent"] > 0
    assert payload["data_coverage_percent"] == 55
    assert payload["confidence_level"] == "medium"


def test_enhanced_analysis_endpoints_return_structured_results(client):
    session_id, segment_id = create_session_with_segment(client, title="Enhanced Demo Session")
    upload_public_demo_minimum(client, session_id)

    analysis_response = client.post(f"/api/v1/sessions/{session_id}/analytics/run")
    assert analysis_response.status_code == 200

    overview_response = client.get(f"/api/v1/sessions/{session_id}/analytics/overview")
    assert overview_response.status_code == 200
    detail_response = client.get(f"/api/v1/segments/{segment_id}/analytics")
    assert detail_response.status_code == 200
    segment_score_id = detail_response.json()["segment_score_id"]

    session_enhance_response = client.post(
        f"/api/v1/sessions/{session_id}/analytics/enhance",
        json={"allow_web_search": False, "include_memory": True},
    )
    assert session_enhance_response.status_code == 200
    session_payload = session_enhance_response.json()
    assert session_payload["status"] == "ready"
    assert session_payload["summary"]
    assert session_payload["top_segment_insights"]
    assert session_payload["top_segment_insights"][0]["segment_id"] == segment_id
    assert session_payload["citations"]

    latest_session_response = client.get(f"/api/v1/sessions/{session_id}/analytics/enhance")
    assert latest_session_response.status_code == 200
    assert latest_session_response.json()["id"] == session_payload["id"]

    segment_enhance_response = client.post(
        f"/api/v1/segment-scores/{segment_score_id}/analytics/enhance",
        json={"allow_web_search": False, "include_memory": True},
    )
    assert segment_enhance_response.status_code == 200
    segment_payload = segment_enhance_response.json()
    assert segment_payload["status"] == "ready"
    assert segment_payload["diagnosis"]
    assert segment_payload["evidence_story"]
    assert len(segment_payload["teacher_focus"]) >= 1
    assert len(segment_payload["recommended_checks"]) >= 1
    assert segment_payload["citations"]
    assert segment_payload["memory_notes"]

    latest_segment_response = client.get(f"/api/v1/segment-scores/{segment_score_id}/analytics/enhance")
    assert latest_segment_response.status_code == 200
    assert latest_segment_response.json()["id"] == segment_payload["id"]


def test_enhanced_analysis_failure_is_persisted_without_500(client, monkeypatch):
    session_id, _ = create_session_with_segment(client, title="Failing Enhanced Session")
    upload_public_demo_minimum(client, session_id)

    analysis_response = client.post(f"/api/v1/sessions/{session_id}/analytics/run")
    assert analysis_response.status_code == 200

    class FailingProvider:
        def get_model_name(self) -> str:
            return "failing-enhanced-provider"

        def generate_session(self, context):
            raise EnhancedAnalysisGenerationError("enhanced session generation failed")

        def generate_segment(self, context):
            raise EnhancedAnalysisGenerationError("enhanced segment generation failed")

    monkeypatch.setattr(
        analytics_routes.enhanced_analysis_service,
        "get_enhanced_analysis_provider",
        lambda: FailingProvider(),
    )

    session_enhance_response = client.post(
        f"/api/v1/sessions/{session_id}/analytics/enhance",
        json={"allow_web_search": False, "include_memory": True},
    )
    assert session_enhance_response.status_code == 200
    session_payload = session_enhance_response.json()
    assert session_payload["status"] == "failed"
    assert session_payload["failure_reason"] == "enhanced session generation failed"
    assert session_payload["summary"] is None
