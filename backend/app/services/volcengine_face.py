from __future__ import annotations

from typing import Any
from uuid import uuid4

import httpx

from app.core.config import get_settings
from app.models.entities import FaceAsset


class VolcengineSetupError(RuntimeError):
    """Raised when a provider feature is requested without required env config."""


def _require_speech_key() -> str:
    api_key = get_settings().volcengine_speech_api_key
    if not api_key:
        raise VolcengineSetupError("VOLCENGINE_SPEECH_API_KEY is required.")
    return api_key


def _safe_provider_error(message: str) -> RuntimeError:
    return RuntimeError(message.replace(_require_speech_key(), "[redacted]"))


def clone_voice_from_asset(asset: FaceAsset, audio_url: str) -> dict[str, str]:
    settings = get_settings()
    api_key = _require_speech_key()
    speaker_id = f"researchmocker-{asset.id}-{uuid4().hex[:10]}"
    payload = {
        "speaker_id": speaker_id,
        "audio_url": audio_url,
        "resource_id": settings.volcengine_voice_clone_resource_id,
    }
    headers = {"X-Api-Key": api_key, "X-Api-Request-Id": uuid4().hex}
    try:
        response = httpx.post(
            "https://openspeech.bytedance.com/api/v3/mega_tts/voice_clone",
            json=payload,
            headers=headers,
            timeout=60,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise _safe_provider_error("Voice clone provider request failed.") from exc

    body = response.json()
    provider_speaker_id = (
        body.get("speaker_id")
        or body.get("data", {}).get("speaker_id")
        or body.get("SpeakerID")
        or speaker_id
    )
    return {"speaker_id": str(provider_speaker_id), "provider_status": "voice_ready"}


def generate_face_videos(asset: FaceAsset, image_url: str) -> dict[str, Any]:
    settings = get_settings()
    if not settings.volcengine_omnihuman_access_key_id:
        raise VolcengineSetupError(
            "VOLCENGINE_OMNIHUMAN_ACCESS_KEY_ID is required for video generation."
        )
    if not settings.volcengine_omnihuman_secret_access_key:
        raise VolcengineSetupError(
            "VOLCENGINE_OMNIHUMAN_SECRET_ACCESS_KEY is required for video generation."
        )

    # OmniHuman local docs describe async submit/query tasks. Keep this boundary narrow:
    # the production smoke path can replace this placeholder body with signed CVSubmitTask calls.
    task_id = f"omnihuman-{asset.id}-{uuid4().hex[:10]}"
    return {
        "provider_status": "video_pending",
        "jobs": [
            {"kind": "ready", "status": "pending", "provider_task_id": task_id, "video_url": None},
            {
                "kind": "listening",
                "status": "pending",
                "provider_task_id": f"{task_id}-listen",
                "video_url": None,
            },
        ],
        "image_url": image_url,
    }


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
