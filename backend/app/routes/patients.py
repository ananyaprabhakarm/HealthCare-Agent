import logging
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..auth import AuthenticatedUser, get_current_user
from ..db import get_db
from ..domain.appointments import get_patient_appointments
from ..schemas import PatientAppointmentSummary

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/me/appointments", response_model=List[PatientAppointmentSummary])
def my_appointments(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user(required_role="patient")),
):
    return get_patient_appointments(db, current_user.id)
