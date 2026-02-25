import os
import json
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List
from dotenv import load_dotenv

load_dotenv()

try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


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

    def _format_tools_for_gemini(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        function_declarations = []
        for tool in tools:
            tool_name = tool.get("name", "")
            if tool_name == "get_doctor_availability":
                function_declarations.append({
                    "name": "get_doctor_availability",
                    "description": "Get available appointment slots for a doctor on a specific date",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "doctor_name": {"type": "string", "description": "Name of the doctor"},
                            "date_str": {"type": "string", "description": "Date in ISO format (YYYY-MM-DD)"},
                            "preferred_slot": {"type": "string", "description": "Preferred time slot: 'morning' or 'afternoon'", "enum": ["morning", "afternoon"]}
                        },
                        "required": ["doctor_name", "date_str"]
                    }
                })
            elif tool_name == "create_appointment":
                function_declarations.append({
                    "name": "create_appointment",
                    "description": "Create a new appointment for a patient with a doctor",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "doctor_name": {"type": "string", "description": "Name of the doctor"},
                            "patient_email": {"type": "string", "description": "Email of the patient"},
                            "patient_name": {"type": "string", "description": "Name of the patient"},
                            "start": {"type": "string", "description": "Start datetime in ISO format"},
                            "end": {"type": "string", "description": "End datetime in ISO format"},
                            "reason": {"type": "string", "description": "Reason for the appointment"},
                            "symptoms": {
                                "type": "array",
                                "description": "Patient symptoms",
                                "items": {"type": "string"}
                            }
                        },
                        "required": ["doctor_name", "patient_email", "start", "end"]
                    }
                })
            elif tool_name == "get_appointment_stats":
                function_declarations.append({
                    "name": "get_appointment_stats",
                    "description": "Get appointment statistics for a doctor",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "doctor_email": {"type": "string", "description": "Email of the doctor"},
                            "timeframe": {"type": "string", "description": "Timeframe: 'today', 'yesterday', or 'tomorrow'"},
                            "symptom_filter": {"type": "string", "description": "Filter by symptom keyword"}
                        },
                        "required": ["doctor_email", "timeframe"]
                    }
                })
        return function_declarations

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

    def _build_gemini_contents(self, messages: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        contents: List[Dict[str, Any]] = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "assistant":
                role = "model"
            elif role == "tool":
                role = "user"
                if not isinstance(content, str):
                    content = json.dumps(content)
                content = f"Tool result: {content}"
            contents.append({"role": role, "parts": [{"text": content}]})
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

    def chat(self, messages: List[Dict[str, str]], tools: List[Dict[str, Any]], db=None) -> Dict[str, Any]:
        if not self.enabled:
            last_user_message = next((m.get("content", "") for m in reversed(messages) if m.get("role") == "user"), "")
            if tools and ("appointment" in last_user_message.lower() or "book" in last_user_message.lower() or "availability" in last_user_message.lower()):
                fallback_result = self._simple_fallback_parser(last_user_message)
                if fallback_result.get("tool_calls"):
                    return fallback_result
            return {"content": "I'd be happy to help! However, the LLM service is not configured. Please set LLM_API_KEY in your environment variables to enable full functionality. For basic appointment checking, please format your request like: 'Check Dr. Ahuja's availability for tomorrow morning'.", "tool_calls": []}
        
        formatted_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            if role == "user":
                formatted_messages.append({"role": "user", "content": msg.get("content", "")})
            elif role == "assistant":
                formatted_messages.append({"role": "assistant", "content": msg.get("content", "")})
            elif role == "tool":
                tool_content = msg.get("content", "")
                tool_call_id = msg.get("tool_call_id", "")
                if isinstance(tool_content, str):
                    try:
                        tool_content = json.loads(tool_content)
                    except:
                        pass
                formatted_messages.append({
                    "role": "tool",
                    "content": json.dumps(tool_content) if not isinstance(tool_content, str) else tool_content,
                    "tool_call_id": tool_call_id
                })
        
        gemini_tools = self._format_tools_for_gemini(tools) if tools else []
        
        try:
            if GEMINI_AVAILABLE and self.enabled and self.client:
                try:
                    system_instruction = "You are a helpful assistant for a doctor appointment system. Use the provided tools to help users book appointments and check availability."

                    contents = self._build_gemini_contents(formatted_messages)

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
                    last_user_message = next((m.get("content", "") for m in reversed(formatted_messages) if m.get("role") == "user"), "")
                    if tools and last_user_message:
                        fallback_result = self._simple_fallback_parser(last_user_message)
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


