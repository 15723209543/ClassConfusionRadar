"""
本文件的作用是：验证现场演示闭环相关功能在典型与异常场景下的行为。
"""
from pathlib import Path


DEMO_ZIP = Path(__file__).resolve().parents[3] / "demo_data" / "现场演示_手动输入版" / "现场演示一键导入.zip"


def test_live_demo_bundle_runs_full_flow(client):
    session = client.post(
        "/api/v1/sessions",
        json={
            "title": "现场演示：Python 条件与循环",
            "course_type": "Python 程序设计",
            "class_date": "2026-09-20",
            "duration_minutes": 90,
        },
    ).json()

    with DEMO_ZIP.open("rb") as handle:
        upload = client.post(
            f"/api/v1/sessions/{session['id']}/dataset-zip",
            files={"file": (DEMO_ZIP.name, handle.read(), "application/zip")},
        )
    assert upload.status_code == 201
    assert len(upload.json()["uploaded_files"]) == 5
    assert upload.json()["knowledge_points_created"] == 5

    build = client.post(f"/api/v1/sessions/{session['id']}/segments/auto-build", json={})
    assert build.status_code == 200
    assert build.json()["created_count"] == 5

    run = client.post(f"/api/v1/sessions/{session['id']}/analytics/run")
    assert run.status_code == 200

    overview = client.get(f"/api/v1/sessions/{session['id']}/analytics/overview").json()
    assert overview["has_analysis"] is True
    assert overview["summary"]["total_segments"] == 5
    assert overview["high_risk_segments"]
    top = overview["high_risk_segments"][0]
    assert "循环边界" in (top["knowledge_point_name"] or top["title"])
    assert top["data_coverage_percent"] == 100
