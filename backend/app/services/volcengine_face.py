from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import logging
import shutil
import struct
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from uuid import uuid4

import httpx
import websockets
from websockets.exceptions import ConnectionClosed

from app.core.config import get_settings
from app.models.entities import FaceAsset, FaceVideoJob

logger = logging.getLogger(__name__)


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
SPEAKING_PROMPT = (
    "正面看镜头，像严格但专业的科研面试老师一样自然说话，"
    "口型与音频同步，动作克制。"
)
FACE_REALTIME_SYSTEM_ROLE = (
    "你是 ResearchMocker 的中文科研项目深挖面试官。你面向 CS/AI 本科生保研、科研实习、"
    "实验室面试场景进行口语面试。你的风格严格但专业，像真实老师或审稿人一样追问，"
    "一次只问一个短问题。重点追问个人贡献、方法必要性、替代方案、实验证据、对比方法、"
    "失败案例、指标是否支持结论、项目故事是否清楚。遇到含糊表述、没有证据的提升、"
    "笼统的“我负责模型”等说法，要继续追问。不要安慰式回答，不做人身攻击，不羞辱用户，"
    "不要让用户写代码或公式。回复必须适合口语面试，简洁、直接、可继续追问。"
)
VOLCENGINE_EVENT_START_CONNECTION = 1
VOLCENGINE_EVENT_START_SESSION = 100
VOLCENGINE_EVENT_FINISH_SESSION = 102
VOLCENGINE_EVENT_TASK_REQUEST = 200
VOLCENGINE_EVENT_END_ASR = 400
VOLCENGINE_EVENT_CLIENT_INTERRUPT = 515
VOLCENGINE_EVENT_SESSION_STARTED = 150
VOLCENGINE_EVENT_CONNECTION_FAILED = 51
VOLCENGINE_EVENT_SESSION_FAILED = 153
VOLCENGINE_EVENT_TTS_RESPONSE = 352
VOLCENGINE_EVENT_TTS_ENDED = 359
VOLCENGINE_EVENT_DIALOG_COMMON_ERROR = 599


def _require_speech_key() -> str:
    api_key = get_settings().volcengine_speech_api_key
    if not api_key:
        raise VolcengineSetupError("VOLCENGINE_SPEECH_API_KEY is required.")
    return api_key


def _require_realtime_config() -> tuple[str, str]:
    settings = get_settings()
    app_id = settings.volcengine_realtime_app_id or settings.volcengine_speech_app_id
    access_token = (
        settings.volcengine_realtime_access_token or settings.volcengine_speech_access_token
    )
    if not app_id:
        raise VolcengineSetupError(
            "VOLCENGINE_REALTIME_APP_ID or VOLCENGINE_SPEECH_APP_ID is required."
        )
    if not access_token:
        raise VolcengineSetupError(
            "VOLCENGINE_REALTIME_ACCESS_TOKEN or VOLCENGINE_SPEECH_ACCESS_TOKEN is required."
        )
    return app_id, access_token


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
        settings.volcengine_realtime_access_token,
        settings.volcengine_omnihuman_access_key_id,
        settings.volcengine_omnihuman_secret_access_key,
    ):
        if secret and len(secret) >= 8:
            redacted = redacted.replace(secret, "[redacted]")
    return RuntimeError(redacted)


def _with_stage(stage: str, message: str) -> str:
    if message.startswith("stage="):
        return message
    return f"stage={stage}: {message}"


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


def _pack_volcengine_frame(
    *,
    event_id: int,
    payload: bytes,
    session_id: str | None = None,
    message_type: int = 0x1,
    serialization: int = 0x1,
) -> bytes:
    header = bytes(
        [
            0x11,
            (message_type << 4) | 0x4,
            (serialization << 4) | 0x0,
            0x00,
        ]
    )
    parts = [header, struct.pack(">I", event_id)]
    if session_id is not None:
        encoded_session_id = session_id.encode("utf-8")
        parts.extend([struct.pack(">I", len(encoded_session_id)), encoded_session_id])
    parts.extend([struct.pack(">I", len(payload)), payload])
    return b"".join(parts)


