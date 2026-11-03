"""
本文件的作用是：验证服务健康检查相关功能在典型与异常场景下的行为。
"""
def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
