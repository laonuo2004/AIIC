from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
import wave
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from uuid import uuid4

import httpx

from app.core.config import get_settings
from app.models.entities import FaceAsset, FaceVideoJob


class VolcengineSetupError(RuntimeError):
    """Raised when a provider feature is requested without required env config."""


OMNIHUMAN_REQ_KEY = "jimeng_realman_avatar_picture_omni_v15"
OMNIHUMAN_ENDPOINT = "https://visual.volcengineapi.com"
OMNIHUMAN_REGION = "cn-north-1"
OMNIHUMAN_SERVICE = "cv"
READY_PROMPT = (
    "正面看镜头，平静呼吸，偶尔眨眼，动作轻微克制，"
    "首尾回到上传图片的中性正面姿态。"
)
LISTENING_PROMPT = (
    "正面看镜头，认真倾听，轻微点头，动作克制自然，"
    "首尾回到上传图片的中性正面姿态。"
)


def _require_speech_key() -> str:
    api_key = get_settings().volcengine_speech_api_key
    if not api_key:
        raise VolcengineSetupError("VOLCENGINE_SPEECH_API_KEY is required.")
    return api_key


def _require_voice_clone_token() -> str:
    settings = get_settings()
    token = settings.volcengine_speech_access_token or settings.volcengine_speech_api_key
    if not token:
        raise VolcengineSetupError(
            "VOLCENGINE_SPEECH_ACCESS_TOKEN or VOLCENGINE_SPEECH_API_KEY is required."
        )
    return token


def _require_speech_app_id() -> str:
    app_id = get_settings().volcengine_speech_app_id
    if not app_id:
        raise VolcengineSetupError("VOLCENGINE_SPEECH_APP_ID is required for voice cloning.")
    return app_id


def _safe_provider_error(message: str) -> RuntimeError:
    settings = get_settings()
    redacted = message
    for secret in (
        settings.volcengine_speech_api_key,
        settings.volcengine_speech_access_token,
        settings.volcengine_omnihuman_access_key_id,
        settings.volcengine_omnihuman_secret_access_key,
    ):
        if secret:
            redacted = redacted.replace(secret, "[redacted]")
    return RuntimeError(redacted)


def _require_voice_clone_speaker_id() -> str:
    speaker_id = get_settings().volcengine_voice_clone_speaker_id
    if not speaker_id:
        raise VolcengineSetupError(
            "VOLCENGINE_VOICE_CLONE_SPEAKER_ID is required. Configure an S_* speaker id "
            "from the Volcengine voice library before cloning."
        )
    return speaker_id


def _audio_format(asset: FaceAsset) -> str:
    suffix = Path(asset.audio_path).suffix.lower().lstrip(".")
    if suffix in {"wav", "mp3", "ogg", "m4a", "aac", "pcm"}:
        return suffix
    mime_map = {
        "audio/aac": "aac",
        "audio/m4a": "m4a",
        "audio/mp4": "m4a",
        "audio/mpeg": "mp3",
        "audio/ogg": "ogg",
        "audio/wav": "wav",
        "audio/x-m4a": "m4a",
        "audio/x-wav": "wav",
    }
    return mime_map.get(asset.audio_mime_type, "wav")


def _base64_audio(path: str) -> str:
    return base64.b64encode(Path(path).read_bytes()).decode("ascii")


def _require_omnihuman_keys() -> tuple[str, str]:
    settings = get_settings()
    if not settings.volcengine_omnihuman_access_key_id:
        raise VolcengineSetupError(
            "VOLCENGINE_OMNIHUMAN_ACCESS_KEY_ID is required for video generation."
        )
    if not settings.volcengine_omnihuman_secret_access_key:
        raise VolcengineSetupError(
            "VOLCENGINE_OMNIHUMAN_SECRET_ACCESS_KEY is required for video generation."
        )
    return (
        settings.volcengine_omnihuman_access_key_id,
        settings.volcengine_omnihuman_secret_access_key,
    )


