from typing import List
from uuid import UUID
import json
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import ChatSession, ChatMessage
from ..schemas import ChatRequest, ChatResponse, ChatMessageSchema, AppointmentCreatePayload
from ..services.llm import LLMClient
from ..mcp.tools import get_doctor_availability, create_appointment
from ..services.calendar import CalendarClient
from ..services.email import EmailClient


logger = logging.getLogger(__name__)
router = APIRouter()


def execute_tool_call(tool_name: str, arguments: dict, db: Session, calendar_client: CalendarClient, email_client: EmailClient) -> dict:
    logger.info(f"🔧 Executing tool: {tool_name} with arguments: {arguments}")
    try:
        if tool_name == "get_doctor_availability":
            result = get_doctor_availability(
                db,
                arguments.get("doctor_name", ""),
                arguments.get("date_str", ""),
                arguments.get("preferred_slot")
            )
            return {"success": True, "result": result.dict()}
        elif tool_name == "create_appointment":
            payload = AppointmentCreatePayload(
                doctor_name=arguments.get("doctor_name", ""),
                patient_email=arguments.get("patient_email", ""),
                patient_name=arguments.get("patient_name", ""),
                start=datetime.fromisoformat(arguments.get("start", "")),
                end=datetime.fromisoformat(arguments.get("end", "")),
                reason=arguments.get("reason"),
                symptoms=arguments.get("symptoms")
            )
            result = create_appointment(db, payload, calendar_client, email_client)
            return {"success": True, "result": result.dict()}
        else:
            logger.warning(f"⚠️ Unknown tool requested: {tool_name}")
            return {"success": False, "error": f"Unknown tool: {tool_name}"}
    except Exception as e:
        logger.error(f"❌ Tool execution failed for {tool_name}: {str(e)}", exc_info=True)
        return {"success": False, "error": str(e)}


@router.post("/patient", response_model=ChatResponse)
def chat_patient(payload: ChatRequest, db: Session = Depends(get_db)):
    logger.info(f"👤 Patient chat request: session_id={payload.session_id}, message_length={len(payload.message) if payload.message else 0}")
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
        logger.info(f"📝 Created new patient session: {session.id}")
    user_message = ChatMessage(session_id=session.id, sender="user", content=payload.message)
    db.add(user_message)
    db.commit()
    llm = LLMClient()
    calendar_client = CalendarClient()
    email_client = EmailClient()
    tools = [
        {"name": "get_doctor_availability"},
        {"name": "create_appointment"},
    ]
    messages_context: List[dict] = []
    history = db.query(ChatMessage).filter(ChatMessage.session_id == session.id).order_by(ChatMessage.created_at.asc()).all()
    for m in history:
        if m.sender == "tool":
            messages_context.append({"role": "tool", "content": m.content, "tool_call_id": m.tool_calls.get("id", "") if m.tool_calls else ""})
        else:
            messages_context.append({"role": m.sender, "content": m.content})
    max_iterations = 5
    iteration = 0
    final_response = None
    llm_result = None
    while iteration < max_iterations:
        logger.debug(f"🔄 Patient chat iteration {iteration + 1}/{max_iterations}")
        llm_result = llm.chat(messages_context, tools, db)
        tool_calls = llm_result.get("tool_calls", [])
        content = llm_result.get("content", "")
        if not tool_calls:
            final_response = content if content else "I'm here to help. Could you please rephrase your request?"
            logger.debug("✓ Patient chat completed without tool calls")
            break
        for tool_call in tool_calls:
            tool_name = tool_call.get("function", {}).get("name", "")
            arguments_str = tool_call.get("function", {}).get("arguments", "{}")
            try:
                arguments = json.loads(arguments_str) if isinstance(arguments_str, str) else arguments_str
            except json.JSONDecodeError:
                arguments = {}
            tool_result = execute_tool_call(tool_name, arguments, db, calendar_client, email_client)
            tool_message = ChatMessage(
                session_id=session.id,
                sender="tool",
                content=json.dumps(tool_result),
                tool_calls={"id": tool_call.get("id", ""), "name": tool_name, "arguments": arguments}
            )
            db.add(tool_message)
            db.commit()
            messages_context.append({
                "role": "tool",
                "content": json.dumps(tool_result),
                "tool_call_id": tool_call.get("id", "")
            })
        if content:
            messages_context.append({
                "role": "assistant",
                "content": content
            })
        iteration += 1
    if final_response is None:
        final_response = llm_result.get("content", "") if llm_result else "I'm processing your request. Please wait a moment."
        if not final_response:
            final_response = "I apologize, but I'm having trouble processing your request. Please try again or rephrase your question."
    assistant_message = ChatMessage(session_id=session.id, sender="assistant", content=final_response)
    db.add(assistant_message)
    db.commit()
    db.refresh(assistant_message)
    messages = db.query(ChatMessage).filter(ChatMessage.session_id == session.id).order_by(ChatMessage.created_at.asc()).all()
    logger.info(f"✓ Patient chat completed: session_id={session.id}, message_count={len(messages)}")
    return ChatResponse(session_id=session.id, messages=[ChatMessageSchema.model_validate(m) for m in messages])
