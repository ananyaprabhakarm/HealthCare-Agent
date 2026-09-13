import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import create_app
from app.auth import JWT_ALGORITHM, JWT_SECRET
from app.db import Base, get_db


@pytest.fixture()
def client():
    # StaticPool pins the engine to a single underlying connection, so every
    # request (even from TestClient's background thread) sees the same
    # in-memory database instead of each getting its own empty one.
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestSessionLocal = sessionmaker(bind=engine)

    def override_get_db():
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def _signup(client, **overrides):
    payload = {"role": "patient", "name": "Pat Patient", "email": "pat@example.com", "password": "hunter22"}
    payload.update(overrides)
    return client.post("/api/auth/signup", json=payload)


def test_signup_and_login_patient(client):
    signup_resp = _signup(client)
    assert signup_resp.status_code == 201
    body = signup_resp.json()
    assert body["role"] == "patient"
    assert body["email"] == "pat@example.com"
    assert "access_token" in body

    login_resp = client.post("/api/auth/login", json={"email": "pat@example.com", "password": "hunter22"})
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]

    me_resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["role"] == "patient"
    assert me_resp.json()["email"] == "pat@example.com"


def test_signup_doctor(client):
    resp = _signup(
        client,
        role="doctor",
        name="Dr. Ahuja",
        email="ahuja@example.com",
        password="secretpw",
        specialization="Cardiology",
    )
    assert resp.status_code == 201
    assert resp.json()["role"] == "doctor"


def test_signup_duplicate_email_across_roles_rejected(client):
    _signup(client, email="dup@example.com")
    resp = _signup(client, role="doctor", email="dup@example.com", name="Dr. Someone")
    assert resp.status_code == 409


def test_login_wrong_password_rejected(client):
    _signup(client, email="user@example.com", password="correct-password")
    resp = client.post("/api/auth/login", json={"email": "user@example.com", "password": "wrong-password"})
    assert resp.status_code == 401


def test_login_unknown_email_rejected(client):
    resp = client.post("/api/auth/login", json={"email": "nobody@example.com", "password": "whatever1"})
    assert resp.status_code == 401


def test_me_without_token_rejected(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


def test_me_with_garbage_token_rejected(client):
    resp = client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert resp.status_code == 401


def test_expired_token_rejected(client):
    now = datetime.now(timezone.utc)
    expired_token = jwt.encode(
        {"sub": str(uuid.uuid4()), "role": "patient", "iat": now - timedelta(days=10), "exp": now - timedelta(days=3)},
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )
    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert resp.status_code == 401


def test_doctor_only_route_rejects_patient_token(client):
    _signup(client, email="p2@example.com")
    token = client.post("/api/auth/login", json={"email": "p2@example.com", "password": "hunter22"}).json()["access_token"]
    resp = client.post("/api/doctor/summary", json={"timeframe": "today"}, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


def test_patient_chat_requires_auth(client):
    resp = client.post("/api/chat/patient", json={"message": "hello"})
    assert resp.status_code == 401


def test_session_ownership_enforced(client, monkeypatch):
    class FakeLLM:
        def chat(self, turns, tools):
            return {"content": "ok", "tool_calls": []}

    monkeypatch.setattr("app.agent.chat_service.LLMClient", lambda: FakeLLM())

    _signup(client, email="p1@example.com")
    token1 = client.post("/api/auth/login", json={"email": "p1@example.com", "password": "hunter22"}).json()["access_token"]
    _signup(client, email="p2b@example.com")
    token2 = client.post("/api/auth/login", json={"email": "p2b@example.com", "password": "hunter22"}).json()["access_token"]

    resp1 = client.post("/api/chat/patient", json={"message": "hi"}, headers={"Authorization": f"Bearer {token1}"})
    assert resp1.status_code == 200
    session_id = resp1.json()["session_id"]

    resp2 = client.post(
        "/api/chat/patient",
        json={"session_id": session_id, "message": "let me in"},
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert resp2.status_code == 403
