import asyncio
import base64
import re
from pathlib import Path
from urllib.parse import urlparse

import httpx
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.models.entities import FaceAsset, FaceVideoJob
from app.services.volcengine_face import (
    LISTENING_PROMPT,
    READY_PROMPT,
    SPEAKING_PROMPT,
    VolcengineRealtimeBridge,
    VolcengineSetupError,
    _pack_volcengine_frame,
    _parse_volcengine_frame,
    clone_voice_from_asset,
    generate_face_videos,
    submit_speaking_face_video,
)

PNG_1X1 = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


def test_omnihuman_prompts_are_chinese_only():
    prompts = [READY_PROMPT, LISTENING_PROMPT, SPEAKING_PROMPT]

    assert all(prompt for prompt in prompts)
    assert all(not re.search(r"[A-Za-z]", prompt) for prompt in prompts)


def test_volcengine_start_connection_frame_matches_documented_example():
    frame = _pack_volcengine_frame(event_id=1, payload=b"{}")

    assert frame == bytes([17, 20, 16, 0, 0, 0, 0, 1, 0, 0, 0, 2, 123, 125])


def test_volcengine_frame_parser_extracts_tts_audio_payload():
    session_id = "3c791a7d-227a-4446-993b-24f9e302cc98"
    payload = b"OggS" + b"\x00" * 4
    frame = _pack_volcengine_frame(
        event_id=352,
        payload=payload,
        session_id=session_id,
        message_type=0xB,
        serialization=0x0,
    )

    parsed = _parse_volcengine_frame(frame)

    assert parsed["event_id"] == 352
    assert parsed["session_id"] == session_id
    assert parsed["payload"] == payload


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


def test_video_generation_uses_background_audio_for_ready_and_listening_jobs(
    tmp_path,
    monkeypatch,
):
    image_path = tmp_path / "face.png"
    audio_path = tmp_path / "voice.wav"
    background_audio_path = tmp_path / "background.mp3"
    image_path.write_bytes(PNG_1X1)
    audio_path.write_bytes(b"RIFF....WAVEfmt " + b"\x00" * 32)
    background_audio_path.write_bytes(b"ID3background-audio")
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
    monkeypatch.setenv("VOLCENGINE_OMNIHUMAN_IDLE_AUDIO_PATH", str(background_audio_path))
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
    assert [job["audio_media_token"] for job in result["jobs"]] != ["audio-token", "audio-token"]
    assert all(Path(job["audio_path"]).exists() for job in result["jobs"])
    assert all(Path(job["audio_path"]).suffix == ".mp3" for job in result["jobs"])
    assert all(
        Path(job["audio_path"]).read_bytes() == b"ID3background-audio"
        for job in result["jobs"]
    )

    ready_payload = captured[0]["payload"]
    assert ready_payload["req_key"] == "jimeng_realman_avatar_picture_omni_v15"
    assert ready_payload["image_url"] == "http://public.example/api/face/media/image-token"
    assert "/api/face/media/" in ready_payload["audio_url"]
    assert "audio-token" not in ready_payload["audio_url"]
    assert ready_payload["output_resolution"] == 720
    assert ready_payload["pe_fast_mode"] is True
    assert "平静呼吸" in ready_payload["prompt"]
    assert ready_payload["prompt"].isascii() is False


def test_speaking_video_submit_retries_transient_omnihuman_504(monkeypatch, tmp_path):
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
    calls = 0

    def fake_visual_request(action, payload):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("OmniHuman provider request failed (504).")
        return {
            "code": 10000,
            "data": {"task_id": "speaking-task"},
            "request_id": "speaking-request",
            "message": "Success",
        }

    monkeypatch.setenv("VOLCENGINE_OMNIHUMAN_ACCESS_KEY_ID", "ak")
    monkeypatch.setenv("VOLCENGINE_OMNIHUMAN_SECRET_ACCESS_KEY", "sk")
    get_settings.cache_clear()
    monkeypatch.setattr("app.services.volcengine_face._visual_api_request", fake_visual_request)

    try:
        result = submit_speaking_face_video(
            asset,
            "http://public.example/api/face/media/image-token",
            "http://public.example/api/face/media/audio-token",
        )
    finally:
        get_settings.cache_clear()

    assert calls == 2
    assert result["provider_task_id"] == "speaking-task"


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
    assert response.headers["content-type"].startswith("audio/wav")
    missing = client.get("/api/face/media/../../etc/passwd")
    assert missing.status_code == 404


