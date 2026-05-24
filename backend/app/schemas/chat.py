from datetime import datetime

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    conversation_id: int | None = None
    model_id: str | None = Field(default=None, max_length=255)
    attachment_ids: list[int] = Field(default_factory=list, max_length=4)


class MessageAttachmentResponse(BaseModel):
    id: int
    name: str
    mime: str
    size: int
    kind: str


class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime
    attachments: list[MessageAttachmentResponse] = Field(default_factory=list)


class ConversationSummary(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime


class ConversationList(BaseModel):
    conversations: list[ConversationSummary]


class ConversationDetail(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime
    messages: list[MessageResponse]
