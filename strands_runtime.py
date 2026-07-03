"""
Strands Agent Runtime

This is the piece that was missing from the project: an actual
strands.Agent backed by a Claude model on Amazon Bedrock, wired to the
tool functions in strands_tools.py.

Session handling
-----------------
Bedrock AgentCore Runtime keeps the same container warm for repeated
invocations that share a session id, which is exactly what we need for
human-in-the-loop confirmation: the employee's first message triggers
tool calls and gets a summary back; their SECOND message ("yes"/"no")
needs to land in the *same* conversation so the model remembers what
it's confirming. We keep one strands.Agent instance per session id in
memory (_SESSIONS below). If you outgrow a single-container deployment,
swap this for Strands' session-persistence hooks (e.g. S3/DynamoDB
session manager) instead of a plain dict.
"""

import logging
import os
import re

from strands import Agent
from strands.models import BedrockModel

from strands_tools import ALL_TOOLS

logger = logging.getLogger(__name__)

# Region matches DynamoDB and the AgentCore Runtime deployment — everything
# in one region (ap-south-1) now, no cross-region source mismatch.
#
# BEDROCK_MODEL_ID verified via:
#   aws bedrock list-inference-profiles --region ap-south-1 \
#     --query "inferenceProfileSummaries[?contains(inferenceProfileId,'nova')].{ID:inferenceProfileId,Name:inferenceProfileName}"
# Re-run that command if this ever needs to change.
BEDROCK_REGION = os.environ.get("BEDROCK_REGION", "ap-south-1")
BEDROCK_MODEL_ID = os.environ.get(
    "BEDROCK_MODEL_ID", "apac.amazon.nova-micro-v1:0"
)

SYSTEM_PROMPT = """You are the Conference Room Booking Assistant for Tachyon Technologies.
Never include <thinking> tags, reasoning narration, or meta-commentary about what you're about to do in your replies. Respond only with the information the employee needs — the booking summary, the confirmation, or the requested details

WORKFLOW (follow every time, do not skip steps):
1. Verify the employee's access permissions for the requested room (verify_employee_access).
2. Check room availability for the requested time slot (check_room_availability).
   - When you have both an employee_id/room_id and a start_time/end_time available at
     the same time, call verify_employee_access and check_room_availability TOGETHER in
     the same turn (as two tool calls in one response) so they execute in parallel,
     rather than waiting for one before requesting the other.
3. Calculate meeting duration and validate it against the employee's access-level limit
   (calculate_meeting_duration) — BASIC=2h, STANDARD=4h, PREMIUM=8h, EXECUTIVE=24h.
4. Validate the room has enough capacity for the attendee count (validate_attendee_count).
5. Get full room details (get_room_details) and present a booking summary: room name,
   capacity, features, start time, end time, calculated duration, attendee count, title.
6. Ask the employee to confirm with YES or NO. Do not proceed until they answer.
7. Only call create_confirmed_booking after an explicit YES. If they say NO, confirm the
   booking was cancelled and do not call create_confirmed_booking.

RULES:
- Always verify access before anything else.
- If any step fails (access denied, room unavailable, duration over limit, capacity
  insufficient), stop, explain clearly which check failed and why, and do not continue
  to later steps.
- Never call create_confirmed_booking without an explicit prior YES from the employee
  in this conversation.
- For cancellations, use cancel_booking; confirm the employee is the original booker.
- Be concise and clear. State facts and numbers exactly as the tools return them —
  do not invent or round data the tools didn't give you.
"""

# One Agent per AgentCore session id, kept for the life of the container.
_SESSIONS: dict[str, Agent] = {}


def _build_agent() -> Agent:
    logger.info(
        "Building Strands Agent — model_id=%s region=%s",
        BEDROCK_MODEL_ID, BEDROCK_REGION,
    )
    model = BedrockModel(model_id=BEDROCK_MODEL_ID, region_name=BEDROCK_REGION)
    return Agent(model=model, tools=ALL_TOOLS, system_prompt=SYSTEM_PROMPT)


def get_agent_for_session(session_id: str) -> Agent:
    """Return the existing agent for this session, or create a new one."""
    if session_id not in _SESSIONS:
        logger.info("Creating new Strands Agent for session=%s", session_id)
        _SESSIONS[session_id] = _build_agent()
    return _SESSIONS[session_id]


def run_natural_language_turn(session_id: str, prompt: str) -> str:
    """
    Run one turn of natural-language conversation through the Strands
    Agent and return the assistant's text reply. Tool calls the model
    makes along the way run automatically as part of agent(prompt).
    """
    agent = get_agent_for_session(session_id)
    try:
        result = agent(prompt)
    except Exception as exc:
        raise RuntimeError(
            f"Bedrock call failed (model_id={BEDROCK_MODEL_ID}, "
            f"region={BEDROCK_REGION}): {exc}"
        ) from exc
    reply = str(result)
    reply = re.sub(r"<thinking>.*?</thinking>", "", reply, flags=re.DOTALL).strip()
    return reply