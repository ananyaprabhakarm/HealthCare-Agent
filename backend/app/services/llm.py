import os
from typing import Any, Dict, List


class LLMClient:
    def __init__(self):
        self.model = os.getenv("LLM_MODEL", "mock-llm")
        self.api_key = os.getenv("LLM_API_KEY", "")

    def chat(self, messages: List[Dict[str, str]], tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {"content": "This is a placeholder response from the assistant.", "tool_calls": []}


