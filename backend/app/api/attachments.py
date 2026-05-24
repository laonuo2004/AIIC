from pathlib import Path
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select

from app.api.deps import DbSession, current_user
from app.core.config import get_settings
from app.models.entities import Attachment, User
from app.schemas.attachments import AttachmentResponse, AttachmentUploadResponse

router = APIRouter(prefix="/api/attachments", tags=["attachments"])
CurrentUser = Annotated[User, Depends(current_user)]
UploadFiles = Annotated[list[UploadFile], File()]

TEXT_EXTENSIONS = {".txt", ".md", ".json", ".csv", ".log"}
IMAGE_MIME_TYPES = {"image/png", "image/jpeg", "image/webp", "image/gif"}


def _attachment_response(attachment: Attachment) -> AttachmentResponse:
    return AttachmentResponse(
        id=attachment.id,
        name=attachment.original_name,
        mime=attachment.mime_type,
        size=attachment.size_bytes,
        kind=attachment.kind,
        created_at=attachment.created_at,
    )


def _kind_for_upload(filename: str, mime_type: str) -> str | None:
    if Path(filename).suffix.lower() in TEXT_EXTENSIONS:
        return "text"
    if mime_type in IMAGE_MIME_TYPES:
        return "image"
    return None


@router.post("", response_model=AttachmentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_attachments(
    db: DbSession,
    user: CurrentUser,
    files: UploadFiles,
) -> AttachmentUploadResponse:
    settings = get_settings()
    if len(files) > settings.max_attachments_per_message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Upload up to {settings.max_attachments_per_message} attachments at once.",
        )

    saved: list[Attachment] = []
    user_dir = Path(settings.upload_dir) / str(user.id)
    user_dir.mkdir(parents=True, exist_ok=True)

    for upload in files:
        filename = Path(upload.filename or "attachment").name
        mime_type = upload.content_type or "application/octet-stream"
        kind = _kind_for_upload(filename, mime_type)
        if kind is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported attachment type.",
            )

        content = await upload.read()
        if len(content) > settings.max_upload_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Attachment exceeds the 5MB limit.",
            )

        if kind == "text":
            try:
                content.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Text attachments must be UTF-8 encoded.",
                ) from exc

        stored_path = user_dir / f"{uuid4().hex}{Path(filename).suffix.lower()}"
        stored_path.write_bytes(content)
        record = Attachment(
            user_id=user.id,
            original_name=filename,
            stored_path=str(stored_path),
            mime_type=mime_type,
            size_bytes=len(content),
            kind=kind,
        )
        db.add(record)
        saved.append(record)

    db.commit()
    for item in saved:
        db.refresh(item)

    return AttachmentUploadResponse(attachments=[_attachment_response(item) for item in saved])


@router.get("/{attachment_id}")
def get_attachment(
    attachment_id: int,
    db: DbSession,
    user: CurrentUser,
) -> FileResponse:
    attachment = db.scalar(
        select(Attachment).where(Attachment.id == attachment_id, Attachment.user_id == user.id)
    )
    if attachment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")
    return FileResponse(
        attachment.stored_path,
        media_type=attachment.mime_type,
        filename=attachment.original_name,
    )
