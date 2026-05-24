from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.attachments import AttachmentResponse


class InterviewCreate(BaseModel):
    self_introduction: str = Field(min_length=1, max_length=4000)
    project_experience: str = Field(min_length=1, max_length=8000)
    target_direction: str = Field(min_length=1, max_length=255)
    weak_points: str = Field(default="", max_length=2000)
    interview_type: Literal["text"] = "text"
    attachment_ids: list[int] = Field(default_factory=list, max_length=4)


class InterviewAnswerCreate(BaseModel):
    answer: str = Field(min_length=1, max_length=8000)


class InterviewTurnOut(BaseModel):
    id: int
    turn_index: int
    question: str
    answer: str | None
    feedback: dict[str, Any] | None
    model_used: str | None
    created_at: datetime
    answered_at: datetime | None


class InterviewDetail(BaseModel):
    id: int
    title: str
    status: str
    profile: dict[str, Any]
    target_direction: str
    interview_type: str
    weak_points: str
    current_question: str | None
    final_report: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime
    finished_at: datetime | None
    turns: list[InterviewTurnOut]
    attachments: list[AttachmentResponse] = Field(default_factory=list)


class InterviewSummary(BaseModel):
    id: int
    title: str
    status: str
    target_direction: str
    current_question: str | None
    created_at: datetime
    updated_at: datetime
    finished_at: datetime | None


class InterviewList(BaseModel):
    interviews: list[InterviewSummary]