def test_generated_media_token_serves_generated_background_mp3(client, tmp_path):
    _register_and_login(client)
    asset = _upload_asset(client)
    generated_dir = Path(get_settings().upload_dir) / "face-generated"
    generated_dir.mkdir(parents=True, exist_ok=True)
    generated_audio = generated_dir / "ready.mp3"
    generated_audio.write_bytes(b"ID3background")

    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        db.add(
            FaceVideoJob(
                asset_id=asset["id"],
                kind="ready",
                status="pending",
                audio_path=str(generated_audio),
                audio_media_token="generated-mp3-token",
            )
        )
        db.commit()
    finally:
        db.close()

    response = client.get("/api/face/media/generated-mp3-token")

    assert response.status_code == 200
    assert response.content == b"ID3background"
    assert response.headers["content-type"].startswith("audio/mpeg")


def test_realtime_bridge_requires_realtime_app_id_and_token(monkeypatch):
    monkeypatch.setenv("VOLCENGINE_REALTIME_APP_ID", "")
    monkeypatch.setenv("VOLCENGINE_REALTIME_ACCESS_TOKEN", "")
    monkeypatch.setenv("VOLCENGINE_SPEECH_APP_ID", "")
    monkeypatch.setenv("VOLCENGINE_SPEECH_ACCESS_TOKEN", "")
    get_settings.cache_clear()

    try:
        bridge = VolcengineRealtimeBridge("S_demo")
        try:
            asyncio.run(bridge.start())
        except VolcengineSetupError as exc:
            assert "VOLCENGINE_REALTIME_APP_ID" in str(exc)
            assert "VOLCENGINE_REALTIME_ACCESS_TOKEN" not in str(exc)
        else:
            raise AssertionError("Expected realtime setup error")
    finally:
        get_settings.cache_clear()


def test_realtime_bridge_falls_back_to_speech_app_id_and_token(monkeypatch):
    captured: dict[str, object] = {}

    class FakeProviderWebSocket:
        async def send(self, payload):
            return None

        async def recv(self):
            raise TimeoutError

        async def close(self):
            return None

    async def fake_connect(url, additional_headers, open_timeout):
        captured["headers"] = additional_headers
        return FakeProviderWebSocket()

    monkeypatch.setenv("VOLCENGINE_REALTIME_APP_ID", "")
    monkeypatch.setenv("VOLCENGINE_REALTIME_ACCESS_TOKEN", "")
    monkeypatch.setenv("VOLCENGINE_SPEECH_APP_ID", "speech-app-id")
    monkeypatch.setenv("VOLCENGINE_SPEECH_ACCESS_TOKEN", "speech-token")
    get_settings.cache_clear()
    monkeypatch.setattr("app.services.volcengine_face.websockets.connect", fake_connect)

    try:
        bridge = VolcengineRealtimeBridge("S_demo")
        asyncio.run(bridge.start())
    finally:
        get_settings.cache_clear()

    headers = captured["headers"]
    assert headers["X-Api-App-ID"] == "speech-app-id"
    assert headers["X-Api-Access-Key"] == "speech-token"


