import json
import logging
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from ..models import ChatMessage, ChatSession
from ..services.llm import ChatTurn, LLMClient, ToolCall
from .conversation import build_turns_from_history
from .tools import TOOLS, ToolContext, tools_for_role

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 5
NO_TOOL_CALL_MESSAGE = "I'm here to help. Could you please rephrase your request?"
NO_RESPONSE_MESSAGE = "I apologize, but I'm having trouble processing your request. Please try again or rephrase your question."


def run_chat_agent(db: Session, session: ChatSession, role: str, context: ToolContext) -> str:
    llm = LLMClient()
    tools = tools_for_role(role)

    history = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
    turns: List[ChatTurn] = build_turns_from_history(history)

    final_response = None
    last_content = ""
    for iteration in range(MAX_ITERATIONS):
        logger.debug(f"🔄 {role} chat iteration {iteration + 1}/{MAX_ITERATIONS}")
        result = llm.chat(turns, tools)
        last_content = result.get("content", "")
        raw_tool_calls = result.get("tool_calls", [])

        if not raw_tool_calls:
            final_response = last_content or NO_TOOL_CALL_MESSAGE
            logger.debug(f"✓ {role} chat completed without tool calls")
            break

        assistant_calls: List[ToolCall] = []
        tool_result_turns: List[ChatTurn] = []
        for raw_call in raw_tool_calls:
            call_id = raw_call.get("id", "")
            tool_name = raw_call.get("function", {}).get("name", "")
            arguments_str = raw_call.get("function", {}).get("arguments", "{}")
            try:
                arguments = json.loads(arguments_str) if isinstance(arguments_str, str) else arguments_str
            except json.JSONDecodeError:
                arguments = {}

            tool_result = _execute_tool(tool_name, arguments, role, context)

            db.add(ChatMessage(
                session_id=session.id,
                sender="tool",
                content=json.dumps(tool_result),
                tool_calls={"id": call_id, "name": tool_name, "arguments": arguments},
            ))
            db.commit()

            assistant_calls.append(ToolCall(id=call_id, name=tool_name, arguments=arguments))
            tool_result_turns.append(ChatTurn(role="tool_result", tool_name=tool_name, tool_response=tool_result))

        turns.append(ChatTurn(role="assistant", text=last_content, tool_calls=assistant_calls))
        turns.extend(tool_result_turns)

    if final_response is None:
        final_response = last_content or NO_RESPONSE_MESSAGE

    assistant_message = ChatMessage(session_id=session.id, sender="assistant", content=final_response)
    db.add(assistant_message)
    db.commit()
    db.refresh(assistant_message)
    logger.info(f"✓ {role} chat completed: session_id={session.id}")
    return final_response


def _execute_tool(tool_name: str, arguments: Dict[str, Any], role: str, context: ToolContext) -> Dict[str, Any]:
    logger.info(f"🔧 Executing tool: {tool_name} with arguments: {arguments}")
    tool = TOOLS.get(tool_name)
    if not tool:
        logger.warning(f"⚠️ Unknown tool requested: {tool_name}")
        return {"success": False, "error": f"Unknown tool: {tool_name}"}
    if role not in tool.roles:
        logger.warning(f"⚠️ Tool {tool_name} is not available for role {role}")
        return {"success": False, "error": f"Tool {tool_name} is not available"}
    try:
        result = tool.handler(context, arguments)
        return {"success": True, "result": result.model_dump(mode="json")}
    except Exception as e:
        logger.error(f"❌ Tool execution failed for {tool_name}: {str(e)}", exc_info=True)
        return {"success": False, "error": str(e)}
