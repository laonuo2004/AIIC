import json


def _register_and_login(client):
    client.post("/api/auth/register", json={"username": "lin", "password": "good-password"})
    response = client.post("/api/auth/login", json={"username": "lin", "password": "good-password"})
    assert response.status_code == 200


def _configure_model(client, monkeypatch):
    monkeypatch.setattr(
        "app.api.providers.fetch_openrouter_models",
        lambda api_key: [
            {
                "id": "qwen/qwen3.6-flash",
                "name": "Qwen 3.6 Flash",
                "input_modalities": ["text"],
                "output_modalities": ["text"],
                "context_length": 128000,
                "pricing": {"prompt": "0.0000001", "completion": "0.0000002"},
            }
        ],
    )
    client.put("/api/providers/openrouter/key", json={"api_key": "sk-or-v1-secret1234"})
    client.patch(
        "/api/providers/openrouter/models",
        json={
            "enabled_model_ids": ["qwen/qwen3.6-flash"],
            "selected_model_id": "qwen/qwen3.6-flash",
        },
    )


def _events(response):
    events = []
    for block in response.text.strip().split("\n\n"):
        lines = block.splitlines()
        event = next(line.removeprefix("event: ") for line in lines if line.startswith("event: "))
        data = next(line.removeprefix("data: ") for line in lines if line.startswith("data: "))
        events.append((event, json.loads(data)))
    return events


def test_stream_chat_persists_conversation_and_messages(client, monkeypatch):
    _register_and_login(client)
    _configure_model(client, monkeypatch)

    def fake_stream(messages, *, model, api_key):
        assert messages[-1]["content"] == "Hello"
        assert model == "openrouter/qwen/qwen3.6-flash"
        assert api_key == "sk-or-v1-secret1234"
        yield "Hi"
        yield " there"

    monkeypatch.setattr("app.api.chat.stream_llm_response", fake_stream)

    response = client.post("/api/chat/stream", json={"message": "Hello"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    events = _events(response)
    assert events[0][0] == "meta"
    assert events[1:] == [
        ("delta", {"text": "Hi"}),
        ("delta", {"text": " there"}),
        ("done", {"conversation_id": events[0][1]["conversation_id"]}),
    ]

    conversations = client.get("/api/conversations")
    assert conversations.status_code == 200
    assert len(conversations.json()["conversations"]) == 1
    conversation_id = conversations.json()["conversations"][0]["id"]

    detail = client.get(f"/api/conversations/{conversation_id}")
    assert detail.status_code == 200
    assert [message["role"] for message in detail.json()["messages"]] == ["user", "assistant"]
    assert detail.json()["messages"][1]["content"] == "Hi there"


def test_stream_chat_requires_auth(client):
    response = client.post("/api/chat/stream", json={"message": "Hello"})

    assert response.status_code == 401


def test_stream_chat_returns_sse_error_when_llm_fails(client, monkeypatch):
    _register_and_login(client)
    _configure_model(client, monkeypatch)

    def fake_stream(messages, *, model, api_key):
        raise RuntimeError("provider unavailable")
        yield ""

    monkeypatch.setattr("app.api.chat.stream_llm_response", fake_stream)

    response = client.post("/api/chat/stream", json={"message": "Hello"})

    assert response.status_code == 200
    events = _events(response)
    assert events[0][0] == "meta"
    assert events[1] == ("error", {"message": "The AI provider failed. Please try again."})