def _signing_key(secret_key: str, date_stamp: str) -> bytes:
    date_key = hmac.new(
        secret_key.encode("utf-8"),
        date_stamp.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    region_key = hmac.new(date_key, OMNIHUMAN_REGION.encode("utf-8"), hashlib.sha256).digest()
    service_key = hmac.new(region_key, OMNIHUMAN_SERVICE.encode("utf-8"), hashlib.sha256).digest()
    return hmac.new(service_key, b"request", hashlib.sha256).digest()


def _visual_api_headers(
    action: str,
    payload_bytes: bytes,
    access_key: str,
    secret_key: str,
) -> dict[str, str]:
    now = datetime.now(UTC)
    x_date = now.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = now.strftime("%Y%m%d")
    payload_hash = hashlib.sha256(payload_bytes).hexdigest()
    query = urlencode({"Action": action, "Version": "2022-08-31"})
    canonical_headers = (
        "content-type:application/json\n"
        "host:visual.volcengineapi.com\n"
        f"x-content-sha256:{payload_hash}\n"
        f"x-date:{x_date}\n"
    )
    signed_headers = "content-type;host;x-content-sha256;x-date"
    canonical_request = "\n".join(
        ["POST", "/", query, canonical_headers, signed_headers, payload_hash]
    )
    credential_scope = f"{date_stamp}/{OMNIHUMAN_REGION}/{OMNIHUMAN_SERVICE}/request"
    string_to_sign = "\n".join(
        [
            "HMAC-SHA256",
            x_date,
            credential_scope,
            hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
        ]
    )
    signature = hmac.new(
        _signing_key(secret_key, date_stamp),
        string_to_sign.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return {
        "Authorization": (
            f"HMAC-SHA256 Credential={access_key}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, Signature={signature}"
        ),
        "Content-Type": "application/json",
        "Host": "visual.volcengineapi.com",
        "X-Content-Sha256": payload_hash,
        "X-Date": x_date,
    }


def _visual_api_request(action: str, payload: dict[str, Any]) -> dict[str, Any]:
    access_key, secret_key = _require_omnihuman_keys()
    payload_bytes = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    url = f"{OMNIHUMAN_ENDPOINT}?{urlencode({'Action': action, 'Version': '2022-08-31'})}"
    try:
        response = httpx.post(
            url,
            content=payload_bytes,
            headers=_visual_api_headers(action, payload_bytes, access_key, secret_key),
            timeout=60,
        )
    except httpx.HTTPError as exc:
        raise _safe_provider_error(f"OmniHuman provider request failed: {exc}") from exc
    if response.is_error:
        raise _safe_provider_error(_omnihuman_failure_message(response))
    body = response.json()
    if not isinstance(body, dict):
        raise _safe_provider_error("OmniHuman provider returned a non-JSON object response.")
    return body


def _omnihuman_failure_message(response: httpx.Response) -> str:
    details = [f"OmniHuman provider request failed ({response.status_code})."]
    try:
        body = response.json()
    except ValueError:
        return " ".join(details)
    if isinstance(body, dict):
        request_id = body.get("request_id")
        provider_code = body.get("code") or body.get("status")
        provider_message = body.get("message")
        if request_id:
            details.append(f"request_id={request_id}.")
        if provider_code is not None:
            details.append(f"provider_code={provider_code}.")
        if provider_message:
            details.append(f"provider_message={provider_message}.")
    return " ".join(details)


def _raise_for_omnihuman_body(body: dict[str, Any], action: str) -> None:
    code = body.get("code")
    if code == 10000:
        return
    request_id = body.get("request_id")
    message = body.get("message") or "unknown provider error"
    details = [f"OmniHuman {action} failed."]
    if request_id:
        details.append(f"request_id={request_id}.")
    if code is not None:
        details.append(f"provider_code={code}.")
    details.append(f"provider_message={message}.")
    raise _safe_provider_error(" ".join(details))


def _generated_audio_dir(asset: FaceAsset) -> Path:
    path = Path(get_settings().upload_dir) / "face-generated" / str(asset.user_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write_silent_wav(asset: FaceAsset, kind: str, seconds: float = 2.0) -> Path:
    path = _generated_audio_dir(asset) / f"{uuid4().hex}-{kind}.wav"
    sample_rate = 16_000
    frame_count = int(sample_rate * seconds)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(b"\x00\x00" * frame_count)
    return path


def _submit_omnihuman_video(
    *,
    image_url: str,
    audio_url: str,
    prompt: str,
) -> dict[str, str]:
    settings = get_settings()
    payload = {
        "req_key": OMNIHUMAN_REQ_KEY,
        "image_url": image_url,
        "audio_url": audio_url,
        "prompt": prompt,
        "output_resolution": settings.volcengine_omnihuman_output_resolution,
        "pe_fast_mode": settings.volcengine_omnihuman_fast_mode,
    }
    body = _visual_api_request("CVSubmitTask", payload)
    _raise_for_omnihuman_body(body, "CVSubmitTask")
    task_id = body.get("data", {}).get("task_id")
    if not task_id:
        raise _safe_provider_error("OmniHuman CVSubmitTask succeeded without task_id.")
    return {
        "status": "pending",
        "provider_task_id": str(task_id),
        "provider_request_id": str(body.get("request_id") or ""),
    }


def _provider_failure_message(response: httpx.Response) -> str:
    log_id = response.headers.get("X-Tt-Logid") or response.headers.get("X-Top-Request-Id")
    details: list[str] = [f"Voice clone provider request failed ({response.status_code})."]
    if log_id:
        details.append(f"log_id={log_id}.")
    try:
        body = response.json()
    except ValueError:
        return " ".join(details)

    base_resp = body.get("BaseResp") if isinstance(body, dict) else None
    provider_code = None
    provider_message = None
    if isinstance(base_resp, dict):
        provider_code = base_resp.get("StatusCode")
        provider_message = base_resp.get("StatusMessage")
    if isinstance(body, dict):
        provider_code = provider_code or body.get("code")
        provider_message = provider_message or body.get("message")
    if provider_code is not None:
        details.append(f"provider_code={provider_code}.")
    if provider_message:
        details.append(f"provider_message={provider_message}.")
    return " ".join(details)


def _raise_for_provider_body(body: dict[str, Any]) -> None:
    base_resp = body.get("BaseResp")
    if not isinstance(base_resp, dict):
        return
    status_code = base_resp.get("StatusCode")
    if status_code in (None, 0):
        return
    status_message = base_resp.get("StatusMessage") or "unknown provider error"
    raise _safe_provider_error(
        f"Voice clone provider request failed. provider_code={status_code}. "
        f"provider_message={status_message}."
    )


def clone_voice_from_asset(asset: FaceAsset, audio_url: str) -> dict[str, str]:
    settings = get_settings()
    token = _require_voice_clone_token()
    app_id = _require_speech_app_id()
    speaker_id = asset.speaker_id or _require_voice_clone_speaker_id()
    _ = audio_url
    payload = {
        "appid": app_id,
        "speaker_id": speaker_id,
        "audios": [
            {
                "audio_bytes": _base64_audio(asset.audio_path),
                "audio_format": _audio_format(asset),
            }
        ],
        "source": 2,
        "language": 0,
        "model_type": 4,
        "extra_params": json.dumps({"voice_clone_denoise_model_id": ""}),
    }
    headers = {
        "Authorization": f"Bearer; {token}",
        "Resource-Id": settings.volcengine_voice_clone_resource_id,
        "X-Api-Request-Id": uuid4().hex,
        "Content-Type": "application/json",
    }
    try:
        response = httpx.post(
            "https://openspeech.bytedance.com/api/v1/mega_tts/audio/upload",
            json=payload,
            headers=headers,
            timeout=60,
        )
    except httpx.HTTPError as exc:
        raise _safe_provider_error(f"Voice clone provider request failed: {exc}") from exc
    if response.is_error:
        raise _safe_provider_error(_provider_failure_message(response))

    body = response.json()
    _raise_for_provider_body(body)
    provider_speaker_id = (
        body.get("speaker_id")
        or body.get("data", {}).get("speaker_id")
        or body.get("SpeakerID")
        or speaker_id
    )
    return {"speaker_id": str(provider_speaker_id), "provider_status": "voice_ready"}


def generate_face_videos(
    asset: FaceAsset,
    image_url: str,
    media_url_for_token,
) -> dict[str, Any]:
    _require_omnihuman_keys()
    ready_audio = _write_silent_wav(asset, "ready")
    listening_audio = _write_silent_wav(asset, "listening")
    ready_token = uuid4().hex
    listening_token = uuid4().hex
    ready_result = _submit_omnihuman_video(
        image_url=image_url,
        audio_url=media_url_for_token(ready_token),
        prompt=READY_PROMPT,
    )
    return {
        "provider_status": "video_pending",
        "jobs": [
            {
                **ready_result,
                "kind": "ready",
                "audio_path": str(ready_audio),
                "audio_media_token": ready_token,
                "video_url": None,
            },
            {
                "kind": "listening",
                "status": "queued",
                "provider_task_id": None,
                "provider_request_id": None,
                "audio_path": str(listening_audio),
                "audio_media_token": listening_token,
                "video_url": None,
            },
        ],
        "image_url": image_url,
    }


def submit_prepared_face_video_job(
    job: FaceVideoJob,
    image_url: str,
    audio_url: str,
) -> dict[str, str]:
    _require_omnihuman_keys()
    if job.kind == "ready":
        prompt = READY_PROMPT
    elif job.kind == "listening":
        prompt = LISTENING_PROMPT
    else:
        raise RuntimeError(f"Unsupported prepared face video kind: {job.kind}.")
    return _submit_omnihuman_video(
        image_url=image_url,
        audio_url=audio_url,
        prompt=prompt,
    )


def submit_speaking_face_video(asset: FaceAsset, image_url: str, audio_url: str) -> dict[str, str]:
    _require_omnihuman_keys()
    return _submit_omnihuman_video(
        image_url=image_url,
        audio_url=audio_url,
        prompt="正面看镜头，像严格但专业的科研面试老师一样自然说话，口型与音频同步，动作克制。",
    )


def poll_face_video_job(job: FaceVideoJob) -> dict[str, str | None]:
    if not job.provider_task_id:
        raise RuntimeError("Face video job does not have a provider task id.")
    payload = {"req_key": OMNIHUMAN_REQ_KEY, "task_id": job.provider_task_id}
    body = _visual_api_request("CVGetResult", payload)
    _raise_for_omnihuman_body(body, "CVGetResult")
    data = body.get("data")
    if not isinstance(data, dict):
        raise _safe_provider_error("OmniHuman CVGetResult succeeded without data.")
    provider_status = str(data.get("status") or "processing")
    if provider_status == "done":
        video_url = data.get("video_url")
        if not video_url:
            raise _safe_provider_error("OmniHuman task finished without video_url.")
        return {
            "status": "done",
            "video_url": str(video_url),
            "provider_request_id": str(body.get("request_id") or ""),
        }
    if provider_status in {"processing", "in_queue", "generating"}:
        return {
            "status": "pending",
            "video_url": None,
            "provider_request_id": str(body.get("request_id") or ""),
        }
    raise _safe_provider_error(f"OmniHuman task is not recoverable: {provider_status}.")


def wait_for_face_video_job(job: FaceVideoJob) -> dict[str, str | None]:
    settings = get_settings()
    deadline = time.monotonic() + settings.volcengine_omnihuman_max_wait_seconds
    last_result: dict[str, str | None] | None = None
    while time.monotonic() <= deadline:
        last_result = poll_face_video_job(job)
        if last_result["status"] == "done":
            return last_result
        time.sleep(settings.volcengine_omnihuman_poll_interval_seconds)
    raise TimeoutError(
        "OmniHuman speaking video timed out after "
        f"{settings.volcengine_omnihuman_max_wait_seconds}s."
    )


class VolcengineRealtimeBridge:
    def __init__(self, speaker_id: str):
        self.speaker_id = speaker_id
        self.settings = get_settings()

    async def start(self) -> dict[str, str]:
        _require_speech_key()
        return {
            "event": "session_started",
            "speaker_id": self.speaker_id,
            "resource_id": self.settings.volcengine_realtime_resource_id,
        }

    async def receive_client_event(self, event: dict[str, Any]) -> list[dict[str, Any]]:
        # The browser/backend protocol is stable and testable even while the provider-specific
        # binary WebSocket bridge is wired during live smoke testing.
        if event.get("event") == "interrupt":
            return [{"event": "tts_ended"}]
        if event.get("event") == "end_asr":
            return [{"event": "asr_final", "text": ""}]
        return []


def create_realtime_bridge(speaker_id: str) -> VolcengineRealtimeBridge:
    return VolcengineRealtimeBridge(speaker_id)
