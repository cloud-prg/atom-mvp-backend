import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ["DATABASE_URL"] = "sqlite:///./data/test.db"
os.environ["DEMO_MODE"] = "true"

from app.db import Base, engine  # noqa: E402
from app.models import EmailVerificationCode  # noqa: E402
from app.main import app  # noqa: E402
from app.services.auth_service import hash_verification_code  # noqa: E402


@pytest.fixture(autouse=True)
def reset_database(monkeypatch):
    Path("data").mkdir(exist_ok=True)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    monkeypatch.setattr("app.services.auth_service.send_email_verification_code", lambda email, code: None)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def db_session():
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def auth_headers(client: TestClient, db_session) -> dict[str, str]:
    response = client.post("/api/auth/admin/login", json={"username": "admin", "password": "admin"})
    assert response.status_code == 200
    token = response.json()["token"]
    return {"Authorization": f"Bearer {token}"}
