import json
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.orm import selectinload

from app.api.deps import DbSession, current_user
from app.models.entities import (
    Attachment,
    InterviewAttachment,
    InterviewSession,
    InterviewTurn,
    User,
)
from app.schemas.attachments import AttachmentResponse
from app.schemas.interviews import (
    InterviewAnswerCreate,
    InterviewCreate,
    InterviewDetail,
    InterviewList,
    InterviewSummary,
    InterviewTurnOut,
)
from app.services.interviews import (
    evaluate_answer_and_follow_up,
    generate_final_report,
    generate_first_question,
)

router = APIRouter(tags=["interviews"])
CurrentUser = Annotated[User, Depends(current_user)]
MAX_INTERVIEW_TURNS = 5


def _profile_from_request(request: InterviewCreate) -> dict[str, str]:
    return {
        "self_introduction": request.self_introduction,
        "project_experience": request.project_experience,
        "target_direction": request.target_direction,
        "weak_points": request.weak_points,
    }


def _loads_object(value: str | None) -> dict[str, Any] | None:
    if not value:
        return None
    loaded = json.loads(value)
    return loaded if isinstance(loaded, dict) else {"value": loaded}


def _turn_out(turn: InterviewTurn) -> InterviewTurnOut:
    return InterviewTurnOut(
        id=turn.id,
        turn_index=turn.turn_index,
        question=turn.question,
        answer=turn.answer,
        feedback=_loads_object(turn.feedback_json),
        model_used=turn.model_used,
        created_at=turn.created_at,
        answered_at=turn.answered_at,
    )


def _attachment_response(attachment: Attachment) -> AttachmentResponse:
    return AttachmentResponse(
        id=attachment.id,
        name=attachment.original_name,
        mime=attachment.mime_type,
        size=attachment.size_bytes,
        kind=attachment.kind,
        created_at=attachment.created_at,
    )


def _interview_attachments(interview: InterviewSession) -> list[Attachment]:
    return [link.attachment for link in interview.attachments]


def _current_question(interview: InterviewSession) -> str | None:
    if interview.status == "finished":
        return None
    for turn in interview.turns:
        if turn.answer is None:
            return turn.question
    return None


def _detail(interview: InterviewSession) -> InterviewDetail:
    return InterviewDetail(
        id=interview.id,
        title=interview.title,
        status=interview.status,
        profile=_loads_object(interview.profile_json) or {},
        target_direction=interview.target_direction,
        interview_type=interview.interview_type,
        weak_points=interview.weak_points,
        current_question=_current_question(interview),
        final_report=_loads_object(interview.final_report_json),
        created_at=interview.created_at,
        updated_at=interview.updated_at,
        finished_at=interview.finished_at,
        turns=[_turn_out(turn) for turn in interview.turns],
        attachments=[_attachment_response(item) for item in _interview_attachments(interview)],
    )


def _summary(interview: InterviewSession) -> InterviewSummary:
    return InterviewSummary(
        id=interview.id,
        title=interview.title,
        status=interview.status,
        target_direction=interview.target_direction,
        current_question=_current_question(interview),
        created_at=interview.created_at,
        updated_at=interview.updated_at,
        finished_at=interview.finished_at,
    )


def _answered_turn_payloads(interview: InterviewSession) -> list[dict[str, Any]]:
    return [
        {
            "question": turn.question,
            "answer": turn.answer,
            "feedback": _loads_object(turn.feedback_json),
        }
        for turn in interview.turns
        if turn.answer is not None
    ]


def _finish_interview(
    interview: InterviewSession,
    *,
    profile: dict[str, Any],
    attachments: list[Attachment],
    now: datetime,
) -> None:
    answered_turns = _answered_turn_payloads(interview)
    result = generate_final_report(profile=profile, turns=answered_turns, attachments=attachments)
    interview.status = "finished"
    interview.final_report_json = json.dumps(result["report"], ensure_ascii=False)
    interview.updated_at = now
    interview.finished_at = now


def _load_interview(interview_id: int, db: DbSession, user: User) -> InterviewSession:
    interview = db.scalar(
        select(InterviewSession)
        .options(
            selectinload(InterviewSession.turns),
            selectinload(InterviewSession.attachments).selectinload(InterviewAttachment.attachment),
        )
        .where(InterviewSession.id == interview_id, InterviewSession.user_id == user.id)
    )
    if interview is None:
        raise HTTPException(status_code=404, detail="Interview not found")
    return interview


