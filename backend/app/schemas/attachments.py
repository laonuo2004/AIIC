from datetime import datetime

from pydantic import BaseModel


class AttachmentResponse(BaseModel):
    id: int
    name: str
    mime: str
    size: int
    kind: str
    created_at: datetime


class AttachmentUploadResponse(BaseModel):
    attachments: list[AttachmentResponse]