def test_realtime_bridge_sends_session_config_and_audio_only(monkeypatch):
    sent: list[bytes] = []
    provider_events = [
        _pack_volcengine_frame(
            event_id=150,
            payload=b'{"dialog_id":"dialog-demo"}',
            session_id="session-demo",
            message_type=0x9,
        )
    ]

    class FakeProviderWebSocket:
        async def send(self, payload):
            sent.append(payload)

        async def recv(self):
            if provider_events:
                return provider_events.pop(0)
            raise TimeoutError

        async def close(self):
            return None

    async def fake_connect(url, additional_headers, open_timeout):
        assert url == "wss://openspeech.bytedance.com/api/v3/realtime/dialogue"
        assert "Authorization" not in additional_headers
        assert additional_headers["X-Api-App-ID"] == "test-app-id"
        assert additional_headers["X-Api-Access-Key"] == "test-token"
        assert additional_headers["X-Api-Resource-Id"] == "volc.speech.dialog"
        assert additional_headers["X-Api-App-Key"] == "PlgvMymc7f3tQnJ6"
        assert additional_headers["X-Api-Connect-Id"]
        assert open_timeout > 0
        return FakeProviderWebSocket()

    monkeypatch.setenv("VOLCENGINE_REALTIME_APP_ID", "test-app-id")
    monkeypatch.setenv("VOLCENGINE_REALTIME_ACCESS_TOKEN", "test-token")
    monkeypatch.setenv("VOLCENGINE_REALTIME_MODEL", "O")
    monkeypatch.setenv("VOLCENGINE_REALTIME_BOT_NAME", "ResearchMocker")
    monkeypatch.setenv("VOLCENGINE_REALTIME_SPEAKING_STYLE", "严格、专业、简洁")
    monkeypatch.setenv("VOLCENGINE_REALTIME_OPENING", "请用一句话开始科研项目深挖面试。")
    get_settings.cache_clear()
    monkeypatch.setattr("app.services.volcengine_face.websockets.connect", fake_connect)

    try:
        bridge = VolcengineRealtimeBridge("S_demo")
        started = asyncio.run(bridge.start())
        asyncio.run(bridge.receive_client_event({"event": "audio_chunk", "audio": "AAAA"}))
    finally:
        get_settings.cache_clear()

    assert started["event"] == "session_started"
    assert started["speaker_id"] == "S_demo"
    assert _parse_volcengine_frame(sent[0])["event_id"] == 1
    session_frame = _parse_volcengine_frame(sent[1])
    assert session_frame["event_id"] == 100
    session_config = __import__("json").loads(session_frame["payload"])
    assert session_config["tts"]["speaker"] == "S_demo"
    assert session_config["asr"]["audio_info"]["format"] == "pcm_s16le"
    assert session_config["asr"]["audio_info"]["channel"] == 1
    assert session_config["dialog"]["bot_name"] == "ResearchMocker"
    assert session_config["dialog"]["speaking_style"] == "严格、专业、简洁"
    assert session_config["dialog"]["extra"]["model"] == "1.2.1.1"
    assert "科研项目深挖面试官" in session_config["dialog"]["system_role"]
    assert "不要让用户写代码" in session_config["dialog"]["system_role"]
    audio_frame = _parse_volcengine_frame(sent[2])
    assert audio_frame["event_id"] == 200
    assert audio_frame["payload"] == base64.b64decode("AAAA")


def test_realtime_bridge_surfaces_provider_session_failure(monkeypatch):
    class FakeProviderWebSocket:
        async def send(self, payload):
            return None

        async def recv(self):
            return _pack_volcengine_frame(
                event_id=153,
                payload=b'{"error":"speaker not supported"}',
                session_id="session-demo",
                message_type=0x9,
            )

        async def close(self):
            return None

    async def fake_connect(url, additional_headers, open_timeout):
        return FakeProviderWebSocket()

    monkeypatch.setenv("VOLCENGINE_REALTIME_APP_ID", "test-app-id")
    monkeypatch.setenv("VOLCENGINE_REALTIME_ACCESS_TOKEN", "test-token")
    monkeypatch.setenv("VOLCENGINE_REALTIME_RECEIVE_TIMEOUT_SECONDS", "0.001")
    get_settings.cache_clear()
    monkeypatch.setattr("app.services.volcengine_face.websockets.connect", fake_connect)

    try:
        bridge = VolcengineRealtimeBridge("S_demo")
        try:
            asyncio.run(bridge.start())
        except RuntimeError as exc:
            assert "speaker not supported" in str(exc)
        else:
            raise AssertionError("Expected provider session failure")
    finally:
        get_settings.cache_clear()


