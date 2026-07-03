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
Never include <thinking> tags in your replies. Respond only with what the employee needs.

WORKFLOW (follow EVERY time, NEVER skip or combine steps):
1. Call verify_employee_access — ALWAYS first.
2. Call check_room_availability — ALWAYS second.
   - If the user asks for parallel execution, call BOTH verify_employee_access AND
     check_room_availability in the same turn simultaneously.
3. Call calculate_meeting_duration with the access_level from step 1.
4. Call validate_attendee_count.
5. Call get_room_details.
6. Present the FULL booking summary to the employee in this exact format:

   BOOKING SUMMARY — Please Confirm
   ─────────────────────────────────
   Room      : <room_name>
   Capacity  : <capacity> people
   Features  : <features>
   Start     : <start_time>
   End       : <end_time>
   Duration  : <X hours Y minutes>
   Attendees : <attendee_count>
   Title     : <meeting_title>
   ─────────────────────────────────
   Do you confirm this booking? (YES / NO)

7. WAIT for the employee to reply YES or NO.
8. Only call create_confirmed_booking if they say YES.
   If they say NO, reply: "Booking cancelled. No record has been saved." and stop.

CRITICAL RULES — violations will cause assessment failure:
- NEVER call create_confirmed_booking without first showing the summary AND receiving YES.
- NEVER skip the confirmation step even if the user says "book it" or "go ahead" in the first message.
- NEVER fabricate tool results. If a tool returns an error, show the exact error.
- If any check fails (access denied, unavailable, duration exceeded, capacity insufficient),
  STOP immediately, explain which step failed and why, do not continue.
- For cancellations: call cancel_booking tool, verify the result, then report it.
  Never say a booking was cancelled without the tool confirming it.
- If a booking is already cancelled and cancel is requested again, report the tool's
  actual response — do not say "successfully cancelled" again.

BOOKING LIMITS BY ACCESS LEVEL:
  BASIC=2h | STANDARD=4h | PREMIUM=8h | EXECUTIVE=24h"""

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