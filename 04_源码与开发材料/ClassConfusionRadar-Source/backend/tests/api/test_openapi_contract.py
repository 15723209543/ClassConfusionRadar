"""
本文件的作用是：验证接口契约相关功能在典型与异常场景下的行为。
"""
def test_openapi_contract_contains_competition_demo_routes(client):
    response = client.get("/openapi.json")
    assert response.status_code == 200
    payload = response.json()
    paths = payload["paths"]

    expected_paths = {
        "/api/v1/sessions/{session_id}/files",
        "/api/v1/sessions/{session_id}/dataset-zip",
        "/api/v1/sessions/{session_id}/segments/auto-build",
        "/api/v1/sessions/{session_id}/analytics/run",
        "/api/v1/sessions/{session_id}/analytics/overview",
        "/api/v1/sessions/{session_id}/analytics/report.html",
        "/api/v1/interventions/{intervention_id}/verify",
    }
    assert expected_paths.issubset(paths.keys())
