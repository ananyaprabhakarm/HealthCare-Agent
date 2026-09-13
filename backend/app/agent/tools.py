from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Set

from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..domain import appointments as domain
from ..schemas import (
    AppointmentCreatePayload,
    AppointmentResponse,
    AvailabilityResponse,
    DoctorStatsRequest,
    DoctorStatsResponse,
)
from ..services.calendar import CalendarClient
from ..services.email import EmailClient
from ..services.notification import NotificationClient


@dataclass
class ToolContext:
    db: Session
    calendar_client: CalendarClient
    email_client: EmailClient
    notification_client: NotificationClient
    user_email: Optional[str] = None
    user_name: Optional[str] = None


@dataclass
class Tool:
    name: str
    description: str
    parameters: Dict[str, Any]
    roles: Set[str]
    handler: Callable[[ToolContext, Dict[str, Any]], BaseModel]


def _handle_get_doctor_availability(ctx: ToolContext, arguments: Dict[str, Any]) -> AvailabilityResponse:
    return domain.get_doctor_availability(
        ctx.db,
        arguments.get("doctor_name", ""),
        arguments.get("date_str", ""),
        arguments.get("preferred_slot"),
    )


def _handle_create_appointment(ctx: ToolContext, arguments: Dict[str, Any]) -> AppointmentResponse:
    # patient_email/patient_name always come from the authenticated session,
    # never from LLM-supplied arguments — a patient can only ever book for themselves.
    payload = AppointmentCreatePayload(
        doctor_name=arguments.get("doctor_name", ""),
        patient_email=ctx.user_email or "",
        patient_name=ctx.user_name or "",
        start=arguments.get("start", ""),
        end=arguments.get("end", ""),
        reason=arguments.get("reason"),
        symptoms=arguments.get("symptoms"),
    )
    return domain.create_appointment(ctx.db, payload, ctx.calendar_client, ctx.email_client)


def _handle_get_appointment_stats(ctx: ToolContext, arguments: Dict[str, Any]) -> DoctorStatsResponse:
    # doctor_email always comes from the authenticated session — a doctor can
    # only ever see their own stats, regardless of what the LLM is asked for.
    request = DoctorStatsRequest(
        doctor_email=ctx.user_email or "",
        timeframe=arguments.get("timeframe", "today"),
        symptom_filter=arguments.get("symptom_filter"),
    )
    return domain.get_appointment_stats(ctx.db, request)


TOOLS: Dict[str, Tool] = {
    tool.name: tool
    for tool in [
        Tool(
            name="get_doctor_availability",
            description="Get available appointment slots for a doctor on a specific date",
            parameters={
                "type": "object",
                "properties": {
                    "doctor_name": {"type": "string", "description": "Name of the doctor"},
                    "date_str": {"type": "string", "description": "Date in ISO format (YYYY-MM-DD)"},
                    "preferred_slot": {
                        "type": "string",
                        "description": "Preferred time slot: 'morning' or 'afternoon'",
                        "enum": ["morning", "afternoon"],
                    },
                },
                "required": ["doctor_name", "date_str"],
            },
            roles={"patient"},
            handler=_handle_get_doctor_availability,
        ),
        Tool(
            name="create_appointment",
            description="Create a new appointment for the current patient with a doctor",
            parameters={
                "type": "object",
                "properties": {
                    "doctor_name": {"type": "string", "description": "Name of the doctor"},
                    "start": {"type": "string", "description": "Start datetime in ISO format"},
                    "end": {"type": "string", "description": "End datetime in ISO format"},
                    "reason": {"type": "string", "description": "Reason for the appointment"},
                    "symptoms": {
                        "type": "array",
                        "description": "Patient symptoms",
                        "items": {"type": "string"},
                    },
                },
                "required": ["doctor_name", "start", "end"],
            },
            roles={"patient"},
            handler=_handle_create_appointment,
        ),
        Tool(
            name="get_appointment_stats",
            description="Get appointment statistics for the current doctor",
            parameters={
                "type": "object",
                "properties": {
                    "timeframe": {"type": "string", "description": "Timeframe: 'today', 'yesterday', or 'tomorrow'"},
                    "symptom_filter": {"type": "string", "description": "Filter by symptom keyword"},
                },
                "required": ["timeframe"],
            },
            roles={"doctor"},
            handler=_handle_get_appointment_stats,
        ),
    ]
}


def tools_for_role(role: str) -> List[Tool]:
    return [tool for tool in TOOLS.values() if role in tool.roles]
