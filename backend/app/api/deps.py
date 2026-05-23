from datetime import UTC, datetime
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import hash_token
from app.models.entities import SessionToken, User

DbSession = Annotated[Session, Depends(get_db)]
SessionCookie = Annotated[str | None, Cookie()]


def current_user(
    db: DbSession,
    session_token: SessionCookie = None,
) -> User:
    if not session_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    token_hash = hash_token(session_token)
    record = db.scalar(select(SessionToken).where(SessionToken.token_hash == token_hash))
    if not record or record.expires_at.replace(tzinfo=UTC) < datetime.now(UTC):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    return record.user
