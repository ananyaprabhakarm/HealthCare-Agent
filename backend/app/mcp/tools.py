from datetime import datetime, timedelta, time
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from ..models import Doctor, Patient, Appointment, DoctorAvailability
from ..schemas import AvailabilityResponse, Slot, AppointmentCreatePayload, AppointmentResponse, DoctorStatsRequest, DoctorStats, DoctorStatsResponse
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
        start_dt = datetime.combine(date, availability.start_time)
        end_dt = datetime.combine(date, availability.end_time)
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
        patient = Patient(name=payload.patient_name, email=payload.patient_email)
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
    now = datetime.utcnow()
    if request.timeframe == "today":
        start = datetime(now.year, now.month, now.day)
        end = start + timedelta(days=1)
    elif request.timeframe == "yesterday":
        end = datetime(now.year, now.month, now.day)
        start = end - timedelta(days=1)
    elif request.timeframe == "tomorrow":
        start = datetime(now.year, now.month, now.day) + timedelta(days=1)
        end = start + timedelta(days=1)
    else:
        start = datetime(now.year, now.month, now.day)
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


