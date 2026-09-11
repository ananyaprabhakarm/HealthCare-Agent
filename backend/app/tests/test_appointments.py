from datetime import datetime, time, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.domain.appointments import (
    create_appointment,
    get_appointment_stats,
    get_doctor_availability,
)
from app.models import Doctor, DoctorAvailability
from app.schemas import AppointmentCreatePayload, DoctorStatsRequest


class FakeCalendarClient:
    def create_event(self, *args, **kwargs):
        return "fake-event-id"


class FakeEmailClient:
    def send_email(self, *args, **kwargs):
        return "fake-email-id"


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture()
def doctor(db_session):
    doc = Doctor(name="Dr. Ahuja", email="ahuja@example.com")
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)
    weekday = str(datetime.now(timezone.utc).date().weekday())
    db_session.add(DoctorAvailability(
        doctor_id=doc.id,
        weekday=weekday,
        start_time=time(9, 0),
        end_time=time(10, 0),
        slot_duration_minutes="30",
    ))
    db_session.commit()
    return doc


def _book_first_slot(db_session, doctor, **overrides):
    today = datetime.now(timezone.utc).date()
    start = datetime.combine(today, time(9, 0), tzinfo=timezone.utc)
    end = start + timedelta(minutes=30)
    payload = AppointmentCreatePayload(
        doctor_name=doctor.name,
        patient_email=overrides.get("patient_email", "pat@example.com"),
        patient_name=overrides.get("patient_name", "Pat Patient"),
        start=start,
        end=end,
        reason=overrides.get("reason"),
    )
    return create_appointment(db_session, payload, FakeCalendarClient(), FakeEmailClient())


def test_get_doctor_availability_returns_all_open_slots(db_session, doctor):
    today = datetime.now(timezone.utc).date().isoformat()
    result = get_doctor_availability(db_session, doctor.name, today)
    assert len(result.slots) == 2


def test_get_doctor_availability_excludes_booked_slot(db_session, doctor):
    _book_first_slot(db_session, doctor)
    today = datetime.now(timezone.utc).date().isoformat()
    result = get_doctor_availability(db_session, doctor.name, today)
    assert len(result.slots) == 1
    assert result.slots[0].label == "09:30 AM"


def test_create_appointment_rejects_overlap(db_session, doctor):
    _book_first_slot(db_session, doctor)
    with pytest.raises(ValueError, match="Slot not available"):
        _book_first_slot(db_session, doctor, patient_email="other@example.com")


def test_get_appointment_stats_counts_scheduled_appointment(db_session, doctor):
    _book_first_slot(db_session, doctor, reason="fever")
    stats = get_appointment_stats(
        db_session,
        DoctorStatsRequest(doctor_email=doctor.email, timeframe="today"),
    )
    assert stats.stats.total == 1
    assert stats.stats.by_status["scheduled"] == 1


def test_get_appointment_stats_symptom_filter_excludes_non_matching(db_session, doctor):
    _book_first_slot(db_session, doctor, reason="fever")
    stats = get_appointment_stats(
        db_session,
        DoctorStatsRequest(doctor_email=doctor.email, timeframe="today", symptom_filter="cough"),
    )
    assert stats.stats.total == 0