def _load_owned_attachments(ids: list[int], db: DbSession, user: User) -> list[Attachment]:
    if not ids:
        return []
    unique_ids = list(dict.fromkeys(ids))
    attachments = db.scalars(
        select(Attachment).where(Attachment.user_id == user.id, Attachment.id.in_(unique_ids))
    ).all()
    if len(attachments) != len(unique_ids):
        raise HTTPException(status_code=404, detail="Attachment not found")
    by_id = {item.id: item for item in attachments}
    return [by_id[item_id] for item_id in unique_ids]


@router.post("/api/interviews", response_model=InterviewDetail)
def create_interview(
    request: InterviewCreate,
    db: DbSession,
    user: CurrentUser,
) -> InterviewDetail:
    profile = _profile_from_request(request)
    attachments = _load_owned_attachments(request.attachment_ids, db, user)
    first = generate_first_question(profile, attachments)
    title = request.target_direction[:150] or "Research mock interview"
    now = datetime.now(UTC)
    interview = InterviewSession(
        user_id=user.id,
        title=title,
        status="active",
        profile_json=json.dumps(profile, ensure_ascii=False),
        target_direction=request.target_direction,
        interview_type=request.interview_type,
        weak_points=request.weak_points,
        created_at=now,
        updated_at=now,
    )
    db.add(interview)
    db.flush()
    for attachment in attachments:
        db.add(InterviewAttachment(interview_id=interview.id, attachment_id=attachment.id))
    db.add(
        InterviewTurn(
            interview_id=interview.id,
            turn_index=1,
            question=first["question"],
            model_used=first.get("model_used"),
            created_at=now,
        )
    )
    db.commit()
    db.refresh(interview)
    return _detail(_load_interview(interview.id, db, user))


@router.get("/api/interviews", response_model=InterviewList)
def list_interviews(db: DbSession, user: CurrentUser) -> InterviewList:
    interviews = db.scalars(
        select(InterviewSession)
        .options(selectinload(InterviewSession.turns))
        .where(InterviewSession.user_id == user.id)
        .order_by(desc(InterviewSession.updated_at), desc(InterviewSession.id))
    ).all()
    return InterviewList(interviews=[_summary(item) for item in interviews])


@router.get("/api/interviews/{interview_id}", response_model=InterviewDetail)
def get_interview(interview_id: int, db: DbSession, user: CurrentUser) -> InterviewDetail:
    return _detail(_load_interview(interview_id, db, user))


@router.post("/api/interviews/{interview_id}/answers", response_model=InterviewDetail)
def submit_answer(
    interview_id: int,
    request: InterviewAnswerCreate,
    db: DbSession,
    user: CurrentUser,
) -> InterviewDetail:
    interview = _load_interview(interview_id, db, user)
    if interview.status == "finished":
        raise HTTPException(status_code=400, detail="Interview is already finished")

    active_turn = next((turn for turn in interview.turns if turn.answer is None), None)
    if active_turn is None:
        raise HTTPException(status_code=400, detail="No active interview question")

    profile = _loads_object(interview.profile_json) or {}
    attachments = _interview_attachments(interview)
    previous_turns = _answered_turn_payloads(interview)
    result = evaluate_answer_and_follow_up(
        profile=profile,
        question=active_turn.question,
        answer=request.answer,
        previous_turns=previous_turns,
        attachments=attachments,
    )
    now = datetime.now(UTC)
    active_turn.answer = request.answer
    active_turn.feedback_json = json.dumps(result["feedback"], ensure_ascii=False)
    active_turn.model_used = result.get("model_used")
    active_turn.answered_at = now

    answered_count = len(previous_turns) + 1
    if answered_count >= MAX_INTERVIEW_TURNS:
        _finish_interview(interview, profile=profile, attachments=attachments, now=now)
    else:
        db.add(
            InterviewTurn(
                interview_id=interview.id,
                turn_index=len(interview.turns) + 1,
                question=result["follow_up_question"],
                model_used=result.get("model_used"),
                created_at=now,
            )
        )
        interview.updated_at = now
    db.commit()
    return _detail(_load_interview(interview.id, db, user))


@router.post("/api/interviews/{interview_id}/finish", response_model=InterviewDetail)
def finish_interview(interview_id: int, db: DbSession, user: CurrentUser) -> InterviewDetail:
    interview = _load_interview(interview_id, db, user)
    if interview.status == "finished":
        return _detail(interview)

    profile = _loads_object(interview.profile_json) or {}
    attachments = _interview_attachments(interview)
    now = datetime.now(UTC)
    _finish_interview(interview, profile=profile, attachments=attachments, now=now)
    db.commit()
    return _detail(_load_interview(interview.id, db, user))