def chat_doctor(payload: ChatRequest, db: Session = Depends(get_db)):
    logger.info(f"👨‍⚕️ Doctor chat request: session_id={payload.session_id}, message_length={len(payload.message) if payload.message else 0}")
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
        logger.info(f"📝 Created new doctor session: {session.id}")
    user_message = ChatMessage(session_id=session.id, sender="user", content=payload.message)
    db.add(user_message)
    db.commit()
    llm = LLMClient()
    from ..mcp.tools import get_appointment_stats
    from ..schemas import DoctorStatsRequest
    from ..services.notification import NotificationClient
    tools = [
        {"name": "get_appointment_stats"},
    ]
    messages_context: List[dict] = []
    history = db.query(ChatMessage).filter(ChatMessage.session_id == session.id).order_by(ChatMessage.created_at.asc()).all()
    for m in history:
        if m.sender == "tool":
            messages_context.append({"role": "tool", "content": m.content, "tool_call_id": m.tool_calls.get("id", "") if m.tool_calls else ""})
        else:
            messages_context.append({"role": m.sender, "content": m.content})
    max_iterations = 5
    iteration = 0
    final_response = None
    llm_result = None
    while iteration < max_iterations:
        logger.debug(f"🔄 Doctor chat iteration {iteration + 1}/{max_iterations}")
        llm_result = llm.chat(messages_context, tools, db)
        tool_calls = llm_result.get("tool_calls", [])
        content = llm_result.get("content", "")
        if not tool_calls:
            final_response = content if content else "I'm here to help. Could you please rephrase your request?"
            logger.debug("✓ Doctor chat completed without tool calls")
            break
        notification_client = NotificationClient()
        for tool_call in tool_calls:
            tool_name = tool_call.get("function", {}).get("name", "")
            arguments_str = tool_call.get("function", {}).get("arguments", "{}")
            try:
                arguments = json.loads(arguments_str) if isinstance(arguments_str, str) else arguments_str
            except json.JSONDecodeError:
                arguments = {}
            if tool_name == "get_appointment_stats":
                try:
                    stats_request = DoctorStatsRequest(
                        doctor_email=arguments.get("doctor_email", payload.user_email or ""),
                        timeframe=arguments.get("timeframe", "today"),
                        symptom_filter=arguments.get("symptom_filter")
                    )
                    result = get_appointment_stats(db, stats_request)
                    tool_result = {"success": True, "result": result.dict()}
                except Exception as e:
                    tool_result = {"success": False, "error": str(e)}
            else:
                tool_result = {"success": False, "error": f"Unknown tool: {tool_name}"}
            tool_message = ChatMessage(
                session_id=session.id,
                sender="tool",
                content=json.dumps(tool_result),
                tool_calls={"id": tool_call.get("id", ""), "name": tool_name, "arguments": arguments}
            )
            db.add(tool_message)
            db.commit()
            messages_context.append({
                "role": "tool",
                "content": json.dumps(tool_result),
                "tool_call_id": tool_call.get("id", "")
            })
        if content:
            messages_context.append({
                "role": "assistant",
                "content": content
            })
        iteration += 1
    if final_response is None:
        final_response = llm_result.get("content", "") if llm_result else "I'm processing your request. Please wait a moment."
        if not final_response:
            final_response = "I apologize, but I'm having trouble processing your request. Please try again or rephrase your question."
    assistant_message = ChatMessage(session_id=session.id, sender="assistant", content=final_response)
    db.add(assistant_message)
    db.commit()
    db.refresh(assistant_message)
    messages = db.query(ChatMessage).filter(ChatMessage.session_id == session.id).order_by(ChatMessage.created_at.asc()).all()
    logger.info(f"✓ Doctor chat completed: session_id={session.id}, message_count={len(messages)}")
    return ChatResponse(session_id=session.id, messages=[ChatMessageSchema.model_validate(m) for m in messages])