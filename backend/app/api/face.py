from __future__ import annotations

import base64
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, WebSocket, status
from fastapi.responses import FileResponse
from sqlalchemy import or_, select

from app.api.deps import DbSession, current_user
from app.core.config import get_settings
from app.models.entities import FaceAsset, FaceRealtimeSession, FaceVideoJob, User
from app.schemas.face import FaceAssetResponse, FaceSessionCreate, FaceSessionResponse
from app.services.volcengine_face import (
    VolcengineSetupError,
    clone_voice_from_asset,
    create_realtime_bridge,
    generate_face_videos,
    poll_face_video_job,
    submit_prepared_face_video_job,
    submit_speaking_face_video,
    wait_for_face_video_job,
)

router = APIRouter(prefix="/api/face", tags=["face"])
CurrentUser = Annotated[User, Depends(current_user)]
ImageFile = Annotated[UploadFile, File()]
AudioFile = Annotated[UploadFile, File()]

IMAGE_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}
AUDIO_MIME_TYPES = {
    "audio/aac",
    "audio/m4a",
    "audio/mp4",
    "audio/mpeg",
    "audio/ogg",
    "audio/wav",
    "audio/x-m4a",
}
MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_AUDIO_BYTES = 10 * 1024 * 1024


def _public_url(request: Request, token: str) -> str:
    return _public_media_url(token, request.url_for("get_face_media", token=token).path)


def _public_media_url(token: str, path: str | None = None) -> str:
    settings = get_settings()
    path = path or f"/api/face/media/{token}"
    if settings.public_base_url:
        return f"{settings.public_base_url.rstrip('/')}{path}"
    return path


def _asset_response(asset: FaceAsset, request: Request) -> FaceAssetResponse:
    return FaceAssetResponse(
        id=asset.id,
        status=asset.status,
        image_url=_public_url(request, asset.image_media_token),
        audio_url=_public_url(request, asset.audio_media_token),
        speaker_id=asset.speaker_id,
        ready_video_url=asset.ready_video_url,
        listening_video_url=asset.listening_video_url,
        latest_speaking_video_url=asset.latest_speaking_video_url,
        provider_status=asset.provider_status,
        error_message=asset.error_message,
        created_at=asset.created_at,
        updated_at=asset.updated_at,
    )


def _load_asset(asset_id: int, db: DbSession, user: User) -> FaceAsset:
    asset = db.scalar(
        select(FaceAsset).where(FaceAsset.id == asset_id, FaceAsset.user_id == user.id)
    )
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Face asset not found")
    return asset


async def _read_upload(
    upload: UploadFile,
    allowed_mime_types: set[str],
    max_bytes: int,
    label: str,
) -> bytes:
    mime_type = upload.content_type or "application/octet-stream"
    if mime_type not in allowed_mime_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported {label} upload type.",
        )
    content = await upload.read()
    if len(content) > max_bytes:
        limit_mb = max_bytes // (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{label.title()} exceeds the {limit_mb}MB limit.",
        )
    return content


def _stored_name(upload: UploadFile, fallback: str) -> str:
    suffix = Path(upload.filename or fallback).suffix.lower()
    return f"{uuid4().hex}{suffix}"


