from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()

if settings.database_url.startswith("sqlite:///"):
    sqlite_path = settings.database_url.removeprefix("sqlite:///")
    if sqlite_path and sqlite_path != ":memory:":
        Path(sqlite_path).parent.mkdir(parents=True, exist_ok=True)

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from app.models import entities  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _patch_sqlite_schema()


def _patch_sqlite_schema() -> None:
    if not settings.database_url.startswith("sqlite"):
        return
    inspector = inspect(engine)
    if "face_video_jobs" not in inspector.get_table_names():
        return
    existing = {column["name"] for column in inspector.get_columns("face_video_jobs")}
    additions = {
        "provider_request_id": "VARCHAR(255)",
        "audio_path": "TEXT",
        "audio_media_token": "VARCHAR(80)",
    }
    with engine.begin() as connection:
        for column, definition in additions.items():
            if column not in existing:
                statement = f"ALTER TABLE face_video_jobs ADD COLUMN {column} {definition}"
                connection.execute(text(statement))
