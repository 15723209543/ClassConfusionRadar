"""
本文件的作用是：验证课堂场次相关功能在典型与异常场景下的行为。
"""
def test_create_session_and_get_detail(client):
    create_response = client.post(
        "/api/v1/sessions",
        json={
            "title": "Python 条件语句课",
            "course_type": "python",
            "class_date": "2026-04-11",
            "duration_minutes": 90,
            "notes": "用于测试的课堂样例",
        },
    )

    assert create_response.status_code == 201
    session_id = create_response.json()["id"]

    detail_response = client.get(f"/api/v1/sessions/{session_id}")
    assert detail_response.status_code == 200
    payload = detail_response.json()
    assert payload["title"] == "Python 条件语句课"
    assert payload["upload_count"] == 0
    assert payload["segment_count"] == 0



def test_upload_auto_detects_file_kind_when_selector_is_wrong(client):
    session = client.post(
        "/api/v1/sessions",
        json={
            "title": "上传类型自动识别",
            "course_type": "python",
            "class_date": "2026-09-03",
            "duration_minutes": 90,
        },
    ).json()

    submission_csv = (
        "student_code,task_name,language,result_status,error_type,error_message,event_minute\n"
        "S01,T1,python,success,,,8\n"
        "S02,T1,python,wrong_answer,OffByOne,boundary,9\n"
    ).encode("utf-8")

    response = client.post(
        f"/api/v1/sessions/{session['id']}/files",
        data={"file_kind": "quiz"},
        files={"file": ("submission.csv", submission_csv, "text/csv")},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["file_kind"] == "submission"
    assert payload["row_count"] == 2
    assert payload["parse_status"] == "success"
