"""
本文件的作用是：验证课堂数据 ZIP 的识别、校验、导入与异常回滚行为。
"""
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

from sqlalchemy import select

from app.models.records import Student


def build_dataset_zip() -> bytes:
    files = {
        "quiz.csv": "student_code,question_code,score,is_correct,event_minute\nS01,Q1,0,false,5\nS02,Q1,1,true,5\n",
        "submission.csv": "student_code,task_name,language,result_status,error_type,error_message,event_minute\nS01,T1,python,wrong_answer,OffByOne,boundary,8\nS02,T1,python,success,,,8\n",
        "interaction.csv": "student_code,event_type,value,event_minute\nS02,poll,1,6\n",
        "transcript.csv": "start_minute,end_minute,text\n0,10,讲条件判断和循环边界。\n",
        "ppt_timeline.csv": "slide_index,start_minute,end_minute,slide_title\n1,0,10,循环边界\n",
        "manifest.json": '{"knowledge_points":[{"name":"循环边界"},{"name":"条件判断"}]}',
        "notes.txt": "这个文件会被忽略",
    }
    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content.encode("utf-8"))
    return buffer.getvalue()


def test_dataset_zip_imports_five_kinds_and_manifest(client, db_session):
    session = client.post(
        "/api/v1/sessions",
        json={"title": "ZIP 导入", "course_type": "python", "class_date": "2026-09-01", "duration_minutes": 90},
    ).json()

    response = client.post(
        f"/api/v1/sessions/{session['id']}/dataset-zip",
        files={"file": ("classroom.zip", build_dataset_zip(), "application/zip")},
    )
    assert response.status_code == 201
    payload = response.json()
    assert len(payload["uploaded_files"]) == 5
    assert payload["knowledge_points_created"] == 2
    assert payload["manifest_found"] is True
    assert payload["skipped_files"] == ["notes.txt"]

    detail = client.get(f"/api/v1/sessions/{session['id']}").json()
    assert detail["upload_count"] == 5
    assert detail["knowledge_point_count"] == 2

    students = db_session.scalars(select(Student)).all()
    assert students
    assert all(student.student_code.startswith("anon_") for student in students)
    assert all(student.display_name.startswith("学生-") for student in students)


def test_dataset_zip_rejects_duplicate_kind(client):
    session = client.post(
        "/api/v1/sessions",
        json={"title": "重复文件", "course_type": "python", "class_date": "2026-09-02", "duration_minutes": 90},
    ).json()
    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        archive.writestr("quiz.csv", "student_code,question_code,score,is_correct,event_minute\nS01,Q1,1,true,2\n")
        archive.writestr("quiz_copy.csv", "student_code,question_code,score,is_correct,event_minute\nS02,Q1,1,true,2\n")

    response = client.post(
        f"/api/v1/sessions/{session['id']}/dataset-zip",
        files={"file": ("bad.zip", buffer.getvalue(), "application/zip")},
    )
    assert response.status_code == 400
    assert "多份 quiz" in response.json()["detail"]
