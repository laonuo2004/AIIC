from app.core.database import SessionLocal
from app.models.entities import OpenRouterCredential


def _register_and_login(client, username="lin"):
    client.post("/api/auth/register", json={"username": username, "password": "good-password"})
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": "good-password"},
    )
    assert response.status_code == 200


def _model_payload():
    return [
        {
            "id": "qwen/qwen3.6-flash",
            "name": "Qwen 3.6 Flash",
            "input_modalities": ["text"],
            "output_modalities": ["text"],
            "context_length": 128000,
            "pricing": {"prompt": "0.0000001", "completion": "0.0000002"},
        },
        {
            "id": "openai/gpt-4o-mini",
            "name": "GPT-4o mini",
            "input_modalities": ["text", "image"],
            "output_modalities": ["text"],
            "context_length": 128000,
            "pricing": {"prompt": "0.00000015", "completion": "0.0000006"},
        },
    ]


def test_openrouter_key_is_saved_encrypted_and_only_hint_is_returned(client, monkeypatch):
    _register_and_login(client)
    monkeypatch.setattr(
        "app.api.providers.fetch_openrouter_models",
        lambda api_key: _model_payload(),
    )

    response = client.put(
        "/api/providers/openrouter/key",
        json={"api_key": "sk-or-v1-secret1234"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["configured"] is True
    assert body["key_hint"] == "1234"
    assert "sk-or-v1-secret1234" not in str(body)

    config = client.get("/api/providers/openrouter/config")
    assert config.status_code == 200
    assert config.json()["configured"] is True
    assert config.json()["key_hint"] == "1234"

    with SessionLocal() as db:
        record = db.query(OpenRouterCredential).one()
        assert "sk-or-v1-secret1234" not in record.encrypted_api_key


def test_openrouter_models_refresh_and_preferences(client, monkeypatch):
    _register_and_login(client)
    monkeypatch.setattr(
        "app.api.providers.fetch_openrouter_models",
        lambda api_key: _model_payload(),
    )
    client.put("/api/providers/openrouter/key", json={"api_key": "sk-or-v1-secret1234"})

    models = client.get("/api/providers/openrouter/models?refresh=true")
    assert models.status_code == 200
    assert {item["id"] for item in models.json()["models"]} == {
        "qwen/qwen3.6-flash",
        "openai/gpt-4o-mini",
    }

    patch = client.patch(
        "/api/providers/openrouter/models",
        json={
            "enabled_model_ids": ["qwen/qwen3.6-flash"],
            "selected_model_id": "qwen/qwen3.6-flash",
        },
    )
    assert patch.status_code == 200
    assert patch.json()["enabled_model_ids"] == ["qwen/qwen3.6-flash"]
    assert patch.json()["selected_model_id"] == "qwen/qwen3.6-flash"


def test_openrouter_models_refresh_falls_back_to_cached_models(client, monkeypatch):
    _register_and_login(client)
    monkeypatch.setattr(
        "app.api.providers.fetch_openrouter_models",
        lambda api_key: _model_payload(),
    )
    client.put("/api/providers/openrouter/key", json={"api_key": "sk-or-v1-secret1234"})

    def fail_fetch(api_key):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr("app.api.providers.fetch_openrouter_models", fail_fetch)
    response = client.get("/api/providers/openrouter/models?refresh=true")

    assert response.status_code == 200
    assert {item["id"] for item in response.json()["models"]} == {
        "qwen/qwen3.6-flash",
        "openai/gpt-4o-mini",
    }
    assert response.json()["warning"] == "Using cached models because OpenRouter refresh failed."


def test_chat_requires_key_enabled_model_and_selected_model(client, monkeypatch):
    _register_and_login(client)

    missing_key = client.post(
        "/api/chat/stream",
        json={"message": "Hello", "model_id": "qwen/qwen3.6-flash"},
    )
    assert missing_key.status_code == 400
    assert "OpenRouter API key" in missing_key.json()["detail"]

    monkeypatch.setattr(
        "app.api.providers.fetch_openrouter_models",
        lambda api_key: _model_payload(),
    )
    client.put("/api/providers/openrouter/key", json={"api_key": "sk-or-v1-secret1234"})

    no_enabled = client.post(
        "/api/chat/stream",
        json={"message": "Hello", "model_id": "qwen/qwen3.6-flash"},
    )
    assert no_enabled.status_code == 400
    assert "Enable at least one model" in no_enabled.json()["detail"]

    client.patch(
        "/api/providers/openrouter/models",
        json={
            "enabled_model_ids": ["qwen/qwen3.6-flash"],
            "selected_model_id": "qwen/qwen3.6-flash",
        },
    )

    disabled = client.post(
        "/api/chat/stream",
        json={"message": "Hello", "model_id": "openai/gpt-4o-mini"},
    )
    assert disabled.status_code == 400
    assert "not enabled" in disabled.json()["detail"]
