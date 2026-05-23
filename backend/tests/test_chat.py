import json


def _register_and_login(client):
    client.post("/api/auth/register", json={"username": "lin", "password": "good-password"})
    response = client.post("/api/auth/login", json={"username": "lin", "password": "good-password"})
    assert response.status_code == 200


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

    def fake_stream(messages):
        assert messages[-1]["content"] == "Hello"
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

    def fake_stream(messages):
        raise RuntimeError("provider unavailable")
        yield ""

    monkeypatch.setattr("app.api.chat.stream_llm_response", fake_stream)

    response = client.post("/api/chat/stream", json={"message": "Hello"})

    assert response.status_code == 200
    events = _events(response)
    assert events[0][0] == "meta"
    assert events[1] == ("error", {"message": "The AI provider failed. Please try again."})
