import os
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass
class ChatTurn:
    """One turn of conversation history, in a provider-agnostic shape.

    role is one of:
      - "user": a plain user message (`text`)
      - "assistant": an assistant turn, with `text` and/or `tool_calls`
      - "tool_result": the result of executing one tool call (`tool_name`, `tool_response`)
    """

    role: str
    text: str = ""
    tool_calls: List[ToolCall] = field(default_factory=list)
    tool_name: Optional[str] = None
    tool_response: Optional[Dict[str, Any]] = None


class LLMClient:
    def __init__(self):
        self.model = os.getenv("LLM_MODEL", "gemini-2.5-flash")
        self.api_key = os.getenv("LLM_API_KEY", "GEMINI_API_KEY")
        self.enabled = bool(self.api_key and self.api_key != "GEMINI_API_KEY")
        self.client = None

        if GEMINI_AVAILABLE and self.enabled:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                print(f"Failed to initialize google.genai client: {e}")
                self.enabled = False
        else:
            if not GEMINI_AVAILABLE:
                print("Warning: google-genai not installed. Install with: pip install google-genai")
            self.enabled = False

    def _format_tools_for_gemini(self, tools: List[Any]) -> List[Dict[str, Any]]:
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            }
            for tool in tools
        ]

    def _simple_fallback_parser(self, user_message: str) -> Dict[str, Any]:
        user_lower = user_message.lower()
        doctor_match = re.search(r'dr\.?\s*(\w+)', user_lower, re.IGNORECASE)
        doctor_name = doctor_match.group(1).title() if doctor_match else None

        date_keywords = {
            "today": datetime.now().date(),
            "tomorrow": (datetime.now() + timedelta(days=1)).date(),
            "yesterday": (datetime.now() - timedelta(days=1)).date(),
        }
        date_str = None
        for keyword, date_obj in date_keywords.items():
            if keyword in user_lower:
                date_str = date_obj.isoformat()
                break

        if not date_str:
            weekday_map = {
                "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
                "friday": 4, "saturday": 5, "sunday": 6
            }
            for day, offset in weekday_map.items():
                if day in user_lower:
                    days_ahead = offset - datetime.now().weekday()
                    if days_ahead <= 0:
                        days_ahead += 7
                    date_str = (datetime.now() + timedelta(days=days_ahead)).date().isoformat()
                    break

        preferred_slot = None
        if "morning" in user_lower:
            preferred_slot = "morning"
        elif "afternoon" in user_lower:
            preferred_slot = "afternoon"

        if doctor_name and date_str and ("availability" in user_lower or "available" in user_lower or "book" in user_lower or "appointment" in user_lower):
            return {
                "content": "",
                "tool_calls": [{
                    "id": "fallback-1",
                    "function": {
                        "name": "get_doctor_availability",
                        "arguments": json.dumps({
                            "doctor_name": f"Dr. {doctor_name}",
                            "date_str": date_str,
                            "preferred_slot": preferred_slot
                        })
                    }
                }]
            }

        return {
            "content": "I can help you book appointments! Please provide:\n- Doctor's name (e.g., Dr. Ahuja)\n- Date (e.g., tomorrow, Friday)\n- Preferred time (morning or afternoon)\n\nExample: 'I want to book an appointment with Dr. Ahuja tomorrow morning'",
            "tool_calls": []
        }

    def _build_gemini_contents(self, turns: List[ChatTurn]) -> List["types.Content"]:
        contents: List[types.Content] = []
        for turn in turns:
            if turn.role == "user":
                contents.append(types.Content(role="user", parts=[types.Part.from_text(text=turn.text or "")]))
            elif turn.role == "assistant":
                parts = []
                if turn.text:
                    parts.append(types.Part.from_text(text=turn.text))
                for call in turn.tool_calls:
                    parts.append(types.Part.from_function_call(name=call.name, args=call.arguments))
                if parts:
                    contents.append(types.Content(role="model", parts=parts))
            elif turn.role == "tool_result":
                contents.append(types.Content(
                    role="user",
                    parts=[types.Part.from_function_response(
                        name=turn.tool_name or "",
                        response=turn.tool_response or {},
                    )],
                ))
        return contents

    def _extract_text_and_tool_calls(self, response: Any) -> Dict[str, Any]:
        content = ""
        tool_calls: List[Dict[str, Any]] = []

        direct_text = getattr(response, "text", None)
        if isinstance(direct_text, str) and direct_text.strip():
            content = direct_text

        function_calls = getattr(response, "function_calls", None)
        if function_calls:
            for idx, call in enumerate(function_calls):
                args = getattr(call, "args", {}) or {}
                tool_calls.append({
                    "id": f"gemini-{idx}",
                    "function": {
                        "name": getattr(call, "name", ""),
                        "arguments": json.dumps(args)
                    }
                })

        if not content:
            candidates = getattr(response, "candidates", None) or []
            for candidate in candidates:
                candidate_content = getattr(candidate, "content", None)
                parts = getattr(candidate_content, "parts", None) or []
                for part in parts:
                    part_text = getattr(part, "text", None)
                    if part_text:
                        content += part_text
                    part_func = getattr(part, "function_call", None)
                    if part_func:
                        args = getattr(part_func, "args", {}) or {}
                        tool_calls.append({
                            "id": f"gemini-{len(tool_calls)}",
                            "function": {
                                "name": getattr(part_func, "name", ""),
                                "arguments": json.dumps(args)
                            }
                        })

        return {"content": content, "tool_calls": tool_calls}

    def chat(self, turns: List[ChatTurn], tools: List[Any]) -> Dict[str, Any]:
        last_user_text = next((t.text for t in reversed(turns) if t.role == "user" and t.text), "")

        if not self.enabled:
            if tools and last_user_text and ("appointment" in last_user_text.lower() or "book" in last_user_text.lower() or "availability" in last_user_text.lower()):
                fallback_result = self._simple_fallback_parser(last_user_text)
                if fallback_result.get("tool_calls"):
                    return fallback_result
            return {"content": "I'd be happy to help! However, the LLM service is not configured. Please set LLM_API_KEY in your environment variables to enable full functionality. For basic appointment checking, please format your request like: 'Check Dr. Ahuja's availability for tomorrow morning'.", "tool_calls": []}

        gemini_tools = self._format_tools_for_gemini(tools) if tools else []

        try:
            if GEMINI_AVAILABLE and self.enabled and self.client:
                try:
                    system_instruction = "You are a helpful assistant for a doctor appointment system. Use the provided tools to help users book appointments and check availability."

                    contents = self._build_gemini_contents(turns)

                    config_kwargs: Dict[str, Any] = {
                        "system_instruction": system_instruction,
                        "temperature": 0.2,
                    }

                    if gemini_tools:
                        config_kwargs["tools"] = [{"function_declarations": gemini_tools}]

                    response = self.client.models.generate_content(
                        model=self.model,
                        contents=contents,
                        config=types.GenerateContentConfig(**config_kwargs),
                    )

                    return self._extract_text_and_tool_calls(response)
                except Exception as api_error:
                    import traceback
                    error_msg = str(api_error)
                    print(f"Gemini API error: {error_msg}")
                    print(traceback.format_exc())
                    # Fallback to simple parser if API fails
                    if tools and last_user_text:
                        fallback_result = self._simple_fallback_parser(last_user_text)
                        if fallback_result.get("tool_calls"):
                            return fallback_result
                    return {"content": f"API Error: {error_msg}. Using fallback response.", "tool_calls": []}
            else:
                return {"content": "Gemini API is not properly configured. Please check your LLM_API_KEY settings and ensure google-genai is installed.", "tool_calls": []}
        except Exception as e:
            import traceback
            error_msg = str(e)
            print(f"LLM API error: {error_msg}")
            print(traceback.format_exc())
            return {"content": f"I encountered an error while processing your request: {error_msg}. Please check your API configuration.", "tool_calls": []}
