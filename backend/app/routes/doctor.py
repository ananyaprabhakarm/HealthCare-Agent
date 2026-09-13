import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import AuthenticatedUser, get_current_user
from ..db import get_db
from ..schemas import DoctorStatsRequest, DoctorStatsResponse, DoctorSummaryRequest
from ..domain.appointments import get_appointment_stats, send_doctor_notification
from ..services.notification import NotificationClient


logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/summary", response_model=DoctorStatsResponse)
def doctor_summary(
    payload: DoctorSummaryRequest,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user(required_role="doctor")),
):
    logger.info(f"📊 Doctor summary request: email={current_user.email}, timeframe={payload.timeframe}")
    if not payload.timeframe:
        raise HTTPException(status_code=400, detail="Timeframe required")
    request = DoctorStatsRequest(
        doctor_email=current_user.email,
        timeframe=payload.timeframe,
        symptom_filter=payload.symptom_filter,
    )
    try:
        stats = get_appointment_stats(db, request)
    except ValueError as e:
        logger.warning(f"⚠️ Doctor summary request failed for {current_user.email}: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    notification_client = NotificationClient()
    send_doctor_notification(db, current_user.email, "in_app", stats.summary, notification_client)
    logger.info(f"✓ Doctor summary completed for {current_user.email}")
    return stats
