from pathlib import Path
from urllib.parse import urlparse

from fastapi.testclient import TestClient

PNG_1X1 = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _register_and_login(client: TestClient, username: str = "face") -> None:
    client.post("/api/auth/register", json={"username": username, "password": "good-password"})
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": "good-password"},
    )
    assert response.status_code == 200


def _upload_asset(client: TestClient) -> dict:
    response = client.post(
        "/api/face/assets",
        files={
            "image": ("interviewer.png", PNG_1X1, "image/png"),
            "audio": ("voice.wav", b"RIFF....WAVEfmt " + b"\x00" * 32, "audio/wav"),
        },
    )
    assert response.status_code == 201
    return response.json()


def test_face_asset_requires_auth_and_validates_uploads(client):
    unauthenticated = client.post(
        "/api/face/assets",
        files={
            "image": ("interviewer.png", PNG_1X1, "image/png"),
            "audio": ("voice.wav", b"voice", "audio/wav"),
        },
    )
    assert unauthenticated.status_code == 401

    _register_and_login(client)
    invalid = client.post(
        "/api/face/assets",
        files={
            "image": ("notes.txt", b"not image", "text/plain"),
            "audio": ("voice.wav", b"voice", "audio/wav"),
        },
    )
    assert invalid.status_code == 400
    assert "image" in invalid.json()["detail"].lower()

    too_large_audio = client.post(
        "/api/face/assets",
        files={
            "image": ("interviewer.png", PNG_1X1, "image/png"),
            "audio": ("voice.wav", b"x" * (10 * 1024 * 1024 + 1), "audio/wav"),
        },
    )
    assert too_large_audio.status_code == 400
    assert "10MB" in too_large_audio.json()["detail"]


def test_face_asset_public_media_token_serves_only_asset_files(client):
    _register_and_login(client)
    asset = _upload_asset(client)

    assert asset["status"] == "uploaded"
    assert asset["image_url"].startswith("http://")
    assert asset["audio_url"].startswith("http://")
    assert "/api/face/media/" in asset["image_url"]
    assert "/api/attachments/" not in asset["image_url"]

    image_path = urlparse(asset["image_url"]).path
    media = client.get(image_path)
    assert media.status_code == 200
    assert media.content == PNG_1X1

    missing = client.get("/api/face/media/not-a-real-token")
    assert missing.status_code == 404


def test_voice_clone_is_mockable_and_stores_speaker_id(client, monkeypatch):
    _register_and_login(client)
    asset = _upload_asset(client)
    captured = {}

    def fake_clone(asset_record, audio_url):
        captured["filename"] = Path(asset_record.audio_path).name
        captured["audio_url"] = audio_url
        return {"speaker_id": "demo-speaker-001", "provider_status": "ready"}

    monkeypatch.setattr("app.api.face.clone_voice_from_asset", fake_clone)

    response = client.post(f"/api/face/assets/{asset['id']}/voice-clone")

    assert response.status_code == 200
    body = response.json()
    assert body["speaker_id"] == "demo-speaker-001"
    assert body["status"] == "voice_ready"
    assert captured["audio_url"] == asset["audio_url"]
    assert captured["filename"].endswith(".wav")


def test_video_generation_surfaces_missing_omnihuman_access_key(client, monkeypatch):
    _register_and_login(client)
    asset = _upload_asset(client)

    def missing_access_key(asset_record, image_url):
        raise RuntimeError("VOLCENGINE_OMNIHUMAN_ACCESS_KEY_ID is required for video generation.")

    monkeypatch.setattr("app.api.face.generate_face_videos", missing_access_key)

    response = client.post(f"/api/face/assets/{asset['id']}/videos")

    assert response.status_code == 400
    assert "VOLCENGINE_OMNIHUMAN_ACCESS_KEY_ID" in response.json()["detail"]
    follow_up = client.get(f"/api/face/assets/{asset['id']}")
    assert follow_up.json()["status"] == "video_error"
    assert "VOLCENGINE_OMNIHUMAN_ACCESS_KEY_ID" in follow_up.json()["error_message"]


def test_realtime_session_websocket_uses_fake_provider_events(client, monkeypatch):
    _register_and_login(client)
    asset = _upload_asset(client)
    voice = {"speaker_id": "demo-speaker-001", "provider_status": "ready"}
    monkeypatch.setattr(
        "app.api.face.clone_voice_from_asset",
        lambda asset_record, audio_url: voice,
    )
    client.post(f"/api/face/assets/{asset['id']}/voice-clone")

    class FakeRealtimeBridge:
        def __init__(self, speaker_id: str):
            self.speaker_id = speaker_id

        async def start(self):
            return {"event": "session_started", "speaker_id": self.speaker_id}

        async def receive_client_event(self, event):
            if event["event"] == "audio_chunk":
                return [
                    {"event": "asr_partial", "text": "我负责模型部分"},
                    {"event": "assistant_text", "text": "你具体实现了哪些模块？"},
                    {
                        "event": "assistant_audio",
                        "audio": "UklGRg==",
                        "mime": "audio/wav",
                    },
                ]
            return []

    monkeypatch.setattr(
        "app.api.face.create_realtime_bridge",
        lambda speaker_id: FakeRealtimeBridge(speaker_id),
    )

    session = client.post("/api/face/session", json={"asset_id": asset["id"]})
    assert session.status_code == 201

    with client.websocket_connect(f"/api/face/session/{session.json()['id']}/stream") as websocket:
        websocket.send_json({"event": "start_session"})
        assert websocket.receive_json()["event"] == "session_started"
        websocket.send_json({"event": "audio_chunk", "audio": "AAAA"})
        assert websocket.receive_json()["event"] == "asr_partial"
        assert websocket.receive_json()["event"] == "assistant_text"
        assert websocket.receive_json()["event"] == "assistant_audio"
        websocket.send_json({"event": "finish_session"})
        assert websocket.receive_json()["event"] == "session_finished"
