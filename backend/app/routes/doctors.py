import logging
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..auth import AuthenticatedUser, get_current_user
from ..db import get_db
from ..domain.appointments import get_doctor_directory, get_doctor_schedule_today, get_doctor_weekly_availability
from ..schemas import DoctorAvailabilityEntry, DoctorDirectoryEntry, DoctorScheduleEntry

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("", response_model=List[DoctorDirectoryEntry])
def doctor_directory(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user()),
):
    return get_doctor_directory(db)


@router.get("/me/schedule/today", response_model=List[DoctorScheduleEntry])
def my_schedule_today(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user(required_role="doctor")),
):
    return get_doctor_schedule_today(db, current_user.id)


@router.get("/me/availability", response_model=List[DoctorAvailabilityEntry])
def my_availability(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user(required_role="doctor")),
):
    return get_doctor_weekly_availability(db, current_user.id)
