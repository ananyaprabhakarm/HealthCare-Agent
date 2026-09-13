from datetime import datetime, timedelta, time, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from ..models import Doctor, Patient, Appointment, DoctorAvailability
from ..schemas import (
    AvailabilityResponse,
    Slot,
    AppointmentCreatePayload,
    AppointmentResponse,
    DoctorAvailabilityEntry,
    DoctorDirectoryEntry,
    DoctorScheduleEntry,
    DoctorStatsRequest,
    DoctorStats,
    DoctorStatsResponse,
    PatientAppointmentSummary,
)
from ..services.calendar import CalendarClient
from ..services.email import EmailClient
from ..services.notification import NotificationClient


def find_doctor_by_name(db: Session, name: str) -> Optional[Doctor]:
    return db.query(Doctor).filter(Doctor.name.ilike(name)).first()


def get_doctor_availability(db: Session, doctor_name: str, date_str: str, preferred_slot: Optional[str] = None) -> AvailabilityResponse:
    doctor = find_doctor_by_name(db, doctor_name)
    if not doctor:
        raise ValueError("Doctor not found")
    date = datetime.fromisoformat(date_str).date()
    weekday = str(date.weekday())
    availability = db.query(DoctorAvailability).filter(DoctorAvailability.doctor_id == doctor.id, DoctorAvailability.weekday == weekday).first()
    slots: List[Slot] = []
    if availability:
        start_dt = datetime.combine(date, availability.start_time, tzinfo=timezone.utc)
        end_dt = datetime.combine(date, availability.end_time, tzinfo=timezone.utc)
        duration = int(availability.slot_duration_minutes)
        current = start_dt
        while current + timedelta(minutes=duration) <= end_dt:
            overlapping = db.query(Appointment).filter(Appointment.doctor_id == doctor.id, Appointment.status == "scheduled", Appointment.start_datetime <= current, Appointment.end_datetime > current).first()
            if not overlapping:
                label = current.strftime("%I:%M %p")
                if preferred_slot == "morning" and current.time() >= time(12, 0):
                    current += timedelta(minutes=duration)
                    continue
                if preferred_slot == "afternoon" and current.time() < time(12, 0):
                    current += timedelta(minutes=duration)
                    continue
                slots.append(Slot(start=current, end=current + timedelta(minutes=duration), label=label))
            current += timedelta(minutes=duration)
    return AvailabilityResponse(doctor_id=doctor.id, doctor_name=doctor.name, date=str(date), slots=slots)


def create_appointment(db: Session, payload: AppointmentCreatePayload, calendar_client: CalendarClient, email_client: EmailClient) -> AppointmentResponse:
    doctor = find_doctor_by_name(db, payload.doctor_name)
    if not doctor:
        raise ValueError("Doctor not found")
    patient = db.query(Patient).filter(Patient.email == payload.patient_email).first()
    if not patient:
        # In the authenticated chat flow this patient already has an account
        # (payload.patient_email is always the signed-in patient's own email),
        # so this branch is a safety net, not the normal path. password_hash is
        # left blank — a record created here can't be used to log in.
        patient = Patient(name=payload.patient_name, email=payload.patient_email, password_hash="")
        db.add(patient)
        db.commit()
        db.refresh(patient)
    overlapping = db.query(Appointment).filter(Appointment.doctor_id == doctor.id, Appointment.status == "scheduled", Appointment.start_datetime < payload.end, Appointment.end_datetime > payload.start).first()
    if overlapping:
        raise ValueError("Slot not available")
    appointment = Appointment(doctor_id=doctor.id, patient_id=patient.id, start_datetime=payload.start, end_datetime=payload.end, status="scheduled", reason=payload.reason, symptoms=payload.symptoms)
    db.add(appointment)
    db.commit()
    db.refresh(appointment)
    summary = f"Appointment with {doctor.name}"
    description = payload.reason or ""
    attendees = [doctor.email, patient.email]
    calendar_event_id = calendar_client.create_event(doctor.google_calendar_id or "primary", summary, description, payload.start, payload.end, attendees)
    subject = f"Appointment confirmed with {doctor.name}"
    body = f"Your appointment is scheduled from {payload.start} to {payload.end}."
    email_client.send_email(patient.email, subject, body)
    return AppointmentResponse(appointment_id=appointment.id, status=appointment.status, calendar_event_id=calendar_event_id)


def get_appointment_stats(db: Session, request: DoctorStatsRequest) -> DoctorStatsResponse:
    doctor = db.query(Doctor).filter(Doctor.email == request.doctor_email).first()
    if not doctor:
        raise ValueError("Doctor not found")
    now = datetime.now(timezone.utc)
    if request.timeframe == "today":
        start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
        end = start + timedelta(days=1)
    elif request.timeframe == "yesterday":
        end = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
        start = end - timedelta(days=1)
    elif request.timeframe == "tomorrow":
        start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc) + timedelta(days=1)
        end = start + timedelta(days=1)
    else:
        start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
        end = start + timedelta(days=1)
    query = db.query(Appointment).filter(Appointment.doctor_id == doctor.id, Appointment.start_datetime >= start, Appointment.start_datetime < end, Appointment.status != "cancelled")
    if request.symptom_filter:
        query = query.filter(Appointment.reason.ilike(f"%{request.symptom_filter}%"))
    appointments = query.all()
    total = len(appointments)
    by_status: Dict[str, int] = {}
    for a in appointments:
        by_status[a.status] = by_status.get(a.status, 0) + 1
    stats = DoctorStats(total=total, by_status=by_status)
    summary = f"{doctor.name} has {total} appointments in {request.timeframe}."
    if request.symptom_filter:
        summary += f" Filtered by {request.symptom_filter}."
    return DoctorStatsResponse(doctor_name=doctor.name, timeframe=request.timeframe, stats=stats, summary=summary)


