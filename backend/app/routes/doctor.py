import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..schemas import DoctorStatsRequest, DoctorStatsResponse
from ..mcp.tools import get_appointment_stats, send_doctor_notification
from ..services.notification import NotificationClient


logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/summary", response_model=DoctorStatsResponse)
def doctor_summary(payload: DoctorStatsRequest, db: Session = Depends(get_db)):
    logger.info(f"📊 Doctor summary request: email={payload.doctor_email}, timeframe={payload.timeframe}")
    if not payload.timeframe:
        raise HTTPException(status_code=400, detail="Timeframe required")
    stats = get_appointment_stats(db, payload)
    notification_client = NotificationClient()
    send_doctor_notification(db, payload.doctor_email, "in_app", stats.summary, notification_client)
    logger.info(f"✓ Doctor summary completed for {payload.doctor_email}")
    return stats