def _parse_volcengine_frame(raw: bytes) -> dict[str, Any]:
    if len(raw) < 12:
        raise ValueError("Volcengine realtime frame was too short.")
    header_size = (raw[0] & 0x0F) * 4
    message_type = raw[1] >> 4
    serialization = raw[2] >> 4
    offset = header_size
    event_id = struct.unpack(">I", raw[offset : offset + 4])[0]
    offset += 4
    session_id = None
    if len(raw) >= offset + 4:
        possible_session_id_size = struct.unpack(">I", raw[offset : offset + 4])[0]
        remaining_after_size = len(raw) - offset - 4
        if 0 < possible_session_id_size <= remaining_after_size - 4:
            possible_session_id = raw[offset + 4 : offset + 4 + possible_session_id_size]
            try:
                decoded_session_id = possible_session_id.decode("utf-8")
            except UnicodeDecodeError:
                decoded_session_id = ""
            if decoded_session_id:
                session_id = decoded_session_id
                offset += 4 + possible_session_id_size
    if len(raw) < offset + 4:
        raise ValueError("Volcengine realtime frame was missing payload size.")
    payload_size = struct.unpack(">I", raw[offset : offset + 4])[0]
    offset += 4
    payload = raw[offset : offset + payload_size]
    if len(payload) != payload_size:
        raise ValueError("Volcengine realtime frame payload was truncated.")
    return {
        "event_id": event_id,
        "message_type": message_type,
        "serialization": serialization,
        "session_id": session_id,
        "payload": payload,
    }


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


def _resolve_idle_audio_path() -> Path:
    configured = get_settings().volcengine_omnihuman_idle_audio_path
    if not configured:
        raise VolcengineSetupError(
            "VOLCENGINE_OMNIHUMAN_IDLE_AUDIO_PATH is required for Ready/Listening videos."
        )
    configured_path = Path(configured)
    candidates = [configured_path]
    if not configured_path.is_absolute():
        cwd = Path.cwd()
        candidates.extend([cwd / configured_path, cwd.parent / configured_path])
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate
    raise VolcengineSetupError(
        "VOLCENGINE_OMNIHUMAN_IDLE_AUDIO_PATH does not point to a readable audio file."
    )


def _copy_idle_audio(asset: FaceAsset, kind: str) -> Path:
    source = _resolve_idle_audio_path()
    suffix = source.suffix.lower() or ".mp3"
    path = _generated_audio_dir(asset) / f"{uuid4().hex}-{kind}{suffix}"
    shutil.copyfile(source, path)
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
    body = _visual_api_request_with_retry("CVSubmitTask", payload)
    _raise_for_omnihuman_body(body, "CVSubmitTask")
    task_id = body.get("data", {}).get("task_id")
    if not task_id:
        raise _safe_provider_error("OmniHuman CVSubmitTask succeeded without task_id.")
    return {
        "status": "pending",
        "provider_task_id": str(task_id),
        "provider_request_id": str(body.get("request_id") or ""),
    }


def _visual_api_request_with_retry(action: str, payload: dict[str, Any]) -> dict[str, Any]:
    max_attempts = 2
    last_error: RuntimeError | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return _visual_api_request(action, payload)
        except RuntimeError as exc:
            last_error = exc
            if not _is_transient_omnihuman_error(str(exc)) or attempt == max_attempts:
                raise
            logger.warning(
                "Retrying transient OmniHuman %s failure after attempt %s.",
                action,
                attempt,
            )
            time.sleep(1)
    if last_error is not None:
        raise last_error
    raise _safe_provider_error("OmniHuman provider request did not run.")