def send_doctor_notification(db: Session, doctor_email: str, channel: str, message: str, notification_client: NotificationClient) -> Dict[str, Any]:
    doctor = db.query(Doctor).filter(Doctor.email == doctor_email).first()
    if not doctor:
        raise ValueError("Doctor not found")
    recipient = doctor.email
    external_id = notification_client.send(channel, recipient, message)
    return {"status": "sent", "channel": channel, "recipient": recipient, "external_id": external_id}


def get_patient_appointments(db: Session, patient_id: UUID) -> List[PatientAppointmentSummary]:
    appointments = (
        db.query(Appointment)
        .filter(Appointment.patient_id == patient_id)
        .order_by(Appointment.start_datetime.desc())
        .all()
    )
    return [
        PatientAppointmentSummary(
            id=a.id,
            doctor_name=a.doctor.name,
            doctor_specialization=a.doctor.specialization,
            start_datetime=a.start_datetime,
            end_datetime=a.end_datetime,
            status=a.status,
            reason=a.reason,
        )
        for a in appointments
    ]


def get_doctor_directory(db: Session) -> List[DoctorDirectoryEntry]:
    doctors = db.query(Doctor).order_by(Doctor.name).all()
    today_str = datetime.now(timezone.utc).date().isoformat()
    entries = []
    for doctor in doctors:
        availability = get_doctor_availability(db, doctor.name, today_str)
        entries.append(DoctorDirectoryEntry(
            id=doctor.id,
            name=doctor.name,
            specialization=doctor.specialization,
            available_today=len(availability.slots) > 0,
        ))
    return entries


def get_doctor_schedule_today(db: Session, doctor_id: UUID) -> List[DoctorScheduleEntry]:
    now = datetime.now(timezone.utc)
    start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    appointments = (
        db.query(Appointment)
        .filter(
            Appointment.doctor_id == doctor_id,
            Appointment.start_datetime >= start,
            Appointment.start_datetime < end,
        )
        .order_by(Appointment.start_datetime.asc())
        .all()
    )
    return [
        DoctorScheduleEntry(
            id=a.id,
            patient_name=a.patient.name,
            start_datetime=a.start_datetime,
            end_datetime=a.end_datetime,
            status=a.status,
            reason=a.reason,
        )
        for a in appointments
    ]


def get_doctor_weekly_availability(db: Session, doctor_id: UUID) -> List[DoctorAvailabilityEntry]:
    rows = (
        db.query(DoctorAvailability)
        .filter(DoctorAvailability.doctor_id == doctor_id)
        .order_by(DoctorAvailability.weekday.asc())
        .all()
    )
    return [
        DoctorAvailabilityEntry(id=row.id, day_of_week=int(row.weekday), start_time=row.start_time, end_time=row.end_time)
        for row in rows
    ]


def create_doctor_availability(
    db: Session, doctor_id: UUID, day_of_week: int, start_time: time, end_time: time
) -> DoctorAvailabilityEntry:
    if start_time >= end_time:
        raise ValueError("start_time must be before end_time")

    weekday_str = str(day_of_week)
    existing_rows = (
        db.query(DoctorAvailability)
        .filter(DoctorAvailability.doctor_id == doctor_id, DoctorAvailability.weekday == weekday_str)
        .all()
    )
    for row in existing_rows:
        if start_time < row.end_time and row.start_time < end_time:
            raise ValueError("This overlaps an existing availability slot")

    row = DoctorAvailability(
        doctor_id=doctor_id,
        weekday=weekday_str,
        start_time=start_time,
        end_time=end_time,
        slot_duration_minutes="30",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return DoctorAvailabilityEntry(id=row.id, day_of_week=day_of_week, start_time=row.start_time, end_time=row.end_time)


def delete_doctor_availability(db: Session, doctor_id: UUID, availability_id: UUID) -> bool:
    row = (
        db.query(DoctorAvailability)
        .filter(DoctorAvailability.id == availability_id, DoctorAvailability.doctor_id == doctor_id)
        .first()
    )
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True


def cancel_patient_appointment(db: Session, patient_id: UUID, appointment_id: UUID) -> Optional[PatientAppointmentSummary]:
    appointment = (
        db.query(Appointment)
        .filter(Appointment.id == appointment_id, Appointment.patient_id == patient_id)
        .first()
    )
    if not appointment:
        return None
    if appointment.status == "cancelled":
        raise ValueError("Appointment is already cancelled")
    # SQLite drops tzinfo on round-trip (Postgres doesn't) — this app stores
    # everything in UTC, so a naive value read back is always UTC.
    start_datetime = appointment.start_datetime
    if start_datetime.tzinfo is None:
        start_datetime = start_datetime.replace(tzinfo=timezone.utc)
    if start_datetime < datetime.now(timezone.utc):
        raise ValueError("Cannot cancel a past appointment")

    appointment.status = "cancelled"
    db.commit()
    db.refresh(appointment)
    return PatientAppointmentSummary(
        id=appointment.id,
        doctor_name=appointment.doctor.name,
        doctor_specialization=appointment.doctor.specialization,
        start_datetime=appointment.start_datetime,
        end_datetime=appointment.end_datetime,
        status=appointment.status,
        reason=appointment.reason,
    )


