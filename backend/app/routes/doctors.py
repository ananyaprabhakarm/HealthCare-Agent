import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import AuthenticatedUser, get_current_user
from ..db import get_db
from ..domain.appointments import (
    create_doctor_availability,
    delete_doctor_availability,
    get_doctor_directory,
    get_doctor_schedule_today,
    get_doctor_weekly_availability,
)
from ..schemas import DoctorAvailabilityCreate, DoctorAvailabilityEntry, DoctorDirectoryEntry, DoctorScheduleEntry

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


@router.post("/me/availability", response_model=DoctorAvailabilityEntry, status_code=201)
def add_availability(
    payload: DoctorAvailabilityCreate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user(required_role="doctor")),
):
    try:
        return create_doctor_availability(db, current_user.id, payload.day_of_week, payload.start_time, payload.end_time)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/me/availability/{availability_id}", status_code=204)
def remove_availability(
    availability_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user(required_role="doctor")),
):
    deleted = delete_doctor_availability(db, current_user.id, availability_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Availability slot not found")
