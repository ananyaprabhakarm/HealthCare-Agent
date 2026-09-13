import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import create_app
from app.db import Base, get_db


@pytest.fixture()
def client():
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


def _signup_and_login(client, role, email):
    client.post("/api/auth/signup", json={"role": role, "name": f"{role} test", "email": email, "password": "password123"})
    return client.post("/api/auth/login", json={"email": email, "password": "password123"}).json()["access_token"]


def test_patient_appointments_requires_auth(client):
    resp = client.get("/api/patients/me/appointments")
    assert resp.status_code == 401


def test_patient_appointments_rejects_doctor_token(client):
    token = _signup_and_login(client, "doctor", "doc1@example.com")
    resp = client.get("/api/patients/me/appointments", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


def test_patient_appointments_empty_list_for_new_patient(client):
    token = _signup_and_login(client, "patient", "pat1@example.com")
    resp = client.get("/api/patients/me/appointments", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json() == []


def test_doctor_directory_accessible_by_any_authenticated_role(client):
    _signup_and_login(client, "doctor", "doc2@example.com")
    patient_token = _signup_and_login(client, "patient", "pat2@example.com")
    resp = client.get("/api/doctors", headers={"Authorization": f"Bearer {patient_token}"})
    assert resp.status_code == 200
    names = [d["name"] for d in resp.json()]
    assert "doctor test" in names


def test_doctor_directory_requires_auth(client):
    resp = client.get("/api/doctors")
    assert resp.status_code == 401


def test_doctor_schedule_requires_doctor_role(client):
    patient_token = _signup_and_login(client, "patient", "pat3@example.com")
    resp = client.get("/api/doctors/me/schedule/today", headers={"Authorization": f"Bearer {patient_token}"})
    assert resp.status_code == 403


def test_doctor_schedule_empty_for_new_doctor(client):
    token = _signup_and_login(client, "doctor", "doc3@example.com")
    resp = client.get("/api/doctors/me/schedule/today", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json() == []


def test_doctor_availability_requires_doctor_role(client):
    patient_token = _signup_and_login(client, "patient", "pat4@example.com")
    resp = client.get("/api/doctors/me/availability", headers={"Authorization": f"Bearer {patient_token}"})
    assert resp.status_code == 403


def test_doctor_availability_empty_for_new_doctor(client):
    token = _signup_and_login(client, "doctor", "doc4@example.com")
    resp = client.get("/api/doctors/me/availability", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json() == []
