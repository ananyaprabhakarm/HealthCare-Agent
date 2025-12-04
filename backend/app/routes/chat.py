from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import ChatSession, ChatMessage
from ..schemas import ChatRequest, ChatResponse, ChatMessageSchema
from ..services.llm import LLMClient
from ..mcp.tools import get_doctor_availability, create_appointment
from ..services.calendar import CalendarClient
from ..services.email import EmailClient


router = APIRouter()


@router.post("/patient", response_model=ChatResponse)
def chat_patient(payload: ChatRequest, db: Session = Depends(get_db)):
    if not payload.message:
        raise HTTPException(status_code=400, detail="Message required")
    session: ChatSession | None = None
    if payload.session_id:
        session = db.query(ChatSession).filter(ChatSession.id == payload.session_id).first()
    if not session:
        session = ChatSession(user_role="patient")
        db.add(session)
        db.commit()
        db.refresh(session)
    user_message = ChatMessage(session_id=session.id, sender="user", content=payload.message)
    db.add(user_message)
    db.commit()
    llm = LLMClient()
    tools = [
        {"name": "get_doctor_availability"},
        {"name": "create_appointment"},
    ]
    messages_context: List[dict] = []
    history = db.query(ChatMessage).filter(ChatMessage.session_id == session.id).order_by(ChatMessage.created_at.asc()).all()
    for m in history:
        messages_context.append({"role": m.sender, "content": m.content})
    llm_result = llm.chat(messages_context, tools)
    assistant_text = llm_result.get("content", "")
    assistant_message = ChatMessage(session_id=session.id, sender="assistant", content=assistant_text)
    db.add(assistant_message)
    db.commit()
    db.refresh(assistant_message)
    messages = db.query(ChatMessage).filter(ChatMessage.session_id == session.id).order_by(ChatMessage.created_at.asc()).all()
    return ChatResponse(session_id=session.id, messages=[ChatMessageSchema.from_orm(m) for m in messages])


@router.post("/doctor", response_model=ChatResponse)
def chat_doctor(payload: ChatRequest, db: Session = Depends(get_db)):
    if not payload.message:
        raise HTTPException(status_code=400, detail="Message required")
    session: ChatSession | None = None
    if payload.session_id:
        session = db.query(ChatSession).filter(ChatSession.id == payload.session_id).first()
    if not session:
        session = ChatSession(user_role="doctor")
        db.add(session)
        db.commit()
        db.refresh(session)
    user_message = ChatMessage(session_id=session.id, sender="user", content=payload.message)
    db.add(user_message)
    db.commit()
    llm = LLMClient()
    tools = [
        {"name": "get_appointment_stats"},
    ]
    messages_context: List[dict] = []
    history = db.query(ChatMessage).filter(ChatMessage.session_id == session.id).order_by(ChatMessage.created_at.asc()).all()
    for m in history:
        messages_context.append({"role": m.sender, "content": m.content})
    llm_result = llm.chat(messages_context, tools)
    assistant_text = llm_result.get("content", "")
    assistant_message = ChatMessage(session_id=session.id, sender="assistant", content=assistant_text)
    db.add(assistant_message)
    db.commit()
    db.refresh(assistant_message)
    messages = db.query(ChatMessage).filter(ChatMessage.session_id == session.id).order_by(ChatMessage.created_at.asc()).all()
    return ChatResponse(session_id=session.id, messages=[ChatMessageSchema.from_orm(m) for m in messages])


