"""Advanced AI Agent Orchestrator."""
import json
import logging
from typing import Any

from app.web_mvp import llm, store
from app.web_mvp.tools import get_all_tool_definitions, execute_tool

logger = logging.getLogger(__name__)

MAX_STEPS = 4

AGENT_SYSTEM_PROMPT = """You are the RGMCET AI Campus Assistant, an advanced AI agent.
You have access to a set of backend tools to search knowledge, look up professors, check schedules, and manage appointments.
Always answer in the user's language (English, Telugu, or Roman Telugu) and keep responses student-friendly and brief.

You operate in a reasoning loop. On your turn, you MUST output valid JSON matching this schema:
{
    "thought": "Your internal reasoning about what to do next.",
    "action": "tool" OR "reply",
    "tool_name": "name of the tool if action=tool",
    "tool_args": {"arg1": "value"} if action=tool,
    "reply": "The natural language response to the user if action=reply",
    "language": "The detected user language (English, Telugu, Roman Telugu)",
    "intent": "The primary intent of the conversation (e.g. PROFESSOR_APPOINTMENT, FACILITY_INFORMATION)",
    "workflow_state": "IDLE | COLLECTING_INFORMATION | AWAITING_CONFIRMATION | COMPLETED"
}

RULES:
1. If you need information, set "action": "tool" and provide "tool_name" and "tool_args".
2. If you have the information or need to ask the user a clarifying question, set "action": "reply" and provide "reply".
3. For appointments (create, reschedule, cancel), you MUST NOT call the tool until you have explicitly asked the user for confirmation and they have agreed. During this time, set workflow_state to AWAITING_CONFIRMATION.
4. Do not invent or hallucinate data. Only use tool results.
5. If a tool fails, explain the error to the user gracefully in the "reply".
6. The backend guards all data; pass exactly what the tool requires.

Available Tools:
{tools}
"""

async def _run_agent_internal(message: str, session_id: str, student_id: str) -> tuple[str, str, str, str, bool, list[dict]]:
    """Runs the agent loop and returns the final response tuple."""
    # Retrieve context
    session = await store.get_chat_session(session_id, student_id)
    if session:
        session_id = session["session_id"]
        history = session.get("turns", [])[-6:] # Keep last 6 turns for context
    else:
        session_id = session_id or __import__("uuid").uuid4().hex
        history = []
        
    tools_json = json.dumps(get_all_tool_definitions(), indent=2)
    system_prompt = AGENT_SYSTEM_PROMPT.replace("{tools}", tools_json)
    
    # Build conversation context
    context_msgs = []
    for turn in history:
        context_msgs.append(f"User: {turn['user_message']}\nAssistant: {turn['assistant_message']}")
    context_msgs.append(f"User: {message}")
    
    prompt = "Conversation History:\n" + "\n".join(context_msgs) + "\n\nTool Results:\n"
    
    all_sources = []
    step = 0
    final_reply = "I'm sorry, I couldn't process your request."
    final_intent = "UNKNOWN"
    final_language = "English"
    verified = False
    
    while step < MAX_STEPS:
        step += 1
        try:
            raw_response = await llm.complete(system_prompt, prompt, json_mode=True, timeout=10.0)
            if not raw_response:
                return await _deterministic_fallback(message, session_id, student_id)
                
            # Parse response
            try:
                response = json.loads(raw_response)
            except json.JSONDecodeError:
                logger.error(f"Agent returned invalid JSON: {raw_response}")
                return await _deterministic_fallback(message, session_id, student_id)

                
            action = response.get("action")
            thought = response.get("thought", "")
            final_intent = response.get("intent", "UNKNOWN")
            final_language = response.get("language", "English")
            
            logger.info(f"Agent Step {step} | Action: {action} | Thought: {thought}")
            
            if action == "reply":
                final_reply = response.get("reply", "")
                break
                
            elif action == "tool":
                tool_name = response.get("tool_name")
                tool_args = response.get("tool_args", {})
                
                # Execute tool
                tool_result = await execute_tool(tool_name, tool_args, student_id)
                
                # Collect sources if any
                if tool_result.sources:
                    all_sources.extend(tool_result.sources)
                    verified = True
                
                # Append result to prompt for next iteration
                prompt += f"\nTool '{tool_name}' returned: {tool_result.model_dump_json()}\n"
                
            else:
                logger.error(f"Agent returned unknown action: {action}")
                return await _deterministic_fallback(message, session_id, student_id)
                
        except Exception as e:
            logger.error(f"Agent loop error: {e}")
            return await _deterministic_fallback(message, session_id, student_id)
            
    # Deduplicate sources
    unique_sources = []
    seen_urls = set()
    for s in all_sources:
        if s["url"] not in seen_urls:
            seen_urls.add(s["url"])
            unique_sources.append(s)
            
    # Save the final interaction
    await store.append_chat_turn(session_id, student_id, message, final_reply, final_intent, final_language)
    
    return final_reply, final_intent, final_language, session_id, verified, unique_sources

async def run_agent(message: str, session_id: str, student_id: str) -> tuple[str, str, str, str, bool, list[dict]]:
    try:
        return await _run_agent_internal(message, session_id, student_id)
    except Exception as e:
        logger.error(f"Agent failed with error: {e}")
        return "I am currently experiencing technical difficulties. Please try again later.", "UNKNOWN", "English", session_id if session_id else "error", False, []


async def _deterministic_fallback(message: str, session_id: str, student_id: str) -> tuple:
    from app.web_mvp.services import legacy_answer_chat
    return await legacy_answer_chat(message, session_id, student_id)
