import json
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.orm import selectinload

from app.api.deps import DbSession, current_user
from app.models.entities import InterviewSession, InterviewTurn, User
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


def _load_interview(interview_id: int, db: DbSession, user: User) -> InterviewSession:
    interview = db.scalar(
        select(InterviewSession)
        .options(selectinload(InterviewSession.turns))
        .where(InterviewSession.id == interview_id, InterviewSession.user_id == user.id)
    )
    if interview is None:
        raise HTTPException(status_code=404, detail="Interview not found")
    return interview


@router.post("/api/interviews", response_model=InterviewDetail)
def create_interview(
    request: InterviewCreate,
    db: DbSession,
    user: CurrentUser,
) -> InterviewDetail:
    profile = _profile_from_request(request)
    first = generate_first_question(profile)
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
    previous_turns = [
        {
            "question": turn.question,
            "answer": turn.answer,
            "feedback": _loads_object(turn.feedback_json),
        }
        for turn in interview.turns
        if turn.answer is not None
    ]
    result = evaluate_answer_and_follow_up(
        profile=profile,
        question=active_turn.question,
        answer=request.answer,
        previous_turns=previous_turns,
    )
    now = datetime.now(UTC)
    active_turn.answer = request.answer
    active_turn.feedback_json = json.dumps(result["feedback"], ensure_ascii=False)
    active_turn.model_used = result.get("model_used")
    active_turn.answered_at = now
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
    answered_turns = [
        {
            "question": turn.question,
            "answer": turn.answer,
            "feedback": _loads_object(turn.feedback_json),
        }
        for turn in interview.turns
        if turn.answer is not None
    ]
    result = generate_final_report(profile=profile, turns=answered_turns)
    now = datetime.now(UTC)
    interview.status = "finished"
    interview.final_report_json = json.dumps(result["report"], ensure_ascii=False)
    interview.updated_at = now
    interview.finished_at = now
    db.commit()
    return _detail(_load_interview(interview.id, db, user))
