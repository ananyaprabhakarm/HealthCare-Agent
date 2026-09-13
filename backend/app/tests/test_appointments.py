from datetime import datetime, time, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.domain.appointments import (
    create_appointment,
    get_appointment_stats,
    get_doctor_availability,
    get_doctor_directory,
    get_doctor_schedule_today,
    get_doctor_weekly_availability,
    get_patient_appointments,
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
    doc = Doctor(name="Dr. Ahuja", email="ahuja@example.com", password_hash="unused-in-this-test")
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


def test_get_patient_appointments_returns_own_bookings(db_session, doctor):
    from app.models import Patient

    _book_first_slot(db_session, doctor, patient_email="pat@example.com", reason="fever")
    patient = db_session.query(Patient).filter(Patient.email == "pat@example.com").first()

    results = get_patient_appointments(db_session, patient.id)

    assert len(results) == 1
    assert results[0].doctor_name == doctor.name
    assert results[0].status == "scheduled"
    assert results[0].reason == "fever"


def test_get_patient_appointments_empty_for_unknown_patient(db_session, doctor):
    import uuid

    assert get_patient_appointments(db_session, uuid.uuid4()) == []


def test_get_doctor_directory_available_today_true_when_open(db_session, doctor):
    entries = get_doctor_directory(db_session)
    assert len(entries) == 1
    assert entries[0].name == doctor.name
    assert entries[0].specialization == doctor.specialization
    assert entries[0].available_today is True


def test_get_doctor_directory_available_today_false_when_fully_booked(db_session, doctor):
    today = datetime.now(timezone.utc).date()
    for start_hour, start_minute, email in [(9, 0, "a@example.com"), (9, 30, "b@example.com")]:
        start = datetime.combine(today, time(start_hour, start_minute), tzinfo=timezone.utc)
        end = start + timedelta(minutes=30)
        create_appointment(
            db_session,
            AppointmentCreatePayload(doctor_name=doctor.name, patient_email=email, patient_name="P", start=start, end=end),
            FakeCalendarClient(),
            FakeEmailClient(),
        )
    entries = get_doctor_directory(db_session)
    assert entries[0].available_today is False


def test_get_doctor_schedule_today_returns_todays_appointments_only(db_session, doctor):
    _book_first_slot(db_session, doctor, reason="checkup")
    schedule = get_doctor_schedule_today(db_session, doctor.id)
    assert len(schedule) == 1
    assert schedule[0].patient_name == "Pat Patient"
    assert schedule[0].reason == "checkup"


def test_get_doctor_weekly_availability_returns_configured_days(db_session, doctor):
    entries = get_doctor_weekly_availability(db_session, doctor.id)
    assert len(entries) == 1
    assert entries[0].day_of_week == datetime.now(timezone.utc).date().weekday()
    assert entries[0].start_time == time(9, 0)
    assert entries[0].end_time == time(10, 0)
