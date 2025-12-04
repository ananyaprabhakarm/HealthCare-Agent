from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr


class ChatMessageSchema(BaseModel):
    id: UUID
    sender: str
    content: str
    created_at: datetime

    class Config:
        orm_mode = True


class ChatSessionSchema(BaseModel):
    id: UUID
    user_role: str
    created_at: datetime
    last_active_at: datetime

    class Config:
        orm_mode = True


class ChatRequest(BaseModel):
    session_id: Optional[UUID] = None
    message: str
    user_email: Optional[EmailStr] = None


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


class DoctorStats(BaseModel):
    total: int
    by_status: dict[str, int]


class DoctorStatsResponse(BaseModel):
    doctor_name: str
    timeframe: str
    stats: DoctorStats
    summary: str


