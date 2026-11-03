"""
本文件的作用是：验证隐私数据清理相关功能在典型与异常场景下的行为。
"""
from pathlib import Path

from sqlalchemy import func, select

from app.core.config import get_settings
from app.models.records import Student


def test_delete_session_removes_source_files_and_orphan_student(client, db_session):
    session = client.post(
        "/api/v1/sessions",
        json={"title": "隐私清理测试", "course_type": "python", "class_date": "2026-09-10", "duration_minutes": 45},
    ).json()
    session_id = session["id"]

    upload = client.post(
        f"/api/v1/sessions/{session_id}/files",
        files={
            "file": (
                "quiz.csv",
                "student_code,question_code,score,is_correct,event_minute\nREAL001,Q1,0,false,5\n",
                "text/csv",
            )
        },
        data={"file_kind": "quiz"},
    )
    assert upload.status_code == 201

    student = db_session.scalar(select(Student))
    assert student is not None
    assert student.student_code != "REAL001"

    session_dir = Path(get_settings().storage_dir) / f"session_{session_id}"
    assert session_dir.exists()

    response = client.delete(f"/api/v1/sessions/{session_id}")
    assert response.status_code == 200
    assert not session_dir.exists()
    assert (db_session.scalar(select(func.count(Student.id))) or 0) == 0
