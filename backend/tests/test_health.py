def test_health_returns_ok(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_runtime_status_exposes_safe_configuration(client):
    response = client.get("/api/status")

    assert response.status_code == 200
    body = response.json()
    assert body["app_env"] == "test"
    assert body["database"] == "sqlite"
    assert body["upload_limit_bytes"] == 5 * 1024 * 1024
    assert "api_key" not in str(body).lower()
