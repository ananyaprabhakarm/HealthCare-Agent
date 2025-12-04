from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..schemas import DoctorStatsRequest, DoctorStatsResponse
from ..mcp.tools import get_appointment_stats, send_doctor_notification
from ..services.notification import NotificationClient


router = APIRouter()


@router.post("/summary", response_model=DoctorStatsResponse)
def doctor_summary(payload: DoctorStatsRequest, db: Session = Depends(get_db)):
    if not payload.timeframe:
        raise HTTPException(status_code=400, detail="Timeframe required")
    stats = get_appointment_stats(db, payload)
    notification_client = NotificationClient()
    send_doctor_notification(db, payload.doctor_email, "in_app", stats.summary, notification_client)
    return stats


