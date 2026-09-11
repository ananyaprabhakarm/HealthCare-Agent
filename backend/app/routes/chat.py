import logging
from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..agent.chat_service import run_chat_agent
from ..agent.tools import ToolContext
from ..db import get_db
from ..models import ChatMessage, ChatSession
from ..schemas import ChatRequest, ChatResponse, ChatMessageSchema
from ..services.calendar import CalendarClient
from ..services.email import EmailClient
from ..services.notification import NotificationClient


logger = logging.getLogger(__name__)
router = APIRouter()


def _get_or_create_session(db: Session, session_id: Optional[UUID], role: str) -> ChatSession:
    session: Optional[ChatSession] = None
    if session_id:
        session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        session = ChatSession(user_role=role)
        db.add(session)
        db.commit()
        db.refresh(session)
        logger.info(f"📝 Created new {role} session: {session.id}")
    return session


def _handle_chat(payload: ChatRequest, db: Session, role: str) -> ChatResponse:
    logger.info(f"💬 {role} chat request: session_id={payload.session_id}, message_length={len(payload.message) if payload.message else 0}")
    if not payload.message:
        raise HTTPException(status_code=400, detail="Message required")

    session = _get_or_create_session(db, payload.session_id, role)
    db.add(ChatMessage(session_id=session.id, sender="user", content=payload.message))
    db.commit()

    context = ToolContext(
        db=db,
        calendar_client=CalendarClient(),
        email_client=EmailClient(),
        notification_client=NotificationClient(),
        user_email=payload.user_email,
    )
    run_chat_agent(db, session, role, context)

    messages = db.query(ChatMessage).filter(ChatMessage.session_id == session.id).order_by(ChatMessage.created_at.asc()).all()
    logger.info(f"✓ {role} chat completed: session_id={session.id}, message_count={len(messages)}")
    return ChatResponse(session_id=session.id, messages=[ChatMessageSchema.model_validate(m) for m in messages])


@router.post("/patient", response_model=ChatResponse)
def chat_patient(payload: ChatRequest, db: Session = Depends(get_db)):
    return _handle_chat(payload, db, "patient")


@router.post("/doctor", response_model=ChatResponse)
def chat_doctor(payload: ChatRequest, db: Session = Depends(get_db)):
    return _handle_chat(payload, db, "doctor")
