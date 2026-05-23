from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import delete, select

from app.api.deps import DbSession, SessionCookie, current_user
from app.core.security import (
    hash_password,
    hash_token,
    new_session_token,
    session_expiry,
    verify_password,
)
from app.models.entities import SessionToken, User
from app.schemas.auth import Credentials, UserResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])
COOKIE_NAME = "session_token"
CurrentUser = Annotated[User, Depends(current_user)]


def _user_response(user: User) -> UserResponse:
    return UserResponse(id=user.id, username=user.username)


def _set_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        COOKIE_NAME,
        token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=60 * 60 * 24,
        path="/",
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(credentials: Credentials, db: DbSession) -> UserResponse:
    if len(credentials.password) < 8:
        raise HTTPException(status_code=422, detail="Password must be at least 8 characters")
    existing = db.scalar(select(User).where(User.username == credentials.username))
    if existing:
        raise HTTPException(status_code=409, detail="Username already exists")

    user = User(username=credentials.username, password_hash=hash_password(credentials.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return _user_response(user)


@router.post("/login", response_model=UserResponse)
def login(
    credentials: Credentials,
    response: Response,
    db: DbSession,
) -> UserResponse:
    user = db.scalar(select(User).where(User.username == credentials.username))
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    raw_token = new_session_token()
    db.add(
        SessionToken(
            token_hash=hash_token(raw_token),
            user_id=user.id,
            expires_at=session_expiry(),
        )
    )
    db.commit()
    _set_cookie(response, raw_token)
    return _user_response(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    db: DbSession,
    session_token: SessionCookie = None,
) -> Response:
    if session_token:
        db.execute(delete(SessionToken).where(SessionToken.token_hash == hash_token(session_token)))
        db.commit()
    response.status_code = status.HTTP_204_NO_CONTENT
    response.delete_cookie(COOKIE_NAME, path="/")
    return response


@router.get("/me", response_model=UserResponse)
def me(user: CurrentUser) -> UserResponse:
    return _user_response(user)