def test_realtime_bridge_ignores_provider_text_and_maps_audio(monkeypatch):
    provider_events = [
        _pack_volcengine_frame(
            event_id=150,
            payload=b'{"dialog_id":"dialog-demo"}',
            session_id="session-demo",
            message_type=0x9,
        ),
        {"event": "asr_partial", "text": "用户文本"},
        {"event": "assistant_text", "text": "助手文本"},
        {"event": "response.audio.delta", "delta": "UklGRg==", "mime": "audio/wav"},
    ]

    class FakeProviderWebSocket:
        async def send(self, payload):
            return None

        async def recv(self):
            if provider_events:
                event = provider_events.pop(0)
                if isinstance(event, bytes):
                    return event
                return __import__("json").dumps(event)
            raise TimeoutError

        async def close(self):
            return None

    async def fake_connect(url, additional_headers, open_timeout):
        return FakeProviderWebSocket()

    monkeypatch.setenv("VOLCENGINE_REALTIME_APP_ID", "test-app-id")
    monkeypatch.setenv("VOLCENGINE_REALTIME_ACCESS_TOKEN", "test-token")
    get_settings.cache_clear()
    monkeypatch.setattr("app.services.volcengine_face.websockets.connect", fake_connect)

    try:
        bridge = VolcengineRealtimeBridge("S_demo")
        asyncio.run(bridge.start())
        events = asyncio.run(bridge.receive_client_event({"event": "end_asr"}))
    finally:
        get_settings.cache_clear()

    assert events == [{"event": "assistant_audio", "audio": "UklGRg==", "mime": "audio/wav"}]


def test_realtime_bridge_buffers_audio_deltas_until_done(monkeypatch):
    provider_events = [
        _pack_volcengine_frame(
            event_id=150,
            payload=b'{"dialog_id":"dialog-demo"}',
            session_id="session-demo",
            message_type=0x9,
        ),
        {"event": "response.audio.delta", "delta": "QQ==", "mime": "audio/wav"},
        {"event": "response.audio.delta", "delta": "Qg==", "mime": "audio/wav"},
        {"event": "response.audio.done"},
    ]

    class FakeProviderWebSocket:
        async def send(self, payload):
            return None

        async def recv(self):
            if provider_events:
                event = provider_events.pop(0)
                if isinstance(event, bytes):
                    return event
                return __import__("json").dumps(event)
            raise TimeoutError

        async def close(self):
            return None

    async def fake_connect(url, additional_headers, open_timeout):
        return FakeProviderWebSocket()

    monkeypatch.setenv("VOLCENGINE_REALTIME_APP_ID", "test-app-id")
    monkeypatch.setenv("VOLCENGINE_REALTIME_ACCESS_TOKEN", "test-token")
    get_settings.cache_clear()
    monkeypatch.setattr("app.services.volcengine_face.websockets.connect", fake_connect)

    try:
        bridge = VolcengineRealtimeBridge("S_demo")
        asyncio.run(bridge.start())
        events = asyncio.run(bridge.receive_client_event({"event": "end_asr"}))
    finally:
        get_settings.cache_clear()

    assert events == [{"event": "assistant_audio", "audio": "QUI=", "mime": "audio/wav"}]


def test_realtime_bridge_waits_for_delayed_audio_after_end_asr(monkeypatch):
    provider_events = [
        TimeoutError,
        {"event": "response.audio.delta", "delta": "QQ==", "mime": "audio/wav"},
        {"event": "response.audio.done"},
    ]

    class FakeProviderWebSocket:
        async def send(self, payload):
            return None

        async def recv(self):
            event = provider_events.pop(0)
            if event is TimeoutError:
                raise TimeoutError
            return __import__("json").dumps(event)

        async def close(self):
            return None

    async def fake_connect(url, additional_headers, open_timeout):
        return FakeProviderWebSocket()

    monkeypatch.setenv("VOLCENGINE_REALTIME_APP_ID", "test-app-id")
    monkeypatch.setenv("VOLCENGINE_REALTIME_ACCESS_TOKEN", "test-token")
    monkeypatch.setenv("VOLCENGINE_REALTIME_RESPONSE_TIMEOUT_SECONDS", "1")
    get_settings.cache_clear()
    monkeypatch.setattr("app.services.volcengine_face.websockets.connect", fake_connect)

    try:
        bridge = VolcengineRealtimeBridge("S_demo")
        asyncio.run(bridge.start())
        events = asyncio.run(bridge.receive_client_event({"event": "end_asr"}))
    finally:
        get_settings.cache_clear()

    assert events == [{"event": "assistant_audio", "audio": "QQ==", "mime": "audio/wav"}]


