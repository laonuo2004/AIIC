import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import attachments, auth, chat, face, interviews, providers
from app.core.config import Settings, get_settings
from app.core.database import init_db

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    init_db()
    yield


app = FastAPI(title="ResearchMocker API", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/status")
def runtime_status() -> dict[str, object]:
    current: Settings = get_settings()
    return {
        "app_env": current.app_env,
        "database": "sqlite" if current.database_url.startswith("sqlite") else "external",
        "upload_limit_bytes": current.max_upload_bytes,
        "max_attachments_per_message": current.max_attachments_per_message,
        "max_pdf_pages_per_attachment": current.max_pdf_pages_per_attachment,
        "proxy_enabled": bool(
            current.openrouter_http_proxy
            or os.environ.get("HTTP_PROXY")
            or os.environ.get("HTTPS_PROXY")
            or os.environ.get("NO_PROXY")
        ),
        "model_strategy": {
            "deep": current.interview_deep_model,
            "fast": current.interview_fast_model,
            "feedback": current.interview_feedback_model,
        },
    }


app.include_router(auth.router)
app.include_router(interviews.router)
app.include_router(chat.router)
app.include_router(face.router)
app.include_router(providers.router)
app.include_router(attachments.router)