@router.post("/assets", response_model=FaceAssetResponse, status_code=status.HTTP_201_CREATED)
async def create_face_asset(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    image: ImageFile,
    audio: AudioFile,
) -> FaceAssetResponse:
    image_bytes = await _read_upload(image, IMAGE_MIME_TYPES, MAX_IMAGE_BYTES, "image")
    audio_bytes = await _read_upload(audio, AUDIO_MIME_TYPES, MAX_AUDIO_BYTES, "audio")

    user_dir = Path(get_settings().upload_dir) / "face" / str(user.id)
    user_dir.mkdir(parents=True, exist_ok=True)
    image_path = user_dir / _stored_name(image, "interviewer.png")
    audio_path = user_dir / _stored_name(audio, "reference.wav")
    image_path.write_bytes(image_bytes)
    audio_path.write_bytes(audio_bytes)

    now = datetime.now(UTC)
    asset = FaceAsset(
        user_id=user.id,
        status="uploaded",
        image_path=str(image_path),
        image_mime_type=image.content_type or "application/octet-stream",
        image_size_bytes=len(image_bytes),
        image_media_token=uuid4().hex,
        audio_path=str(audio_path),
        audio_mime_type=audio.content_type or "application/octet-stream",
        audio_size_bytes=len(audio_bytes),
        audio_media_token=uuid4().hex,
        provider_status="uploaded",
        created_at=now,
        updated_at=now,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return _asset_response(asset, request)


@router.get("/assets/{asset_id}", response_model=FaceAssetResponse)
def get_face_asset(
    asset_id: int,
    request: Request,
    db: DbSession,
    user: CurrentUser,
) -> FaceAssetResponse:
    return _asset_response(_load_asset(asset_id, db, user), request)


@router.post("/assets/{asset_id}/voice-clone", response_model=FaceAssetResponse)
def prepare_voice_clone(
    asset_id: int,
    request: Request,
    db: DbSession,
    user: CurrentUser,
) -> FaceAssetResponse:
    asset = _load_asset(asset_id, db, user)
    try:
        result = clone_voice_from_asset(asset, _public_url(request, asset.audio_media_token))
    except VolcengineSetupError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        asset.status = "voice_error"
        asset.error_message = str(exc)
        asset.provider_status = "voice_error"
        asset.updated_at = datetime.now(UTC)
        db.commit()
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    asset.speaker_id = result["speaker_id"]
    asset.status = "voice_ready"
    asset.provider_status = result.get("provider_status", "voice_ready")
    asset.error_message = None
    asset.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(asset)
    return _asset_response(asset, request)


@router.post("/assets/{asset_id}/videos", response_model=FaceAssetResponse)
def prepare_face_videos(
    asset_id: int,
    request: Request,
    db: DbSession,
    user: CurrentUser,
) -> FaceAssetResponse:
    asset = _load_asset(asset_id, db, user)
    try:
        result = generate_face_videos(
            asset,
            _public_url(request, asset.image_media_token),
            lambda token: _public_url(request, token),
        )
    except VolcengineSetupError as exc:
        asset.status = "video_error"
        asset.error_message = str(exc)
        asset.provider_status = "video_error"
        asset.updated_at = datetime.now(UTC)
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        asset.status = "video_error"
        asset.error_message = str(exc)
        asset.provider_status = "video_error"
        asset.updated_at = datetime.now(UTC)
        db.commit()
        status_code = (
            status.HTTP_400_BAD_REQUEST
            if str(exc).startswith("VOLCENGINE_OMNIHUMAN_")
            else status.HTTP_502_BAD_GATEWAY
        )
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc

    for job in result.get("jobs", []):
        db.add(
            FaceVideoJob(
                asset_id=asset.id,
                kind=job["kind"],
                status=job["status"],
                provider_task_id=job.get("provider_task_id"),
                provider_request_id=job.get("provider_request_id"),
                audio_path=job.get("audio_path"),
                audio_media_token=job.get("audio_media_token"),
                video_url=job.get("video_url"),
            )
        )
    asset.status = "video_pending"
    asset.provider_status = result.get("provider_status", "video_pending")
    asset.error_message = None
    asset.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(asset)
    return _asset_response(asset, request)


@router.post("/assets/{asset_id}/videos/poll", response_model=FaceAssetResponse)
def poll_face_videos(
    asset_id: int,
    request: Request,
    db: DbSession,
    user: CurrentUser,
) -> FaceAssetResponse:
    asset = _load_asset(asset_id, db, user)
    pending_jobs = [
        job
        for job in asset.video_jobs
        if job.kind in {"ready", "listening"} and job.status == "pending"
    ]
    now = datetime.now(UTC)
    for job in pending_jobs:
        try:
            result = poll_face_video_job(job)
        except RuntimeError as exc:
            job.status = "error"
            job.error_message = str(exc)
            asset.status = "video_error"
            asset.provider_status = "video_error"
            asset.error_message = str(exc)
            job.updated_at = now
            asset.updated_at = now
            db.commit()
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
        job.provider_request_id = result.get("provider_request_id") or job.provider_request_id
        if result["status"] == "done":
            job.status = "done"
            job.video_url = result.get("video_url")
            if job.kind == "ready":
                asset.ready_video_url = job.video_url
            if job.kind == "listening":
                asset.listening_video_url = job.video_url
        job.updated_at = now

    active_provider_job = any(
        job.kind in {"ready", "listening"} and job.status == "pending"
        for job in asset.video_jobs
    )
    queued_jobs = [
        job
        for job in asset.video_jobs
        if job.kind in {"ready", "listening"} and job.status == "queued"
    ]
    if not active_provider_job and queued_jobs:
        queued_jobs.sort(key=lambda job: 0 if job.kind == "ready" else 1)
        job = queued_jobs[0]
        if not job.audio_media_token:
            message = "Queued face video job does not have a generated audio token."
            job.status = "error"
            job.error_message = message
            asset.status = "video_error"
            asset.provider_status = "video_error"
            asset.error_message = message
            job.updated_at = now
            asset.updated_at = now
            db.commit()
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=message)
        try:
            result = submit_prepared_face_video_job(
                job,
                _public_url(request, asset.image_media_token),
                _public_url(request, job.audio_media_token),
            )
        except RuntimeError as exc:
            job.status = "error"
            job.error_message = str(exc)
            asset.status = "video_error"
            asset.provider_status = "video_error"
            asset.error_message = str(exc)
            job.updated_at = now
            asset.updated_at = now
            db.commit()
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
        job.status = result.get("status", "pending")
        job.provider_task_id = result.get("provider_task_id")
        job.provider_request_id = result.get("provider_request_id")
        job.updated_at = now

    ready_done = any(job.kind == "ready" and job.status == "done" for job in asset.video_jobs)
    listening_done = any(
        job.kind == "listening" and job.status == "done" for job in asset.video_jobs
    )
    if ready_done and listening_done:
        asset.status = "video_ready"
        asset.provider_status = "video_ready"
        asset.error_message = None
    elif any(
        job.status == "error" for job in asset.video_jobs if job.kind in {"ready", "listening"}
    ):
        asset.status = "video_error"
        asset.provider_status = "video_error"
    else:
        asset.status = "video_pending"
        asset.provider_status = "video_pending"
    asset.updated_at = now
    db.commit()
    db.refresh(asset)
    return _asset_response(asset, request)


