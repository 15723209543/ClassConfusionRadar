"""
本文件的作用是：验证课堂数据上传、困惑分析和教学建议生成的完整流程。
"""
def create_session_with_segment(client):
    session_response = client.post(
        "/api/v1/sessions",
        json={
            "title": "循环结构课堂",
            "course_type": "c_language",
            "class_date": "2026-04-11",
            "duration_minutes": 90,
            "notes": "分析流程测试",
        },
    )
    session_id = session_response.json()["id"]

    knowledge_point_response = client.post(
        f"/api/v1/sessions/{session_id}/knowledge-points",
        json={
            "name": "while 循环",
            "topic_area": "控制流",
            "display_order": 1,
        },
    )
    knowledge_point_id = knowledge_point_response.json()["id"]

    segment_response = client.post(
        f"/api/v1/sessions/{session_id}/segments",
        json={
            "title": "循环条件判断",
            "knowledge_point_id": knowledge_point_id,
            "start_minute": 10,
            "end_minute": 30,
            "display_order": 1,
        },
    )
    assert segment_response.status_code == 201
    return session_id, segment_response.json()["id"]


def test_upload_analyze_and_generate_suggestion(client):
    session_id, segment_id = create_session_with_segment(client)

    quiz_csv = (
        "student_code,student_name,question_code,score,is_correct,event_minute\n"
        "S01,张三,Q1,0,false,12\n"
        "S02,李四,Q1,0,false,15\n"
        "S03,王五,Q1,1,true,18\n"
    )
    submission_csv = (
        "student_code,student_name,task_name,language,result_status,error_type,error_message,event_minute\n"
        "S01,张三,LoopTask,c_language,compile_error,SyntaxError,missing semicolon,16\n"
        "S01,张三,LoopTask,c_language,compile_error,SyntaxError,missing semicolon,17\n"
        "S01,张三,LoopTask,c_language,compile_error,SyntaxError,missing semicolon,18\n"
        "S02,李四,LoopTask,c_language,runtime_error,InfiniteLoop,timeout,19\n"
        "S02,李四,LoopTask,c_language,runtime_error,InfiniteLoop,timeout,21\n"
        "S03,王五,LoopTask,c_language,success,,,20\n"
    )
    interaction_csv = (
        "student_code,student_name,event_type,value,event_minute\n"
        "S03,王五,raise_hand,1,14\n"
    )

    for file_kind, content in [
        ("quiz", quiz_csv),
        ("submission", submission_csv),
        ("interaction", interaction_csv),
    ]:
        response = client.post(
            f"/api/v1/sessions/{session_id}/files",
            files={"file": (f"{file_kind}.csv", content, "text/csv")},
            data={"file_kind": file_kind},
        )
        assert response.status_code == 201
        assert response.json()["parse_status"] == "success"

    analysis_response = client.post(f"/api/v1/sessions/{session_id}/analytics/run")
    assert analysis_response.status_code == 200
    assert analysis_response.json()["status"] == "completed"

    overview_response = client.get(f"/api/v1/sessions/{session_id}/analytics/overview")
    assert overview_response.status_code == 200
    overview_payload = overview_response.json()
    assert overview_payload["has_analysis"] is True
    assert overview_payload["summary"]["total_segments"] == 1
    assert "有效数据项加权归一化" in overview_payload["score_formula"]
    assert len(overview_payload["scoring_rules"]) == 4
    assert overview_payload["high_risk_segments"][0]["segment_id"] == segment_id
    assert overview_payload["high_risk_segments"][0]["primary_signal_label"] == "提交失败率"
    assert overview_payload["high_risk_segments"][0]["main_error_summary"] == "语法错误（3 次）；死循环（2 次）"
    assert "判定为高风险" in overview_payload["high_risk_segments"][0]["overall_explanation"]

    detail_response = client.get(f"/api/v1/segments/{segment_id}/analytics")
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["segment_id"] == segment_id
    assert detail_payload["score_formula"] == overview_payload["score_formula"]
    assert len(detail_payload["signal_breakdown"]) == 4
    assert detail_payload["data_coverage_percent"] == 100
    assert detail_payload["confidence_level"] == "high"
    assert {item["label"] for item in detail_payload["signal_breakdown"]} == {
        "测验错误率",
        "提交失败率",
        "重复错误密度",
        "互动沉默度",
    }
    assert detail_payload["main_error_summary"] == "语法错误（3 次）；死循环（2 次）"
    assert "判定为高风险" in detail_payload["overall_explanation"]
    assert "测验错误率" in detail_payload["overall_explanation"]
    assert "提交失败率" in detail_payload["overall_explanation"]

    segment_score_id = overview_payload["high_risk_segments"][0]["segment_score_id"]
    intervention_response = client.post(
        f"/api/v1/segment-scores/{segment_score_id}/interventions",
        json={"status": "executed", "plan_text": "已采纳建议"},
    )
    assert intervention_response.status_code == 201
    assert intervention_response.json()["status"] == "executed"

    report_response = client.get(f"/api/v1/sessions/{session_id}/analytics/report.md")
    assert report_response.status_code == 200
    assert "课堂复盘报告" in report_response.text

    suggestion_response = client.post(f"/api/v1/segment-scores/{segment_score_id}/suggestions")
    assert suggestion_response.status_code == 201
    suggestion_payload = suggestion_response.json()
    assert suggestion_payload["status"] == "ready"
    assert suggestion_payload["structured_content"]["diagnosis"]
    assert len(suggestion_payload["structured_content"]["reteach_script"]) >= 1
    assert len(suggestion_payload["structured_content"]["board_plan"]) >= 1
    assert len(suggestion_payload["structured_content"]["micro_exercises"]) >= 1
    assert suggestion_payload["structured_content"]["followup_task"]
    assert "再教学建议" in suggestion_payload["suggestion_markdown"]
    assert suggestion_payload["generation_mode"] == "offline_rule"
    assert suggestion_payload["generation_mode_label"] == "离线可解释建议"

    print_report_response = client.get(f"/api/v1/sessions/{session_id}/analytics/report.html")
    assert print_report_response.status_code == 200
    assert "打印 / 另存为 PDF" in print_report_response.text


