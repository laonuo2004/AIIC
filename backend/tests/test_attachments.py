import json

PNG_1X1 = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _register_and_login(client, username="lin"):
    client.post("/api/auth/register", json={"username": username, "password": "good-password"})
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": "good-password"},
    )
    assert response.status_code == 200


def _events(response):
    events = []
    for block in response.text.strip().split("\n\n"):
        lines = block.splitlines()
        event = next(line.removeprefix("event: ") for line in lines if line.startswith("event: "))
        data = next(line.removeprefix("data: ") for line in lines if line.startswith("data: "))
        events.append((event, json.loads(data)))
    return events


def _configure_model(client, monkeypatch):
    monkeypatch.setattr(
        "app.api.providers.fetch_openrouter_models",
        lambda api_key: [
            {
                "id": "openai/gpt-4o-mini",
                "name": "GPT-4o mini",
                "input_modalities": ["text", "image"],
                "output_modalities": ["text"],
                "context_length": 128000,
                "pricing": {"prompt": "0.00000015", "completion": "0.0000006"},
            }
        ],
    )
    client.put("/api/providers/openrouter/key", json={"api_key": "sk-or-v1-secret1234"})
    client.patch(
        "/api/providers/openrouter/models",
        json={
            "enabled_model_ids": ["openai/gpt-4o-mini"],
            "selected_model_id": "openai/gpt-4o-mini",
        },
    )


def test_text_and_image_attachment_upload_download_and_auth(client):
    _register_and_login(client)

    upload = client.post(
        "/api/attachments",
        files=[
            ("files", ("notes.md", b"# Notes\nUse this context.", "text/markdown")),
            ("files", ("pixel.png", PNG_1X1, "image/png")),
        ],
    )

    assert upload.status_code == 201
    attachments = upload.json()["attachments"]
    assert [item["kind"] for item in attachments] == ["text", "image"]
    assert attachments[0]["name"] == "notes.md"

    download = client.get(f"/api/attachments/{attachments[0]['id']}")
    assert download.status_code == 200
    assert download.text == "# Notes\nUse this context."

    client.post("/api/auth/logout")
    _register_and_login(client, username="ada")
    forbidden = client.get(f"/api/attachments/{attachments[0]['id']}")
    assert forbidden.status_code == 404


def test_attachment_upload_rejects_unsupported_size_and_count(client):
    _register_and_login(client)

    unsupported = client.post(
        "/api/attachments",
        files=[("files", ("program.exe", b"nope", "application/octet-stream"))],
    )
    assert unsupported.status_code == 400
    assert "Unsupported attachment type" in unsupported.json()["detail"]

    too_large = client.post(
        "/api/attachments",
        files=[("files", ("large.txt", b"x" * (5 * 1024 * 1024 + 1), "text/plain"))],
    )
    assert too_large.status_code == 400
    assert "5MB" in too_large.json()["detail"]

    too_many = client.post(
        "/api/attachments",
        files=[
            ("files", (f"notes-{index}.txt", b"ok", "text/plain"))
            for index in range(5)
        ],
    )
    assert too_many.status_code == 400
    assert "up to 4" in too_many.json()["detail"]


def test_chat_injects_text_and_image_attachments_into_llm_messages(client, monkeypatch):
    _register_and_login(client)
    _configure_model(client, monkeypatch)
    upload = client.post(
        "/api/attachments",
        files=[
            ("files", ("notes.txt", b"Important context", "text/plain")),
            ("files", ("pixel.png", PNG_1X1, "image/png")),
        ],
    )
    attachment_ids = [item["id"] for item in upload.json()["attachments"]]

    captured = {}

    def fake_stream(messages, *, model, api_key):
        captured["messages"] = messages
        captured["model"] = model
        captured["api_key"] = api_key
        yield "Done"

    monkeypatch.setattr("app.api.chat.stream_llm_response", fake_stream)

    response = client.post(
        "/api/chat/stream",
        json={
            "message": "Summarize this.",
            "model_id": "openai/gpt-4o-mini",
            "attachment_ids": attachment_ids,
        },
    )

    assert response.status_code == 200
    assert _events(response)[0] == (
        "meta",
        {"conversation_id": 1, "model_id": "openrouter/openai/gpt-4o-mini"},
    )
    assert captured["model"] == "openrouter/openai/gpt-4o-mini"
    assert captured["api_key"] == "sk-or-v1-secret1234"
    user_content = captured["messages"][-1]["content"]
    assert user_content[0]["type"] == "text"
    assert "Important context" in user_content[0]["text"]
    assert user_content[1]["type"] == "image_url"
    assert user_content[1]["image_url"]["url"].startswith("data:image/png;base64,")