@router.post("/session", response_model=FaceSessionResponse, status_code=status.HTTP_201_CREATED)
def create_face_session(
    request: FaceSessionCreate,
    db: DbSession,
    user: CurrentUser,
) -> FaceSessionResponse:
    asset = _load_asset(request.asset_id, db, user)
    if not asset.speaker_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Voice clone must be prepared before starting a face session.",
        )
    now = datetime.now(UTC)
    session = FaceRealtimeSession(
        asset_id=asset.id,
        user_id=user.id,
        status="created",
        created_at=now,
        updated_at=now,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return FaceSessionResponse(
        id=session.id,
        asset_id=session.asset_id,
        status=session.status,
        created_at=session.created_at,
    )


@router.get("/media/{token}", name="get_face_media")
def get_face_media(token: str, db: DbSession) -> FileResponse:
    asset = db.scalar(
        select(FaceAsset).where(
            or_(FaceAsset.image_media_token == token, FaceAsset.audio_media_token == token)
        )
    )
    if asset is not None:
        if token == asset.image_media_token:
            return FileResponse(asset.image_path, media_type=asset.image_mime_type)
        return FileResponse(asset.audio_path, media_type=asset.audio_mime_type)

    generated = db.scalar(select(FaceVideoJob).where(FaceVideoJob.audio_media_token == token))
    if generated is None or not generated.audio_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media not found")
    generated_path = Path(generated.audio_path)
    upload_root = Path(get_settings().upload_dir).resolve()
    try:
        generated_path.resolve().relative_to(upload_root)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media not found",
        ) from None
    return FileResponse(str(generated_path), media_type="audio/wav")


def _store_speaking_audio(asset: FaceAsset, encoded_audio: str, mime_type: str) -> tuple[str, str]:
    try:
        audio_bytes = base64.b64decode(encoded_audio, validate=True)
    except ValueError as exc:
        raise RuntimeError("Assistant audio from realtime provider was not valid base64.") from exc
    suffix = ".wav"
    if "mpeg" in mime_type or "mp3" in mime_type:
        suffix = ".mp3"
    elif "ogg" in mime_type:
        suffix = ".ogg"
    generated_dir = Path(get_settings().upload_dir) / "face-generated" / str(asset.user_id)
    generated_dir.mkdir(parents=True, exist_ok=True)
    audio_path = generated_dir / f"{uuid4().hex}-speaking{suffix}"
    audio_path.write_bytes(audio_bytes)
    return str(audio_path), uuid4().hex


