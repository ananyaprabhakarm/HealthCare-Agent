from datetime import datetime, time
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ChatMessageSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    sender: str
    content: str
    created_at: datetime


class ChatSessionSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    user_role: str
    created_at: datetime
    last_active_at: datetime


class ChatRequest(BaseModel):
    session_id: Optional[UUID] = None
    message: str


class ChatResponse(BaseModel):
    session_id: UUID
    messages: List[ChatMessageSchema]


class Slot(BaseModel):
    start: datetime
    end: datetime
    label: str


class AvailabilityResponse(BaseModel):
    doctor_id: UUID
    doctor_name: str
    date: str
    slots: List[Slot]


class AppointmentCreatePayload(BaseModel):
    doctor_name: str
    patient_email: EmailStr
    patient_name: str
    start: datetime
    end: datetime
    reason: str | None = None
    symptoms: list[str] | None = None


class AppointmentResponse(BaseModel):
    appointment_id: UUID
    status: str
    calendar_event_id: str | None = None


class DoctorStatsRequest(BaseModel):
    doctor_email: EmailStr
    timeframe: str
    symptom_filter: str | None = None


class DoctorSummaryRequest(BaseModel):
    """Public request body for POST /api/doctor/summary. No email field —
    the doctor is identified by their authenticated session, not the body."""

    timeframe: str
    symptom_filter: str | None = None


class DoctorStats(BaseModel):
    total: int
    by_status: dict[str, int]


class DoctorStatsResponse(BaseModel):
    doctor_name: str
    timeframe: str
    stats: DoctorStats
    summary: str


class SignupRequest(BaseModel):
    role: Literal["patient", "doctor"]
    name: str
    email: EmailStr
    password: str = Field(min_length=6)
    phone: str | None = None
    specialization: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    role: str
    name: str
    email: str


class MeResponse(BaseModel):
    id: UUID
    role: str
    name: str
    email: str


class PatientAppointmentSummary(BaseModel):
    id: UUID
    doctor_name: str
    doctor_specialization: str | None = None
    start_datetime: datetime
    end_datetime: datetime
    status: str
    reason: str | None = None


class DoctorDirectoryEntry(BaseModel):
    id: UUID
    name: str
    specialization: str | None = None
    available_today: bool


class DoctorScheduleEntry(BaseModel):
    id: UUID
    patient_name: str
    start_datetime: datetime
    end_datetime: datetime
    status: str
    reason: str | None = None


class DoctorAvailabilityEntry(BaseModel):
    id: UUID
    day_of_week: int
    start_time: time
    end_time: time


class DoctorAvailabilityCreate(BaseModel):
    day_of_week: int = Field(ge=0, le=6)
    start_time: time
    end_time: time


