from datetime import datetime

from pydantic import BaseModel


class FaceAssetResponse(BaseModel):
    id: int
    status: str
    image_url: str
    audio_url: str
    speaker_id: str | None
    ready_video_url: str | None
    listening_video_url: str | None
    latest_speaking_video_url: str | None
    provider_status: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class FaceSessionCreate(BaseModel):
    asset_id: int


class FaceSessionResponse(BaseModel):
    id: int
    asset_id: int
    status: str
    created_at: datetime