def _is_transient_omnihuman_error(message: str) -> bool:
    transient_markers = ("(502)", "(503)", "(504)", "timed out", "ReadTimeout")
    return any(marker in message for marker in transient_markers)


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
    ready_audio = _copy_idle_audio(asset, "ready")
    listening_audio = _copy_idle_audio(asset, "listening")
    ready_token = uuid4().hex
    listening_token = uuid4().hex
    try:
        ready_result = _submit_omnihuman_video(
            image_url=image_url,
            audio_url=media_url_for_token(ready_token),
            prompt=READY_PROMPT,
        )
    except RuntimeError as exc:
        raise _safe_provider_error(_with_stage("ready", str(exc))) from exc
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
    try:
        return _submit_omnihuman_video(
            image_url=image_url,
            audio_url=audio_url,
            prompt=prompt,
        )
    except RuntimeError as exc:
        raise _safe_provider_error(_with_stage(job.kind, str(exc))) from exc


def submit_speaking_face_video(asset: FaceAsset, image_url: str, audio_url: str) -> dict[str, str]:
    _require_omnihuman_keys()
    try:
        return _submit_omnihuman_video(
            image_url=image_url,
            audio_url=audio_url,
            prompt=SPEAKING_PROMPT,
        )
    except RuntimeError as exc:
        raise _safe_provider_error(_with_stage("speaking", str(exc))) from exc


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
        self.websocket = None
        self.session_id = str(uuid4())
        self._audio_chunks: list[bytes] = []
        self._audio_mime = "audio/wav"

    async def start(self) -> dict[str, str]:
        app_id, access_token = _require_realtime_config()
        headers = {
            "X-Api-App-ID": app_id,
            "X-Api-Access-Key": access_token,
            "X-Api-Resource-Id": self.settings.volcengine_realtime_resource_id,
            "X-Api-App-Key": self.settings.volcengine_realtime_app_key,
            "X-Api-Connect-Id": uuid4().hex,
        }
        try:
            self.websocket = await websockets.connect(
                self.settings.volcengine_realtime_ws_url,
                additional_headers=headers,
                open_timeout=self.settings.volcengine_realtime_open_timeout_seconds,
            )
            await self._send_provider_event(VOLCENGINE_EVENT_START_CONNECTION, {})
            await self._send_provider_event(
                VOLCENGINE_EVENT_START_SESSION,
                self._session_config(),
                session_id=self.session_id,
            )
            await self._wait_for_provider_session_started()
        except OSError as exc:
            raise _safe_provider_error(f"Realtime provider connection failed: {exc}") from exc
        return {
            "event": "session_started",
            "speaker_id": self.speaker_id,
            "resource_id": self.settings.volcengine_realtime_resource_id,
        }

    async def receive_client_event(self, event: dict[str, Any]) -> list[dict[str, Any]]:
        event_name = event.get("event")
        if self.websocket is None:
            raise RuntimeError("Realtime provider session has not started.")
        if event_name == "audio_chunk":
            audio = event.get("audio")
            if isinstance(audio, str) and audio:
                await self._send_provider_audio(audio)
        elif event_name == "end_asr":
            await self._send_provider_event(
                VOLCENGINE_EVENT_END_ASR,
                {},
                session_id=self.session_id,
            )
            events = await self._drain_provider_events(wait_for_response=True)
            if not events:
                return [
                    {
                        "event": "error",
                        "message": "Realtime provider did not return audio before timeout.",
                    }
                ]
            return events
        elif event_name == "interrupt":
            await self._send_provider_event(
                VOLCENGINE_EVENT_CLIENT_INTERRUPT,
                {},
                session_id=self.session_id,
            )
            return [{"event": "tts_ended"}]
        return await self._drain_provider_events()

    async def close(self) -> None:
        if self.websocket is not None:
            await self.websocket.close()
            self.websocket = None

    def _session_config(self) -> dict[str, Any]:
        model = self.settings.volcengine_realtime_model
        normalized_model = {"O": "1.2.1.1", "SC": "2.2.0.0"}.get(model.upper(), model)
        return {
            "tts": {
                "speaker": self.speaker_id,
                "extra": {},
            },
            "asr": {
                "audio_info": {
                    "format": "pcm_s16le",
                    "sample_rate": 16000,
                    "channel": 1,
                },
                "extra": {
                    "enable_asr_twopass": True,
                },
            },
            "dialog": {
                "bot_name": self.settings.volcengine_realtime_bot_name,
                "system_role": FACE_REALTIME_SYSTEM_ROLE,
                "speaking_style": self.settings.volcengine_realtime_speaking_style,
                "extra": {
                    "model": normalized_model,
                    "input_mod": "push_to_talk",
                },
            },
        }

    async def _send_provider_event(
        self,
        event_id: int,
        payload: dict[str, Any],
        *,
        session_id: str | None = None,
    ) -> None:
        if self.websocket is None:
            raise RuntimeError("Realtime provider session has not started.")
        encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        frame = _pack_volcengine_frame(
            event_id=event_id,
            payload=encoded,
            session_id=session_id,
        )
        try:
            await self.websocket.send(frame)
        except ConnectionClosed as exc:
            raise RuntimeError(
                "Realtime provider connection closed before accepting data."
            ) from exc

    async def _send_provider_audio(self, encoded_audio: str) -> None:
        if self.websocket is None:
            raise RuntimeError("Realtime provider session has not started.")
        try:
            audio = base64.b64decode(encoded_audio, validate=True)
        except ValueError as exc:
            raise RuntimeError("Browser audio chunk was not valid base64.") from exc
        frame = _pack_volcengine_frame(
            event_id=VOLCENGINE_EVENT_TASK_REQUEST,
            payload=audio,
            session_id=self.session_id,
            message_type=0x2,
            serialization=0x0,
        )
        try:
            await self.websocket.send(frame)
        except ConnectionClosed as exc:
            raise RuntimeError(
                "Realtime provider connection closed before accepting audio."
            ) from exc

    async def _wait_for_provider_session_started(self) -> None:
        if self.websocket is None:
            return
        while True:
            try:
                raw = await asyncio.wait_for(
                    self.websocket.recv(),
                    timeout=self.settings.volcengine_realtime_receive_timeout_seconds,
                )
            except TimeoutError:
                return
            except ConnectionClosed as exc:
                raise RuntimeError(
                    "Realtime provider connection closed before starting session."
                ) from exc
            if not isinstance(raw, bytes):
                continue
            try:
                frame = _parse_volcengine_frame(raw)
            except ValueError:
                continue
            event_id = frame["event_id"]
            logger.info(
                "Volcengine realtime provider startup event_id=%s message_type=%s payload_bytes=%s",
                event_id,
                frame["message_type"],
                len(frame["payload"]),
            )
            if event_id == VOLCENGINE_EVENT_SESSION_STARTED:
                return
            if event_id in {
                VOLCENGINE_EVENT_CONNECTION_FAILED,
                VOLCENGINE_EVENT_SESSION_FAILED,
                VOLCENGINE_EVENT_DIALOG_COMMON_ERROR,
            }:
                raise RuntimeError(self._provider_error_message(frame["payload"]))

    async def _drain_provider_events(
        self,
        *,
        wait_for_response: bool = False,
    ) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        if self.websocket is None:
            return events
        deadline = (
            time.monotonic() + self.settings.volcengine_realtime_response_timeout_seconds
            if wait_for_response
            else None
        )
        while True:
            try:
                raw = await asyncio.wait_for(
                    self.websocket.recv(),
                    timeout=self.settings.volcengine_realtime_receive_timeout_seconds,
                )
            except TimeoutError:
                if self._audio_chunks:
                    break
                if deadline is not None and time.monotonic() < deadline:
                    await asyncio.sleep(self.settings.volcengine_realtime_receive_timeout_seconds)
                    continue
                break
            except ConnectionClosed as exc:
                raise RuntimeError(
                    "Realtime provider connection closed while waiting for audio."
                ) from exc
            normalized = self._normalize_provider_event(raw)
            if normalized is not None:
                events.append(normalized)
                if normalized.get("event") in {"assistant_audio", "error", "tts_ended"}:
                    break
        buffered = self._flush_audio_chunks()
        if buffered is not None:
            events.append(buffered)
        if wait_for_response and not events:
            logger.warning(
                "Volcengine realtime provider returned no events before response timeout."
            )
        return events

    def _normalize_provider_event(self, raw: str | bytes | dict[str, Any]) -> dict[str, Any] | None:
        if isinstance(raw, bytes):
            try:
                frame = _parse_volcengine_frame(raw)
            except ValueError:
                self._audio_chunks.append(raw)
                self._audio_mime = "audio/ogg"
                return None
            event_id = frame["event_id"]
            payload = frame["payload"]
            if event_id != VOLCENGINE_EVENT_TTS_RESPONSE:
                logger.info(
                    "Volcengine realtime provider event_id=%s message_type=%s payload_bytes=%s",
                    event_id,
                    frame["message_type"],
                    len(payload),
                )
            if event_id == VOLCENGINE_EVENT_TTS_RESPONSE:
                self._audio_chunks.append(payload)
                self._audio_mime = "audio/ogg"
                return None
            if event_id == VOLCENGINE_EVENT_TTS_ENDED:
                return self._flush_audio_chunks()
            if event_id in {
                VOLCENGINE_EVENT_CONNECTION_FAILED,
                VOLCENGINE_EVENT_SESSION_FAILED,
                VOLCENGINE_EVENT_DIALOG_COMMON_ERROR,
            }:
                message = self._provider_error_message(payload)
                return {"event": "error", "message": str(_safe_provider_error(message))}
            return None
        if isinstance(raw, str):
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                return None
        else:
            payload = raw
        if not isinstance(payload, dict):
            return None
        event_name = str(payload.get("event") or payload.get("type") or "")
        if event_name in {"asr_partial", "asr_final", "assistant_text"}:
            return None
        if "transcript" in payload or event_name.endswith(".transcript.delta"):
            return None
        if event_name in {"response.audio.delta", "assistant_audio", "audio"}:
            audio = payload.get("audio") or payload.get("delta") or payload.get("data")
            if isinstance(audio, str) and audio:
                self._append_audio_chunk(
                    audio,
                    str(payload.get("mime") or payload.get("mime_type") or "audio/wav"),
                )
                if event_name in {"assistant_audio", "audio"}:
                    return self._flush_audio_chunks()
                return None
        if event_name in {"response.audio.done", "tts_ended"}:
            return self._flush_audio_chunks()
        if event_name == "error":
            message = str(payload.get("message") or "Realtime provider error.")
            return {"event": "error", "message": str(_safe_provider_error(message))}
        return None

    def _provider_error_message(self, payload: bytes) -> str:
        message = "Realtime provider error."
        try:
            body = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return message
        if isinstance(body, dict):
            return str(body.get("message") or body.get("error") or message)
        return message

    def _append_audio_chunk(self, encoded_audio: str, mime_type: str) -> None:
        try:
            chunk = base64.b64decode(encoded_audio, validate=True)
        except ValueError:
            chunk = encoded_audio.encode("utf-8")
        self._audio_chunks.append(chunk)
        self._audio_mime = mime_type

    def _flush_audio_chunks(self) -> dict[str, str] | None:
        if not self._audio_chunks:
            return None
        audio = base64.b64encode(b"".join(self._audio_chunks)).decode("ascii")
        mime = self._audio_mime
        self._audio_chunks = []
        self._audio_mime = "audio/wav"
        return {"event": "assistant_audio", "audio": audio, "mime": mime}


def create_realtime_bridge(speaker_id: str) -> VolcengineRealtimeBridge:
    return VolcengineRealtimeBridge(speaker_id)