def test_realtime_bridge_reports_timeout_when_provider_returns_no_reply(monkeypatch):
    class FakeProviderWebSocket:
        async def send(self, payload):
            return None

        async def recv(self):
            raise TimeoutError

        async def close(self):
            return None

    async def fake_connect(url, additional_headers, open_timeout):
        return FakeProviderWebSocket()

    monkeypatch.setenv("VOLCENGINE_REALTIME_APP_ID", "test-app-id")
    monkeypatch.setenv("VOLCENGINE_REALTIME_ACCESS_TOKEN", "test-token")
    monkeypatch.setenv("VOLCENGINE_REALTIME_RECEIVE_TIMEOUT_SECONDS", "0.001")
    monkeypatch.setenv("VOLCENGINE_REALTIME_RESPONSE_TIMEOUT_SECONDS", "0.001")
    get_settings.cache_clear()
    monkeypatch.setattr("app.services.volcengine_face.websockets.connect", fake_connect)

    try:
        bridge = VolcengineRealtimeBridge("S_demo")
        asyncio.run(bridge.start())
        events = asyncio.run(bridge.receive_client_event({"event": "end_asr"}))
    finally:
        get_settings.cache_clear()

    assert events == [
        {
            "event": "error",
            "message": "Realtime provider did not return audio before timeout.",
        }
    ]


def test_realtime_session_suppresses_provider_text_events(client, monkeypatch):
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
        assert websocket.receive_json()["event"] == "error"
        assert websocket.receive_json()["event"] == "assistant_audio"
        websocket.send_json({"event": "finish_session"})
        assert websocket.receive_json()["event"] == "session_finished"


def test_realtime_session_surfaces_provider_start_failure(client, monkeypatch):
    _register_and_login(client)
    asset = _upload_asset(client)
    monkeypatch.setattr(
        "app.api.face.clone_voice_from_asset",
        lambda asset_record, audio_url: {"speaker_id": "demo-speaker-001"},
    )
    client.post(f"/api/face/assets/{asset['id']}/voice-clone")

    class FakeRealtimeBridge:
        async def start(self):
            raise RuntimeError("Realtime provider connection failed: handshake rejected")

        async def receive_client_event(self, event):
            return []

    monkeypatch.setattr(
        "app.api.face.create_realtime_bridge",
        lambda speaker_id: FakeRealtimeBridge(),
    )

    session = client.post("/api/face/session", json={"asset_id": asset["id"]})

    with client.websocket_connect(f"/api/face/session/{session.json()['id']}/stream") as websocket:
        websocket.send_json({"event": "start_session"})
        event = websocket.receive_json()

    assert event == {
        "event": "error",
        "message": "Realtime provider connection failed: handshake rejected",
    }


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
        audio_token = urlparse(audio_url).path.rsplit("/", 1)[-1]
        from app.core.database import SessionLocal

        db = SessionLocal()
        try:
            captured["audio_visible_before_submit"] = (
                db.query(FaceVideoJob)
                .filter(FaceVideoJob.audio_media_token == audio_token)
                .first()
                is not None
            )
        finally:
            db.close()
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
        assert websocket.receive_json()["event"] == "speaking_video_pending"
        ready = websocket.receive_json()
        assert ready == {"event": "speaking_video_ready", "video_url": "https://cdn.example/speaking.mp4"}
        websocket.send_json({"event": "finish_session"})
        assert websocket.receive_json()["event"] == "session_finished"

    assert captured["job_kind"] == "speaking"
    assert "/api/face/media/" in captured["image_url"]
    assert "/api/face/media/" in captured["audio_url"]
    assert captured["audio_visible_before_submit"] is True


