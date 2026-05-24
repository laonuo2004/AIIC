from pathlib import Path
from urllib.parse import urlparse

import httpx
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.models.entities import FaceAsset, FaceVideoJob
from app.services.volcengine_face import clone_voice_from_asset, generate_face_videos

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


def test_voice_clone_requires_configured_volcengine_speaker_id(client, monkeypatch):
    _register_and_login(client)
    asset = _upload_asset(client)
    monkeypatch.setenv("VOLCENGINE_SPEECH_API_KEY", "test-speech-key")
    monkeypatch.setenv("VOLCENGINE_SPEECH_APP_ID", "test-app-id")
    monkeypatch.setenv("VOLCENGINE_VOICE_CLONE_SPEAKER_ID", "")
    get_settings.cache_clear()

    try:
        response = client.post(f"/api/face/assets/{asset['id']}/voice-clone")
    finally:
        get_settings.cache_clear()

    assert response.status_code == 400
    assert "VOLCENGINE_VOICE_CLONE_SPEAKER_ID" in response.json()["detail"]


def test_voice_clone_requires_configured_volcengine_app_id(client, monkeypatch):
    _register_and_login(client)
    asset = _upload_asset(client)
    monkeypatch.setenv("VOLCENGINE_SPEECH_API_KEY", "test-speech-key")
    monkeypatch.setenv("VOLCENGINE_VOICE_CLONE_SPEAKER_ID", "S_demo")
    monkeypatch.setenv("VOLCENGINE_SPEECH_APP_ID", "")
    get_settings.cache_clear()

    try:
        response = client.post(f"/api/face/assets/{asset['id']}/voice-clone")
    finally:
        get_settings.cache_clear()

    assert response.status_code == 400
    assert "VOLCENGINE_SPEECH_APP_ID" in response.json()["detail"]


def test_voice_clone_uses_access_token_when_configured(tmp_path, monkeypatch):
    audio_path = tmp_path / "voice.wav"
    audio_path.write_bytes(b"RIFF....WAVEfmt " + b"\x00" * 32)
    asset = FaceAsset(
        id=7,
        user_id=1,
        image_path=str(tmp_path / "face.png"),
        image_mime_type="image/png",
        image_size_bytes=1,
        image_media_token="image-token",
        audio_path=str(audio_path),
        audio_mime_type="audio/wav",
        audio_size_bytes=audio_path.stat().st_size,
        audio_media_token="audio-token",
    )
    captured = {}

    def fake_post(url, json, headers, timeout):
        captured["headers"] = headers
        return httpx.Response(200, json={"BaseResp": {"StatusCode": 0}, "speaker_id": "S_demo"})

    monkeypatch.setenv("VOLCENGINE_SPEECH_API_KEY", "test-api-key")
    monkeypatch.setenv("VOLCENGINE_SPEECH_ACCESS_TOKEN", "test-access-token")
    monkeypatch.setenv("VOLCENGINE_SPEECH_APP_ID", "test-app-id")
    monkeypatch.setenv("VOLCENGINE_VOICE_CLONE_SPEAKER_ID", "S_demo")
    get_settings.cache_clear()
    monkeypatch.setattr("app.services.volcengine_face.httpx.post", fake_post)

    try:
        clone_voice_from_asset(asset, "http://example.invalid/audio.wav")
    finally:
        get_settings.cache_clear()

    assert captured["headers"]["Authorization"] == "Bearer; test-access-token"


