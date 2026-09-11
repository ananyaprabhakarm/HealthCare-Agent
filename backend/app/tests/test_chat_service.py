import json
from datetime import datetime, time, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.agent.chat_service import run_chat_agent
from app.agent.tools import ToolContext
from app.db import Base
from app.models import ChatMessage, ChatSession, Doctor, DoctorAvailability


class FakeLLM:
    """Replays a scripted sequence of chat() results instead of calling Gemini."""

    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def chat(self, turns, tools):
        self.calls.append(turns)
        return self.responses[len(self.calls) - 1]


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture()
def doctor(db_session):
    doc = Doctor(name="Dr. Ahuja", email="ahuja@example.com")
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)
    weekday = str(datetime.now(timezone.utc).date().weekday())
    db_session.add(DoctorAvailability(
        doctor_id=doc.id,
        weekday=weekday,
        start_time=time(9, 0),
        end_time=time(17, 0),
        slot_duration_minutes="30",
    ))
    db_session.commit()
    return doc


def test_tool_result_containing_uuid_is_json_serializable(db_session, doctor, monkeypatch):
    """Regression test: tool results (e.g. AvailabilityResponse.doctor_id) contain UUID
    and datetime fields. Persisting them as a ChatMessage row previously crashed with
    `TypeError: Object of type UUID is not JSON serializable` on every successful tool call.
    """
    session = ChatSession(user_role="patient")
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)
    db_session.add(ChatMessage(session_id=session.id, sender="user", content="check availability today"))
    db_session.commit()

    today = datetime.now(timezone.utc).date().isoformat()
    fake_llm = FakeLLM([
        {
            "content": "",
            "tool_calls": [{
                "id": "call-1",
                "function": {
                    "name": "get_doctor_availability",
                    "arguments": json.dumps({"doctor_name": "Dr. Ahuja", "date_str": today}),
                },
            }],
        },
        {"content": "Here are the open slots.", "tool_calls": []},
    ])
    monkeypatch.setattr("app.agent.chat_service.LLMClient", lambda: fake_llm)

    context = ToolContext(db=db_session, calendar_client=None, email_client=None, notification_client=None)
    final_response = run_chat_agent(db_session, session, "patient", context)

    assert final_response == "Here are the open slots."
    tool_message = db_session.query(ChatMessage).filter(ChatMessage.sender == "tool").one()
    stored = json.loads(tool_message.content)
    assert stored["success"] is True
    assert isinstance(stored["result"]["doctor_id"], str)
