from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import create_app
from app.db import Base, get_db
from app.models import Appointment, Doctor, Patient


@pytest.fixture()
def engine():
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=eng)
    return eng


@pytest.fixture()
def client(engine):
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


@pytest.fixture()
def db_session(engine):
    """A raw session bound to the same in-memory engine `client` uses, for
    tests that need to seed data (e.g. an appointment) with no REST endpoint
    to create it through — booking only happens via the chat/LLM tool-calling
    flow, which route-level tests shouldn't have to drive."""
    TestSessionLocal = sessionmaker(bind=engine)
    session = TestSessionLocal()
    yield session
    session.close()


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


def test_add_availability_success(client):
    token = _signup_and_login(client, "doctor", "doc-avail@example.com")
    resp = client.post(
        "/api/doctors/me/availability",
        json={"day_of_week": 1, "start_time": "09:00", "end_time": "10:00"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["day_of_week"] == 1
    assert "id" in body


def test_add_availability_requires_doctor_role(client):
    token = _signup_and_login(client, "patient", "pat-avail@example.com")
    resp = client.post(
        "/api/doctors/me/availability",
        json={"day_of_week": 1, "start_time": "09:00", "end_time": "10:00"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


def test_add_availability_rejects_invalid_range(client):
    token = _signup_and_login(client, "doctor", "doc-range@example.com")
    resp = client.post(
        "/api/doctors/me/availability",
        json={"day_of_week": 1, "start_time": "10:00", "end_time": "09:00"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400


def test_add_availability_rejects_overlap(client):
    token = _signup_and_login(client, "doctor", "doc-overlap@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    client.post(
        "/api/doctors/me/availability",
        json={"day_of_week": 2, "start_time": "09:00", "end_time": "10:00"},
        headers=headers,
    )
    resp = client.post(
        "/api/doctors/me/availability",
        json={"day_of_week": 2, "start_time": "09:30", "end_time": "10:30"},
        headers=headers,
    )
    assert resp.status_code == 400


def test_delete_availability_requires_doctor_role(client):
    token = _signup_and_login(client, "patient", "pat-del@example.com")
    resp = client.delete(
        "/api/doctors/me/availability/00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


def test_delete_availability_removes_own_slot(client):
    token = _signup_and_login(client, "doctor", "doc-del2@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    created = client.post(
        "/api/doctors/me/availability",
        json={"day_of_week": 3, "start_time": "09:00", "end_time": "10:00"},
        headers=headers,
    ).json()

    resp = client.delete(f"/api/doctors/me/availability/{created['id']}", headers=headers)

    assert resp.status_code == 204
    assert client.get("/api/doctors/me/availability", headers=headers).json() == []


def test_delete_availability_rejects_other_doctors_slot(client):
    owner_token = _signup_and_login(client, "doctor", "doc-owner@example.com")
    intruder_token = _signup_and_login(client, "doctor", "doc-intruder@example.com")
    created = client.post(
        "/api/doctors/me/availability",
        json={"day_of_week": 4, "start_time": "09:00", "end_time": "10:00"},
        headers={"Authorization": f"Bearer {owner_token}"},
    ).json()

    resp = client.delete(
        f"/api/doctors/me/availability/{created['id']}",
        headers={"Authorization": f"Bearer {intruder_token}"},
    )

    assert resp.status_code == 404
    remaining = client.get("/api/doctors/me/availability", headers={"Authorization": f"Bearer {owner_token}"}).json()
    assert len(remaining) == 1


def test_cancel_appointment_requires_patient_role(client):
    token = _signup_and_login(client, "doctor", "doc-cancelrole@example.com")
    resp = client.patch(
        "/api/patients/me/appointments/00000000-0000-0000-0000-000000000000/cancel",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


def test_cancel_appointment_rejects_unknown_id(client):
    token = _signup_and_login(client, "patient", "pat-unknown@example.com")
    resp = client.patch(
        "/api/patients/me/appointments/00000000-0000-0000-0000-000000000000/cancel",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


def test_cancel_appointment_success(client, db_session):
    _signup_and_login(client, "doctor", "doc-cancel@example.com")
    patient_token = _signup_and_login(client, "patient", "pat-cancel@example.com")

    doctor = db_session.query(Doctor).filter(Doctor.email == "doc-cancel@example.com").first()
    patient = db_session.query(Patient).filter(Patient.email == "pat-cancel@example.com").first()
    start = datetime.now(timezone.utc) + timedelta(hours=1)
    appt = Appointment(
        doctor_id=doctor.id,
        patient_id=patient.id,
        start_datetime=start,
        end_datetime=start + timedelta(minutes=30),
        status="scheduled",
    )
    db_session.add(appt)
    db_session.commit()
    db_session.refresh(appt)

    resp = client.patch(
        f"/api/patients/me/appointments/{appt.id}/cancel",
        headers={"Authorization": f"Bearer {patient_token}"},
    )

    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"


def test_cancel_appointment_rejects_other_patients_appointment(client, db_session):
    _signup_and_login(client, "doctor", "doc-cancel2@example.com")
    _signup_and_login(client, "patient", "owner-cancel@example.com")
    intruder_token = _signup_and_login(client, "patient", "intruder-cancel@example.com")

    doctor = db_session.query(Doctor).filter(Doctor.email == "doc-cancel2@example.com").first()
    owner = db_session.query(Patient).filter(Patient.email == "owner-cancel@example.com").first()
    start = datetime.now(timezone.utc) + timedelta(hours=1)
    appt = Appointment(
        doctor_id=doctor.id,
        patient_id=owner.id,
        start_datetime=start,
        end_datetime=start + timedelta(minutes=30),
        status="scheduled",
    )
    db_session.add(appt)
    db_session.commit()
    db_session.refresh(appt)

    resp = client.patch(
        f"/api/patients/me/appointments/{appt.id}/cancel",
        headers={"Authorization": f"Bearer {intruder_token}"},
    )

    assert resp.status_code == 404
    assert db_session.get(Appointment, appt.id).status == "scheduled"
