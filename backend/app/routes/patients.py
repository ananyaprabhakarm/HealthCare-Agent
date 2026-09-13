import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import AuthenticatedUser, get_current_user
from ..db import get_db
from ..domain.appointments import cancel_patient_appointment, get_patient_appointments
from ..schemas import PatientAppointmentSummary

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/me/appointments", response_model=List[PatientAppointmentSummary])
def my_appointments(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user(required_role="patient")),
):
    return get_patient_appointments(db, current_user.id)


@router.patch("/me/appointments/{appointment_id}/cancel", response_model=PatientAppointmentSummary)
def cancel_appointment(
    appointment_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user(required_role="patient")),
):
    try:
        result = cancel_patient_appointment(db, current_user.id, appointment_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if result is None:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return result
