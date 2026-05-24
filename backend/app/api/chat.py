import base64
import json
import logging
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import desc, select
from sqlalchemy.orm import selectinload

from app.api.deps import DbSession, current_user
from app.core.config import get_settings
from app.models.entities import Attachment, Conversation, Message, MessageAttachment, User
from app.schemas.chat import ChatRequest, ConversationDetail, ConversationList, ConversationSummary
from app.services.llm import stream_llm_response
from app.services.openrouter import (
    decrypt_api_key,
    enabled_model_ids,
    get_credential,
    to_litellm_model_id,
)

router = APIRouter(tags=["chat"])
CurrentUser = Annotated[User, Depends(current_user)]
logger = logging.getLogger(__name__)


def _sse(event: str, data: dict[str, object]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, separators=(',', ':'))}\n\n"


def _title_from_message(message: str) -> str:
    normalized = " ".join(message.split())
    return normalized[:60] or "New conversation"


def _message_attachments(message: Message) -> list[dict[str, object]]:
    return [
        {
            "id": link.attachment.id,
            "name": link.attachment.original_name,
            "mime": link.attachment.mime_type,
            "size": link.attachment.size_bytes,
            "kind": link.attachment.kind,
        }
        for link in message.attachments
    ]


def _attachment_context(message: str, attachments: list[Attachment]) -> str:
    text_parts = [message]
    for attachment in attachments:
        if attachment.kind != "text":
            continue
        text = Path(attachment.stored_path).read_text(encoding="utf-8")
        text_parts.append(f"\n\n[Attachment: {attachment.original_name}]\n{text}")
    return "".join(text_parts)


def _user_content_for_llm(message: str, attachments: list[Attachment]) -> object:
    images = [item for item in attachments if item.kind == "image"]
    text = _attachment_context(message, attachments)
    if not images:
        return text

    content: list[dict[str, object]] = [{"type": "text", "text": text}]
    for image in images:
        encoded = base64.b64encode(Path(image.stored_path).read_bytes()).decode("ascii")
        content.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:{image.mime_type};base64,{encoded}"},
            }
        )
    return content


def _resolve_openrouter_request(
    request: ChatRequest,
    db: DbSession,
    user: User,
) -> tuple[str, str]:
    credential = get_credential(db, user.id)
    if credential is None:
        raise HTTPException(
            status_code=400,
            detail="OpenRouter API key is required before chatting.",
        )

    enabled_ids = enabled_model_ids(db, user.id)
    if not enabled_ids:
        raise HTTPException(status_code=400, detail="Enable at least one model before chatting.")

    model_id = request.model_id or credential.selected_model_id
    if not model_id:
        raise HTTPException(status_code=400, detail="Select a model before chatting.")
    if model_id not in enabled_ids:
        raise HTTPException(status_code=400, detail=f"Model '{model_id}' is not enabled.")

    return to_litellm_model_id(model_id), decrypt_api_key(credential)


def _load_attachments(request: ChatRequest, db: DbSession, user: User) -> list[Attachment]:
    settings = get_settings()
    if len(request.attachment_ids) > settings.max_attachments_per_message:
        raise HTTPException(
            status_code=400,
            detail=f"Attach up to {settings.max_attachments_per_message} files per message.",
        )
    if not request.attachment_ids:
        return []

    attachments = db.scalars(
        select(Attachment).where(
            Attachment.user_id == user.id,
            Attachment.id.in_(request.attachment_ids),
        )
    ).all()
    if len(attachments) != len(set(request.attachment_ids)):
        raise HTTPException(status_code=404, detail="Attachment not found")
    attachment_by_id = {item.id: item for item in attachments}
    return [attachment_by_id[item_id] for item_id in request.attachment_ids]


@router.post("/api/chat/stream")
def stream_chat(
    request: ChatRequest,
    db: DbSession,
    user: CurrentUser,
) -> StreamingResponse:
    litellm_model_id, api_key = _resolve_openrouter_request(request, db, user)
    attachments = _load_attachments(request, db, user)

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
    user_message = Message(conversation_id=conversation.id, role="user", content=request.message)
    db.add(user_message)
    db.flush()
    for attachment in attachments:
        db.add(MessageAttachment(message_id=user_message.id, attachment_id=attachment.id))
    db.commit()
    conversation_id = conversation.id

    history = db.scalars(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc(), Message.id.asc())
    ).all()
    messages = [{"role": item.role, "content": item.content} for item in history]
    messages[-1]["content"] = _user_content_for_llm(request.message, attachments)

    def generate() -> Iterator[str]:
        assistant_parts: list[str] = []
        yield _sse("meta", {"conversation_id": conversation_id, "model_id": litellm_model_id})
        try:
            for text in stream_llm_response(messages, model=litellm_model_id, api_key=api_key):
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
        .options(
            selectinload(Conversation.messages)
            .selectinload(Message.attachments)
            .selectinload(MessageAttachment.attachment)
        )
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
                "attachments": _message_attachments(message),
            }
            for message in conversation.messages
        ],
    )