def test_voice_clone_uses_upload_training_request(tmp_path, monkeypatch):
    audio_path = tmp_path / "voice.wav"
    audio_path.write_bytes(b"RIFF....WAVEfmt " + b"\x00" * 32)
    asset = FaceAsset(
        id=7,
        user_id=1,
        image_path=str(tmp_path / "face.png"),
        image_mime_type="image/png",
        image_size_bytes=1,
        image_media_token="image-token",
        audio_path=str(audio_path),
        audio_mime_type="audio/wav",
        audio_size_bytes=audio_path.stat().st_size,
        audio_media_token="audio-token",
    )
    captured = {}

    def fake_post(url, json, headers, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        captured["timeout"] = timeout
        return httpx.Response(200, json={"BaseResp": {"StatusCode": 0}, "speaker_id": "S_demo"})

    monkeypatch.setenv("VOLCENGINE_SPEECH_API_KEY", "test-speech-key")
    monkeypatch.setenv("VOLCENGINE_SPEECH_ACCESS_TOKEN", "")
    monkeypatch.setenv("VOLCENGINE_SPEECH_APP_ID", "test-app-id")
    monkeypatch.setenv("VOLCENGINE_VOICE_CLONE_SPEAKER_ID", "S_demo")
    get_settings.cache_clear()
    monkeypatch.setattr("app.services.volcengine_face.httpx.post", fake_post)

    try:
        result = clone_voice_from_asset(asset, "http://example.invalid/audio.wav")
    finally:
        get_settings.cache_clear()

    assert result["speaker_id"] == "S_demo"
    assert captured["url"] == "https://openspeech.bytedance.com/api/v1/mega_tts/audio/upload"
    assert captured["headers"]["Authorization"] == "Bearer; test-speech-key"
    assert captured["headers"]["Resource-Id"] == "seed-icl-2.0"
    assert captured["json"]["speaker_id"] == "S_demo"
    assert captured["json"]["appid"] == "test-app-id"
    assert captured["json"]["audios"][0]["audio_format"] == "wav"
    assert captured["json"]["audios"][0]["audio_bytes"]
    assert "audio_url" not in captured["json"]


def test_video_generation_surfaces_missing_omnihuman_access_key(client, monkeypatch):
    _register_and_login(client)
    asset = _upload_asset(client)

    def missing_access_key(asset_record, image_url, media_url_for_token):
        raise RuntimeError("VOLCENGINE_OMNIHUMAN_ACCESS_KEY_ID is required for video generation.")

    monkeypatch.setattr("app.api.face.generate_face_videos", missing_access_key)

    response = client.post(f"/api/face/assets/{asset['id']}/videos")

    assert response.status_code == 400
    assert "VOLCENGINE_OMNIHUMAN_ACCESS_KEY_ID" in response.json()["detail"]
    follow_up = client.get(f"/api/face/assets/{asset['id']}")
    assert follow_up.json()["status"] == "video_error"
    assert "VOLCENGINE_OMNIHUMAN_ACCESS_KEY_ID" in follow_up.json()["error_message"]


def test_video_generation_submits_ready_and_listening_omnihuman_jobs(
    tmp_path,
    monkeypatch,
):
    image_path = tmp_path / "face.png"
    audio_path = tmp_path / "voice.wav"
    image_path.write_bytes(PNG_1X1)
    audio_path.write_bytes(b"RIFF....WAVEfmt " + b"\x00" * 32)
    asset = FaceAsset(
        id=7,
        user_id=1,
        image_path=str(image_path),
        image_mime_type="image/png",
        image_size_bytes=image_path.stat().st_size,
        image_media_token="image-token",
        audio_path=str(audio_path),
        audio_mime_type="audio/wav",
        audio_size_bytes=audio_path.stat().st_size,
        audio_media_token="audio-token",
    )
    captured: list[dict] = []

    def fake_visual_request(action, payload):
        captured.append({"action": action, "payload": payload})
        return {
            "code": 10000,
            "data": {"task_id": f"task-{len(captured)}"},
            "request_id": f"request-{len(captured)}",
            "message": "Success",
        }

    monkeypatch.setenv("VOLCENGINE_OMNIHUMAN_ACCESS_KEY_ID", "ak")
    monkeypatch.setenv("VOLCENGINE_OMNIHUMAN_SECRET_ACCESS_KEY", "sk")
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    get_settings.cache_clear()
    monkeypatch.setattr("app.services.volcengine_face._visual_api_request", fake_visual_request)

    try:
        result = generate_face_videos(
            asset,
            "http://public.example/api/face/media/image-token",
            lambda token: f"http://public.example/api/face/media/{token}",
        )
    finally:
        get_settings.cache_clear()

    assert [call["action"] for call in captured] == ["CVSubmitTask"]
    assert result["provider_status"] == "video_pending"
    assert [job["kind"] for job in result["jobs"]] == ["ready", "listening"]
    assert result["jobs"][0]["provider_request_id"] == "request-1"
    assert result["jobs"][0]["provider_task_id"] == "task-1"
    assert result["jobs"][1]["status"] == "queued"
    assert result["jobs"][1]["provider_request_id"] is None
    assert result["jobs"][1]["provider_task_id"] is None
    assert all(job["audio_media_token"] for job in result["jobs"])
    assert all(Path(job["audio_path"]).exists() for job in result["jobs"])

    ready_payload = captured[0]["payload"]
    assert ready_payload["req_key"] == "jimeng_realman_avatar_picture_omni_v15"
    assert ready_payload["image_url"] == "http://public.example/api/face/media/image-token"
    assert "/api/face/media/" in ready_payload["audio_url"]
    assert ready_payload["output_resolution"] == 720
    assert ready_payload["pe_fast_mode"] is True
    assert "平静呼吸" in ready_payload["prompt"]


def test_video_poll_updates_ready_and_listening_urls(client, monkeypatch):
    _register_and_login(client)
    asset = _upload_asset(client)

    def fake_generate(asset_record, image_url, media_url_for_token):
        return {
            "provider_status": "video_pending",
            "jobs": [
                {
                    "kind": "ready",
                    "status": "pending",
                    "provider_task_id": "ready-task",
                    "provider_request_id": "ready-request",
                    "audio_path": "data/test-uploads/generated/ready.wav",
                    "audio_media_token": "ready-audio-token",
                },
                {
                    "kind": "listening",
                    "status": "pending",
                    "provider_task_id": "listening-task",
                    "provider_request_id": "listening-request",
                    "audio_path": "data/test-uploads/generated/listening.wav",
                    "audio_media_token": "listening-audio-token",
                },
            ],
        }

    def fake_poll(job):
        return {
            "status": "done",
            "video_url": f"https://cdn.example/{job.kind}.mp4",
            "provider_request_id": f"{job.kind}-poll-request",
        }

    monkeypatch.setattr("app.api.face.generate_face_videos", fake_generate)
    monkeypatch.setattr("app.api.face.poll_face_video_job", fake_poll)
    submitted = client.post(f"/api/face/assets/{asset['id']}/videos")
    assert submitted.status_code == 200

    response = client.post(f"/api/face/assets/{asset['id']}/videos/poll")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "video_ready"
    assert body["ready_video_url"] == "https://cdn.example/ready.mp4"
    assert body["listening_video_url"] == "https://cdn.example/listening.mp4"
    assert body["error_message"] is None


def test_video_poll_submits_listening_after_ready_finishes(client, monkeypatch):
    _register_and_login(client)
    asset = _upload_asset(client)

    def fake_generate(asset_record, image_url, media_url_for_token):
        return {
            "provider_status": "video_pending",
            "jobs": [
                {
                    "kind": "ready",
                    "status": "pending",
                    "provider_task_id": "ready-task",
                    "provider_request_id": "ready-request",
                    "audio_path": "data/test-uploads/generated/ready.wav",
                    "audio_media_token": "ready-audio-token",
                },
                {
                    "kind": "listening",
                    "status": "queued",
                    "provider_task_id": None,
                    "provider_request_id": None,
                    "audio_path": "data/test-uploads/generated/listening.wav",
                    "audio_media_token": "listening-audio-token",
                },
            ],
        }

    def fake_poll(job):
        assert job.kind == "ready"
        return {
            "status": "done",
            "video_url": "https://cdn.example/ready.mp4",
            "provider_request_id": "ready-poll-request",
        }

    submitted: list[dict] = []

    def fake_submit(job, image_url, audio_url):
        submitted.append({"kind": job.kind, "image_url": image_url, "audio_url": audio_url})
        return {
            "status": "pending",
            "provider_task_id": "listening-task",
            "provider_request_id": "listening-submit-request",
        }

    monkeypatch.setattr("app.api.face.generate_face_videos", fake_generate)
    monkeypatch.setattr("app.api.face.poll_face_video_job", fake_poll)
    monkeypatch.setattr("app.api.face.submit_prepared_face_video_job", fake_submit)
    submitted_response = client.post(f"/api/face/assets/{asset['id']}/videos")
    assert submitted_response.status_code == 200

    response = client.post(f"/api/face/assets/{asset['id']}/videos/poll")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "video_pending"
    assert body["ready_video_url"] == "https://cdn.example/ready.mp4"
    assert body["listening_video_url"] is None
    media_base_url = submitted_response.json()["image_url"].rsplit("/", 1)[0]
    assert submitted == [
        {
            "kind": "listening",
            "image_url": submitted_response.json()["image_url"],
            "audio_url": f"{media_base_url}/listening-audio-token",
        }
    ]


def test_generated_media_token_serves_only_generated_face_audio(client, tmp_path):
    _register_and_login(client)
    asset = _upload_asset(client)
    generated_dir = Path(get_settings().upload_dir) / "face-generated"
    generated_dir.mkdir(parents=True, exist_ok=True)
    generated_audio = generated_dir / "ready.wav"
    generated_audio.write_bytes(b"RIFFgenerated")

    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        db.add(
            FaceVideoJob(
                asset_id=asset["id"],
                kind="ready",
                status="pending",
                audio_path=str(generated_audio),
                audio_media_token="generated-token",
            )
        )
        db.commit()
    finally:
        db.close()

    response = client.get("/api/face/media/generated-token")

    assert response.status_code == 200
    assert response.content == b"RIFFgenerated"
    missing = client.get("/api/face/media/../../etc/passwd")
    assert missing.status_code == 404


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
    monkeypatch.setattr(
        "app.api.face.submit_speaking_face_video",
        lambda asset_record, image_url, audio_url: (_ for _ in ()).throw(
            RuntimeError("OmniHuman unavailable")
        ),
    )

    session = client.post("/api/face/session", json={"asset_id": asset["id"]})
    assert session.status_code == 201

    with client.websocket_connect(f"/api/face/session/{session.json()['id']}/stream") as websocket:
        websocket.send_json({"event": "start_session"})
        assert websocket.receive_json()["event"] == "session_started"
        websocket.send_json({"event": "audio_chunk", "audio": "AAAA"})
        assert websocket.receive_json()["event"] == "asr_partial"
        assert websocket.receive_json()["event"] == "assistant_text"
        assert websocket.receive_json()["event"] == "error"
        assert websocket.receive_json()["event"] == "assistant_audio"
        websocket.send_json({"event": "finish_session"})
        assert websocket.receive_json()["event"] == "session_finished"


def test_realtime_session_waits_for_speaking_omnihuman_video(client, monkeypatch):
    _register_and_login(client)
    asset = _upload_asset(client)
    voice = {"speaker_id": "demo-speaker-001", "provider_status": "ready"}
    monkeypatch.setattr(
        "app.api.face.clone_voice_from_asset",
        lambda asset_record, audio_url: voice,
    )
    client.post(f"/api/face/assets/{asset['id']}/voice-clone")
    captured = {}

    class FakeRealtimeBridge:
        def __init__(self, speaker_id: str):
            self.speaker_id = speaker_id

        async def start(self):
            return {"event": "session_started", "speaker_id": self.speaker_id}

        async def receive_client_event(self, event):
            if event["event"] == "audio_chunk":
                return [
                    {"event": "assistant_text", "text": "请说明你的个人贡献。"},
                    {
                        "event": "assistant_audio",
                        "audio": "UklGRg==",
                        "mime": "audio/wav",
                    },
                ]
            return []

    def fake_submit(asset_record, image_url, audio_url):
        captured["image_url"] = image_url
        captured["audio_url"] = audio_url
        return {
            "status": "pending",
            "provider_task_id": "speaking-task",
            "provider_request_id": "speaking-request",
        }

    def fake_wait(job):
        captured["job_kind"] = job.kind
        return {
            "status": "done",
            "video_url": "https://cdn.example/speaking.mp4",
            "provider_request_id": "speaking-done-request",
        }

    monkeypatch.setattr(
        "app.api.face.create_realtime_bridge",
        lambda speaker_id: FakeRealtimeBridge(speaker_id),
    )
    monkeypatch.setattr("app.api.face.submit_speaking_face_video", fake_submit)
    monkeypatch.setattr("app.api.face.wait_for_face_video_job", fake_wait)

    session = client.post("/api/face/session", json={"asset_id": asset["id"]})
    assert session.status_code == 201

    with client.websocket_connect(f"/api/face/session/{session.json()['id']}/stream") as websocket:
        websocket.send_json({"event": "start_session"})
        assert websocket.receive_json()["event"] == "session_started"
        websocket.send_json({"event": "audio_chunk", "audio": "AAAA"})
        assert websocket.receive_json()["event"] == "assistant_text"
        assert websocket.receive_json()["event"] == "speaking_video_pending"
        ready = websocket.receive_json()
        assert ready == {"event": "speaking_video_ready", "video_url": "https://cdn.example/speaking.mp4"}
        websocket.send_json({"event": "finish_session"})
        assert websocket.receive_json()["event"] == "session_finished"

    assert captured["job_kind"] == "speaking"
    assert "/api/face/media/" in captured["image_url"]
    assert "/api/face/media/" in captured["audio_url"]
