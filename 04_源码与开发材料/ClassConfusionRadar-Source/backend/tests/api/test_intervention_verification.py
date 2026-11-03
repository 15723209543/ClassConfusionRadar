"""
本文件的作用是：验证教学干预效果核验相关功能在典型与异常场景下的行为。
"""
def create_analyzed_quiz_session(client, *, title: str, date: str, wrong_count: int):
    session = client.post(
        "/api/v1/sessions",
        json={"title": title, "course_type": "python", "class_date": date, "duration_minutes": 60},
    ).json()
    point = client.post(
        f"/api/v1/sessions/{session['id']}/knowledge-points",
        json={"name": "while 循环", "display_order": 1},
    ).json()
    segment = client.post(
        f"/api/v1/sessions/{session['id']}/segments",
        json={
            "title": "while 循环",
            "knowledge_point_id": point["id"],
            "start_minute": 0,
            "end_minute": 20,
            "display_order": 1,
        },
    ).json()

    rows = ["student_code,question_code,score,is_correct,event_minute"]
    for index in range(5):
        wrong = index < wrong_count
        rows.append(f"S{index+1:02d},Q1,{0 if wrong else 1},{'false' if wrong else 'true'},10")
    upload = client.post(
        f"/api/v1/sessions/{session['id']}/files",
        files={"file": ("quiz.csv", "\n".join(rows) + "\n", "text/csv")},
        data={"file_kind": "quiz"},
    )
    assert upload.status_code == 201
    assert client.post(f"/api/v1/sessions/{session['id']}/analytics/run").status_code == 200
    detail = client.get(f"/api/v1/segments/{segment['id']}/analytics").json()
    return detail


def test_intervention_can_be_verified_against_later_session(client):
    before = create_analyzed_quiz_session(client, title="第一次课", date="2026-09-01", wrong_count=4)
    intervention = client.post(
        f"/api/v1/segment-scores/{before['segment_score_id']}/interventions",
        json={"status": "executed", "plan_text": "补讲循环终止条件"},
    ).json()

    after = create_analyzed_quiz_session(client, title="第二次课", date="2026-09-08", wrong_count=1)
    assert before["confusion_score"] == 80
    assert after["confusion_score"] == 20

    response = client.post(f"/api/v1/interventions/{intervention['id']}/verify")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "verified"
    assert payload["followup_score_before"] == 80
    assert payload["followup_score_after"] == 20
    assert "下降 60" in payload["outcome_summary"]