async def _handle_assistant_audio(
    websocket: WebSocket,
    db,
    asset: FaceAsset,
    provider_event: dict,
) -> None:
    audio = provider_event.get("audio")
    if not isinstance(audio, str):
        await websocket.send_json({"event": "error", "message": "Assistant audio was missing."})
        return
    mime_type = str(provider_event.get("mime") or "audio/wav")
    try:
        audio_path, audio_token = _store_speaking_audio(asset, audio, mime_type)
        job = FaceVideoJob(
            asset_id=asset.id,
            kind="speaking",
            status="pending",
            audio_path=audio_path,
            audio_media_token=audio_token,
        )
        result = submit_speaking_face_video(
            asset,
            _public_media_url(asset.image_media_token),
            _public_media_url(audio_token),
        )
        job.status = result.get("status", "pending")
        job.provider_task_id = result.get("provider_task_id")
        job.provider_request_id = result.get("provider_request_id")
        db.add(job)
        db.commit()
        db.refresh(job)
        await websocket.send_json({"event": "speaking_video_pending"})
        wait_result = wait_for_face_video_job(job)
        job.status = "done"
        job.video_url = wait_result.get("video_url")
        job.provider_request_id = wait_result.get("provider_request_id") or job.provider_request_id
        job.updated_at = datetime.now(UTC)
        asset.latest_speaking_video_url = job.video_url
        asset.updated_at = job.updated_at
        db.commit()
        await websocket.send_json({"event": "speaking_video_ready", "video_url": job.video_url})
    except (RuntimeError, TimeoutError) as exc:
        if "job" in locals():
            job.status = "error"
            job.error_message = str(exc)
            job.updated_at = datetime.now(UTC)
            db.commit()
        await websocket.send_json({"event": "error", "message": str(exc)})
        await websocket.send_json(provider_event)


@router.websocket("/session/{session_id}/stream")
async def stream_face_session(websocket: WebSocket, session_id: int) -> None:
    await websocket.accept()
    session_token = websocket.cookies.get("session_token")
    if not session_token:
        await websocket.send_json({"event": "error", "message": "Not authenticated"})
        await websocket.close(code=1008)
        return

    from app.api.deps import hash_token
    from app.core.database import SessionLocal
    from app.models.entities import SessionToken

    db = SessionLocal()
    try:
        token_hash = hash_token(session_token)
        auth_record = db.scalar(select(SessionToken).where(SessionToken.token_hash == token_hash))
        session = db.scalar(select(FaceRealtimeSession).where(FaceRealtimeSession.id == session_id))
        if auth_record is None or session is None or session.user_id != auth_record.user_id:
            await websocket.send_json({"event": "error", "message": "Not authenticated"})
            await websocket.close(code=1008)
            return
        asset = db.scalar(select(FaceAsset).where(FaceAsset.id == session.asset_id))
        if asset is None or not asset.speaker_id:
            await websocket.send_json({"event": "error", "message": "Face session is not ready"})
            await websocket.close(code=1011)
            return
        bridge = create_realtime_bridge(asset.speaker_id)
        while True:
            event = await websocket.receive_json()
            event_name = event.get("event")
            if event_name == "start_session":
                started = await bridge.start()
                session.status = "streaming"
                session.updated_at = datetime.now(UTC)
                db.commit()
                await websocket.send_json(started)
            elif event_name == "finish_session":
                session.status = "finished"
                session.finished_at = datetime.now(UTC)
                session.updated_at = session.finished_at
                db.commit()
                await websocket.send_json({"event": "session_finished"})
                await websocket.close()
                return
            else:
                for provider_event in await bridge.receive_client_event(event):
                    if provider_event.get("event") == "assistant_audio":
                        await _handle_assistant_audio(websocket, db, asset, provider_event)
                    else:
                        await websocket.send_json(provider_event)
    finally:
        db.close()