def test_run_analysis_requires_successful_upload(client):
    session_id, _ = create_session_with_segment(client)

    response = client.post(f"/api/v1/sessions/{session_id}/analytics/run")

    assert response.status_code == 400
    assert "成功解析" in response.json()["detail"]


def test_delete_uploaded_file_resets_session_status_and_roster(client):
    session_id, _ = create_session_with_segment(client)

    quiz_response = client.post(
        f"/api/v1/sessions/{session_id}/files",
        files={
            "file": (
                "quiz.csv",
                "student_code,student_name,question_code,score,is_correct,event_minute\nS01,张三,Q1,0,false,12\n",
                "text/csv",
            )
        },
        data={"file_kind": "quiz"},
    )
    assert quiz_response.status_code == 201
    file_id = quiz_response.json()["id"]

    detail_response = client.get(f"/api/v1/sessions/{session_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["status"] == "ready"

    delete_response = client.delete(f"/api/v1/files/{file_id}")
    assert delete_response.status_code == 200

    detail_response = client.get(f"/api/v1/sessions/{session_id}")
    assert detail_response.status_code == 200
    payload = detail_response.json()
    assert payload["status"] == "draft"
    assert payload["upload_count"] == 0

    rerun_response = client.post(f"/api/v1/sessions/{session_id}/analytics/run")
    assert rerun_response.status_code == 400


def test_suggestion_generation_failure_returns_failed_status(client, monkeypatch):
    session_id, segment_id = create_session_with_segment(client)

    quiz_response = client.post(
        f"/api/v1/sessions/{session_id}/files",
        files={
            "file": (
                "quiz.csv",
                "student_code,student_name,question_code,score,is_correct,event_minute\nS01,张三,Q1,0,false,12\n",
                "text/csv",
            )
        },
        data={"file_kind": "quiz"},
    )
    assert quiz_response.status_code == 201

    analysis_response = client.post(f"/api/v1/sessions/{session_id}/analytics/run")
    assert analysis_response.status_code == 200

    detail_response = client.get(f"/api/v1/segments/{segment_id}/analytics")
    assert detail_response.status_code == 200
    segment_score_id = detail_response.json()["segment_score_id"]

    from app.ai.provider import SuggestionGenerationError
    from app.api.v1.routes import suggestions as suggestion_routes

    class FailingProvider:
        def get_model_name(self) -> str:
            return "failing-provider"

        def generate(self, context):
            raise SuggestionGenerationError("模型返回了无法解析的结构化建议，请稍后重试。")

    monkeypatch.setattr(suggestion_routes.suggestion_service, "get_suggestion_provider", lambda: FailingProvider())

    suggestion_response = client.post(f"/api/v1/segment-scores/{segment_score_id}/suggestions")
    assert suggestion_response.status_code == 201
    suggestion_payload = suggestion_response.json()
    assert suggestion_payload["status"] == "failed"
    assert suggestion_payload["structured_content"] is None
    assert suggestion_payload["failure_reason"] == "模型返回了无法解析的结构化建议，请稍后重试。"
    assert "建议生成失败" in suggestion_payload["suggestion_markdown"]