def test_ready_omnihuman_failure_includes_stage_context(client, monkeypatch):
    _register_and_login(client)
    asset = _upload_asset(client)
    monkeypatch.setattr(
        "app.api.face.clone_voice_from_asset",
        lambda asset_record, audio_url: {"speaker_id": "demo-speaker-001"},
    )
    client.post(f"/api/face/assets/{asset['id']}/voice-clone")
    monkeypatch.setenv("VOLCENGINE_OMNIHUMAN_ACCESS_KEY_ID", "ak")
    monkeypatch.setenv("VOLCENGINE_OMNIHUMAN_SECRET_ACCESS_KEY", "secret-key-not-in-message")
    monkeypatch.setenv("VOLCENGINE_OMNIHUMAN_IDLE_AUDIO_PATH", str(Path(__file__)))
    get_settings.cache_clear()
    monkeypatch.setattr(
        "app.services.volcengine_face._visual_api_request",
        lambda action, payload: (_ for _ in ()).throw(
            RuntimeError("50514 Pre Audio Risk Not Pass")
        ),
    )

    response = client.post(f"/api/face/assets/{asset['id']}/videos")

    assert response.status_code == 502
    assert "stage=ready" in response.json()["detail"]
    assert "50514 Pre Audio Risk Not Pass" in response.json()["detail"]


def test_listening_omnihuman_failure_includes_stage_context(client, monkeypatch):
    _register_and_login(client)
    asset = _upload_asset(client)
    monkeypatch.setattr(
        "app.api.face.clone_voice_from_asset",
        lambda asset_record, audio_url: {"speaker_id": "demo-speaker-001"},
    )
    client.post(f"/api/face/assets/{asset['id']}/voice-clone")

    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        db.add(
            FaceVideoJob(
                asset_id=asset["id"],
                kind="ready",
                status="done",
                video_url="https://cdn.example/ready.mp4",
            )
        )
        db.add(
            FaceVideoJob(
                asset_id=asset["id"],
                kind="listening",
                status="queued",
                audio_path=str(Path(__file__)),
                audio_media_token="listening-audio-token",
            )
        )
        db.commit()
    finally:
        db.close()

    monkeypatch.setattr(
        "app.api.face.submit_prepared_face_video_job",
        lambda job, image_url, audio_url: (_ for _ in ()).throw(
            RuntimeError("50514 Pre Audio Risk Not Pass")
        ),
    )

    response = client.post(f"/api/face/assets/{asset['id']}/videos/poll")

    assert response.status_code == 502
    assert "stage=listening" in response.json()["detail"]
    assert "50514 Pre Audio Risk Not Pass" in response.json()["detail"]


def test_speaking_omnihuman_failure_includes_stage_context(client, monkeypatch):
    _register_and_login(client)
    asset = _upload_asset(client)
    monkeypatch.setattr(
        "app.api.face.clone_voice_from_asset",
        lambda asset_record, audio_url: {"speaker_id": "demo-speaker-001"},
    )
    client.post(f"/api/face/assets/{asset['id']}/voice-clone")

    class FakeRealtimeBridge:
        async def start(self):
            return {"event": "session_started"}

        async def receive_client_event(self, event):
            if event["event"] == "audio_chunk":
                return [{"event": "assistant_audio", "audio": "UklGRg==", "mime": "audio/wav"}]
            return []

    monkeypatch.setattr(
        "app.api.face.create_realtime_bridge",
        lambda speaker_id: FakeRealtimeBridge(),
    )
    monkeypatch.setattr(
        "app.api.face.submit_speaking_face_video",
        lambda asset_record, image_url, audio_url: (_ for _ in ()).throw(
            RuntimeError("50514 Pre Audio Risk Not Pass")
        ),
    )

    session = client.post("/api/face/session", json={"asset_id": asset["id"]})
    with client.websocket_connect(f"/api/face/session/{session.json()['id']}/stream") as websocket:
        websocket.send_json({"event": "start_session"})
        websocket.receive_json()
        websocket.send_json({"event": "audio_chunk", "audio": "AAAA"})
        error = websocket.receive_json()

    assert error["event"] == "error"
    assert "stage=speaking" in error["message"]
    assert "50514 Pre Audio Risk Not Pass" in error["message"]
