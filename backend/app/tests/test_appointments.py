from datetime import datetime, time, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.domain.appointments import (
    cancel_patient_appointment,
    create_appointment,
    create_doctor_availability,
    delete_doctor_availability,
    get_appointment_stats,
    get_doctor_availability,
    get_doctor_directory,
    get_doctor_schedule_today,
    get_doctor_weekly_availability,
    get_patient_appointments,
)
from app.models import Appointment, Doctor, DoctorAvailability, Patient
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


def _other_weekday(doctor_weekday: int) -> int:
    return (doctor_weekday + 1) % 7


def test_create_doctor_availability_success(db_session, doctor):
    today_weekday = datetime.now(timezone.utc).date().weekday()
    other_day = _other_weekday(today_weekday)

    entry = create_doctor_availability(db_session, doctor.id, other_day, time(14, 0), time(15, 0))

    assert entry.id is not None
    assert entry.day_of_week == other_day
    assert entry.start_time == time(14, 0)
    assert entry.end_time == time(15, 0)
    entries = get_doctor_weekly_availability(db_session, doctor.id)
    assert len(entries) == 2


def test_create_doctor_availability_rejects_invalid_range(db_session, doctor):
    other_day = _other_weekday(datetime.now(timezone.utc).date().weekday())
    with pytest.raises(ValueError, match="start_time must be before end_time"):
        create_doctor_availability(db_session, doctor.id, other_day, time(15, 0), time(14, 0))


def test_create_doctor_availability_rejects_overlap(db_session, doctor):
    today_weekday = datetime.now(timezone.utc).date().weekday()
    with pytest.raises(ValueError, match="overlaps"):
        create_doctor_availability(db_session, doctor.id, today_weekday, time(9, 30), time(10, 30))


def test_delete_doctor_availability_removes_own_slot(db_session, doctor):
    entries = get_doctor_weekly_availability(db_session, doctor.id)
    deleted = delete_doctor_availability(db_session, doctor.id, entries[0].id)
    assert deleted is True
    assert get_doctor_weekly_availability(db_session, doctor.id) == []


def test_delete_doctor_availability_rejects_other_doctors_slot(db_session, doctor):
    other_doctor = Doctor(name="Dr. Other", email="other.doc@example.com", password_hash="unused")
    db_session.add(other_doctor)
    db_session.commit()
    db_session.refresh(other_doctor)

    entries = get_doctor_weekly_availability(db_session, doctor.id)
    deleted = delete_doctor_availability(db_session, other_doctor.id, entries[0].id)

    assert deleted is False
    assert len(get_doctor_weekly_availability(db_session, doctor.id)) == 1


def _create_future_appointment(db_session, doctor, patient_email: str, reason: str | None = None) -> "Appointment":
    """Books an appointment a fixed 30 min from now, bypassing the doctor's
    availability window. _book_first_slot's fixed 9:00 AM "today" slot
    becomes a *past* appointment for any test run after 9:30 AM, which
    would wrongly trip the "can't cancel a past appointment" rule below."""
    patient = db_session.query(Patient).filter(Patient.email == patient_email).first()
    if not patient:
        patient = Patient(name="Test Patient", email=patient_email, password_hash="unused")
        db_session.add(patient)
        db_session.commit()
        db_session.refresh(patient)

    start = datetime.now(timezone.utc) + timedelta(minutes=30)
    appointment = Appointment(
        doctor_id=doctor.id,
        patient_id=patient.id,
        start_datetime=start,
        end_datetime=start + timedelta(minutes=30),
        status="scheduled",
        reason=reason,
    )
    db_session.add(appointment)
    db_session.commit()
    db_session.refresh(appointment)
    return appointment


def test_cancel_patient_appointment_success(db_session, doctor):
    appointment = _create_future_appointment(db_session, doctor, "cancel-me@example.com")

    result = cancel_patient_appointment(db_session, appointment.patient_id, appointment.id)

    assert result is not None
    assert result.status == "cancelled"


def test_cancel_patient_appointment_rejects_other_patients_appointment(db_session, doctor):
    _book_first_slot(db_session, doctor, patient_email="owner@example.com")
    owner = db_session.query(Patient).filter(Patient.email == "owner@example.com").first()
    appointment = db_session.query(Appointment).filter(Appointment.patient_id == owner.id).first()

    intruder = Patient(name="Intruder", email="intruder@example.com", password_hash="unused")
    db_session.add(intruder)
    db_session.commit()
    db_session.refresh(intruder)

    result = cancel_patient_appointment(db_session, intruder.id, appointment.id)

    assert result is None
    assert db_session.get(Appointment, appointment.id).status == "scheduled"


def test_cancel_patient_appointment_rejects_already_cancelled(db_session, doctor):
    appointment = _create_future_appointment(db_session, doctor, "twice@example.com")

    cancel_patient_appointment(db_session, appointment.patient_id, appointment.id)
    with pytest.raises(ValueError, match="already cancelled"):
        cancel_patient_appointment(db_session, appointment.patient_id, appointment.id)


def test_cancel_patient_appointment_rejects_past_appointment(db_session, doctor):
    patient = Patient(name="Past Patient", email="past@example.com", password_hash="unused")
    db_session.add(patient)
    db_session.commit()
    db_session.refresh(patient)

    past_start = datetime.now(timezone.utc) - timedelta(days=1)
    appointment = Appointment(
        doctor_id=doctor.id,
        patient_id=patient.id,
        start_datetime=past_start,
        end_datetime=past_start + timedelta(minutes=30),
        status="scheduled",
    )
    db_session.add(appointment)
    db_session.commit()
    db_session.refresh(appointment)

    with pytest.raises(ValueError, match="past appointment"):
        cancel_patient_appointment(db_session, patient.id, appointment.id)


def test_get_appointment_stats_excludes_cancelled_appointment(db_session, doctor):
    """Explicit verification (per Phase 3 spec) that stats already exclude
    cancelled appointments, rather than just assuming the existing filter covers it."""
    appointment = _create_future_appointment(db_session, doctor, "stats-cancel@example.com")

    cancel_patient_appointment(db_session, appointment.patient_id, appointment.id)

    stats = get_appointment_stats(db_session, DoctorStatsRequest(doctor_email=doctor.email, timeframe="today"))
    assert stats.stats.total == 0


def test_get_doctor_schedule_today_still_shows_cancelled_appointment(db_session, doctor):
    """Explicit verification (per Phase 3 spec) that a doctor's schedule still
    surfaces a cancelled appointment (labeled as such) rather than hiding it."""
    appointment = _create_future_appointment(db_session, doctor, "schedule-cancel@example.com")

    cancel_patient_appointment(db_session, appointment.patient_id, appointment.id)

    schedule = get_doctor_schedule_today(db_session, doctor.id)
    assert len(schedule) == 1
    assert schedule[0].status == "cancelled"
