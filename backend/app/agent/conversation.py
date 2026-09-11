import json
from typing import List

from ..models import ChatMessage
from ..services.llm import ChatTurn, ToolCall


def build_turns_from_history(history: List[ChatMessage]) -> List[ChatTurn]:
    turns: List[ChatTurn] = []
    for message in history:
        if message.sender == "user":
            turns.append(ChatTurn(role="user", text=message.content))
        elif message.sender == "assistant":
            turns.append(ChatTurn(role="assistant", text=message.content))
        elif message.sender == "tool":
            call_info = message.tool_calls or {}
            tool_name = call_info.get("name", "")
            arguments = call_info.get("arguments", {})
            call_id = call_info.get("id", "")
            try:
                tool_response = json.loads(message.content)
            except (TypeError, ValueError):
                tool_response = {"raw": message.content}
            turns.append(ChatTurn(
                role="assistant",
                tool_calls=[ToolCall(id=call_id, name=tool_name, arguments=arguments)],
            ))
            turns.append(ChatTurn(role="tool_result", tool_name=tool_name, tool_response=tool_response))
    return turns
