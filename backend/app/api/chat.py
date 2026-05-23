import json
import logging
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import desc, select
from sqlalchemy.orm import selectinload

from app.api.deps import DbSession, current_user
from app.models.entities import Conversation, Message, User
from app.schemas.chat import ChatRequest, ConversationDetail, ConversationList, ConversationSummary
from app.services.llm import stream_llm_response

router = APIRouter(tags=["chat"])
CurrentUser = Annotated[User, Depends(current_user)]
logger = logging.getLogger(__name__)


def _sse(event: str, data: dict[str, object]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, separators=(',', ':'))}\n\n"


def _title_from_message(message: str) -> str:
    normalized = " ".join(message.split())
    return normalized[:60] or "New conversation"


@router.post("/api/chat/stream")
def stream_chat(
    request: ChatRequest,
    db: DbSession,
    user: CurrentUser,
) -> StreamingResponse:
    conversation = None
    if request.conversation_id is not None:
        conversation = db.scalar(
            select(Conversation).where(
                Conversation.id == request.conversation_id,
                Conversation.user_id == user.id,
            )
        )
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found")

    if conversation is None:
        conversation = Conversation(user_id=user.id, title=_title_from_message(request.message))
        db.add(conversation)
        db.flush()

    now = datetime.now(UTC)
    conversation.updated_at = now
    db.add(Message(conversation_id=conversation.id, role="user", content=request.message))
    db.commit()
    conversation_id = conversation.id

    history = db.scalars(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc(), Message.id.asc())
    ).all()
    messages = [{"role": item.role, "content": item.content} for item in history]

    def generate() -> Iterator[str]:
        assistant_parts: list[str] = []
        yield _sse("meta", {"conversation_id": conversation_id})
        try:
            for text in stream_llm_response(messages):
                assistant_parts.append(text)
                yield _sse("delta", {"text": text})
        except Exception:
            logger.exception("LLM streaming failed")
            yield _sse("error", {"message": "The AI provider failed. Please try again."})
            return

        assistant_text = "".join(assistant_parts)
        if assistant_text:
            conversation_for_update = db.get(Conversation, conversation_id)
            if conversation_for_update is not None:
                conversation_for_update.updated_at = datetime.now(UTC)
            db.add(
                Message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=assistant_text,
                )
            )
            db.commit()
        yield _sse("done", {"conversation_id": conversation_id})

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/api/conversations", response_model=ConversationList)
def list_conversations(
    db: DbSession,
    user: CurrentUser,
) -> ConversationList:
    conversations = db.scalars(
        select(Conversation)
        .where(Conversation.user_id == user.id)
        .order_by(desc(Conversation.updated_at), desc(Conversation.id))
    ).all()
    return ConversationList(
        conversations=[
            ConversationSummary(
                id=item.id,
                title=item.title,
                created_at=item.created_at,
                updated_at=item.updated_at,
            )
            for item in conversations
        ]
    )


@router.get("/api/conversations/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    conversation_id: int,
    db: DbSession,
    user: CurrentUser,
) -> ConversationDetail:
    conversation = db.scalar(
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(Conversation.id == conversation_id, Conversation.user_id == user.id)
    )
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return ConversationDetail(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=[
            {
                "id": message.id,
                "role": message.role,
                "content": message.content,
                "created_at": message.created_at,
            }
            for message in conversation.messages
        ],
    )
