import os
import json
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()


class LLMClient:
    def __init__(self):
        self.model = os.getenv("LLM_MODEL", "gemini-1.5-flash")
        self.api_key = os.getenv("LLM_API_KEY")
        self.enabled = bool(self.api_key)

        if self.enabled:
            self.client = genai.Client(api_key=self.api_key)
        else:
            print("LLM_API_KEY not set. Gemini disabled.")

    # -----------------------------
    # TOOL FORMAT (NEW SDK STYLE)
    # -----------------------------
    def _format_tools(self, tools: List[Dict[str, Any]]) -> List[types.Tool]:
        function_declarations = []

        for tool in tools:
            name = tool.get("name")

            if name == "get_doctor_availability":
                function_declarations.append(
                    types.FunctionDeclaration(
                        name="get_doctor_availability",
                        description="Get available appointment slots for a doctor on a specific date",
                        parameters={
                            "type": "object",
                            "properties": {
                                "doctor_name": {"type": "string"},
                                "date_str": {"type": "string"},
                                "preferred_slot": {
                                    "type": "string",
                                    "enum": ["morning", "afternoon"],
                                },
                            },
                            "required": ["doctor_name", "date_str"],
                        },
                    )
                )

        if function_declarations:
            return [types.Tool(function_declarations=function_declarations)]

        return []

    # -----------------------------
    # MAIN CHAT METHOD (NEW SDK)
    # -----------------------------
    def chat(self, messages: List[Dict[str, str]], tools: List[Dict[str, Any]],db=None) -> Dict[str, Any]:

        if not self.enabled:
            return {
                "content": "Gemini not configured.",
                "tool_calls": []
            }

        try:
            # Convert chat history
            contents = []

            for msg in messages:
                role = msg.get("role")
                text = msg.get("content", "")

                if role == "user":
                    contents.append(
                        types.Content(
                            role="user",
                            parts=[types.Part(text=text)]
                        )
                    )
                elif role == "assistant":
                    contents.append(
                        types.Content(
                            role="model",
                            parts=[types.Part(text=text)]
                        )
                    )

            formatted_tools = self._format_tools(tools)

            response = self.client.models.generate_content(
                model=self.model,
                contents=contents,
                tools=formatted_tools if formatted_tools else None,
                tool_config=types.ToolConfig(
                    function_calling_config=types.FunctionCallingConfig(
                        mode="AUTO"
                    )
                ) if formatted_tools else None,
            )

            content = ""
            tool_calls = []

            if response.candidates:
                candidate = response.candidates[0]

                if candidate.content and candidate.content.parts:
                    for part in candidate.content.parts:

                        # Normal text response
                        if part.text:
                            content += part.text

                        # Function call
                        if part.function_call:
                            tool_calls.append({
                                "id": "gemini-0",
                                "function": {
                                    "name": part.function_call.name,
                                    "arguments": json.dumps(
                                        part.function_call.args
                                    )
                                }
                            })

            return {
                "content": content,
                "tool_calls": tool_calls
            }

        except Exception as e:
            return {
                "content": f"Gemini API Error: {str(e)}",
                "tool_calls": []
            }