import os
import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ["DATABASE_URL"] = "sqlite:///./data/test.sqlite3"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["APP_ENV"] = "test"
os.environ["UPLOAD_DIR"] = "./data/test-uploads"

from app.core.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture()
def client() -> Iterator[TestClient]:
    upload_dir = Path(os.environ["UPLOAD_DIR"])
    if upload_dir.exists():
        shutil.rmtree(upload_dir)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as test_client:
        yield test_client
    if upload_dir.exists():
        shutil.rmtree(upload_dir)
