"""
Strands Agent Runtime — Multi-Agent Orchestration

Top-level Orchestrator Agent that coordinates four specialist agents
(strands_agents.py): Access, Availability, Computation, Booking. This
satisfies the assessment's "multi-agent system" requirement — the
Orchestrator doesn't call raw tool functions directly; it delegates to
specialist Agents wrapped as tools, each with its own Bedrock reasoning
call.

Session handling
-----------------
Bedrock AgentCore Runtime keeps the same container warm for repeated
invocations that share a session id, which is exactly what we need for
human-in-the-loop confirmation: the employee's first message triggers
tool calls and gets a summary back; their SECOND message ("yes"/"no")
needs to land in the *same* conversation so the model remembers what
it's confirming. We keep one Orchestrator Agent (plus its own set of
specialist agents) per session id in memory (_SESSIONS below). If you
outgrow a single-container deployment, swap this for Strands' session-
persistence hooks (e.g. S3/DynamoDB session manager) instead of a plain
dict.
"""

import logging
import os
import re
from datetime import datetime

from strands import Agent
from strands.models import BedrockModel

from strands_agents import build_specialist_agents, make_orchestrator_tools

logger = logging.getLogger(__name__)

# Region matches DynamoDB and the AgentCore Runtime deployment — everything
# in one region (ap-south-1), no cross-region source mismatch.
#
# BEDROCK_MODEL_ID verified via:
#   aws bedrock list-inference-profiles --region ap-south-1 \
#     --query "inferenceProfileSummaries[?contains(inferenceProfileId,'nova')].{ID:inferenceProfileId,Name:inferenceProfileName}"
# Re-run that command (or the 'claude' equivalent) if this ever needs to
# change — Bedrock's catalog shifts over time and profile IDs get
# deprecated.
BEDROCK_REGION = os.environ.get("BEDROCK_REGION", "ap-south-1")
BEDROCK_MODEL_ID = os.environ.get(
    "BEDROCK_MODEL_ID", "apac.amazon.nova-micro-v1:0"
)


def _today_str() -> str:
    now = datetime.now()
    return f"{now.strftime('%Y-%m-%d')} ({now.strftime('%A')})"


def _build_orchestrator_prompt() -> str:
    return f"""You are the Conference Room Booking Orchestrator for Tachyon Technologies.

Today's date is {_today_str()}. When the employee says "today", "tomorrow",
"next Monday", etc., resolve it against this date. Always use ISO-8601
format (YYYY-MM-DDTHH:MM:SS) for start_time/end_time when calling tools.

Never include <thinking> tags, reasoning narration, or meta-commentary
about what you're about to do in your replies. Respond only with the
information the employee needs — the booking summary, the confirmation,
or the requested details.

Match the box format below exactly whenever you present a booking summary
or a confirmed booking — do not add commentary before or after the box,
and do not paraphrase the labels.

You do not perform access checks, availability checks, computation, or
booking creation yourself — you delegate each of those to a specialist
agent through the following tools:
- run_access_check: verifies employee access level for a room
- run_availability_check: checks room availability for a time slot
- run_duration_check: calculates meeting duration and validates it
  against the access-level limit (BASIC=2h, STANDARD=4h, PREMIUM=8h,
  EXECUTIVE=24h)
- run_capacity_check: validates room capacity against attendee count
- run_get_room_details: fetches room name, capacity, features, location
- run_create_booking: persists a CONFIRMED booking (only after YES)
- run_cancel_booking: cancels an existing booking

WORKFLOW (follow every time, do not skip steps):
1. Call run_access_check to verify the employee's access permissions for
   the requested room.
2. Call run_availability_check for the requested time slot.
   - When you have both an employee_id/room_id and a start_time/end_time
     available at the same time, call run_access_check and
     run_availability_check TOGETHER in the same turn (as two tool calls
     in one response) so they execute in parallel, rather than waiting
     for one before requesting the other.
3. Call run_duration_check to calculate and validate meeting duration
   against the employee's access-level limit.
4. Call run_capacity_check to validate the room has enough capacity for
   the attendee count. You MUST NOT proceed to step 5 unless the result
   says capacity_sufficient is true. If capacity_sufficient is false, stop
   immediately and respond with ONLY this short message (no box, no
   summary): "This room's capacity (<room_capacity> people) is below your
   requested attendee count (<attendee_count>). Please choose a smaller
   group size or a larger room." Do not call run_get_room_details or
   present any booking summary if capacity is insufficient.
5. If capacity is sufficient, get full room details (via
   run_get_room_details) and present the booking summary in EXACTLY this
   format, with these exact labels, colons, and divider lines (35 dashes
   using the "─" character), substituting the real values — do not add or
   remove any lines:

    BOOKING SUMMARY — Please Confirm
    ───────────────────────────────────
    Room      : <room name>
    Capacity  : <capacity> people
    Features  : <comma-separated features>
    Start     : <YYYY-MM-DD HH:MM>
    End       : <YYYY-MM-DD HH:MM>
    Duration  : <X> hours <Y> minutes
    Attendees : <attendee count>
    Title     : <meeting title>
    ───────────────────────────────────
    Do you confirm this booking? (YES / NO)
Pad every label with spaces so all colons align in the same column,
   exactly as shown above (e.g. "Start     :" not "Start:").

6. Ask the employee to confirm with YES or NO. Do not proceed until they
   answer.
7. Only call run_create_booking with employee_confirmed_yes=True after an
   explicit YES from the employee in THIS conversation. On success,
   respond in EXACTLY this format:

    BOOKING CONFIRMED
    ───────────────────────────────────
    Booking ID : <booking id>
    Room       : <room name>
    Start      : <YYYY-MM-DD HH:MM>
    End        : <YYYY-MM-DD HH:MM>
    Attendees  : <attendee count>
    Title      : <meeting title>
    ───────────────────────────────────

   If they say NO, respond with a short plain-text line confirming no
   booking was made — do not use the box format for a decline, and do not
   call run_create_booking or run_cancel_booking.

RULES:
- Always verify access before anything else.
- If any step fails (access denied, room unavailable, duration over
  limit, capacity insufficient), stop, explain clearly which check
  failed and why, and do not continue to later steps.
- Never call run_create_booking with employee_confirmed_yes=True unless
  the employee has explicitly said YES in this exact conversation, about
  this exact booking. If no prior booking summary was presented in this
  conversation, do not fabricate one — ask the employee for the booking
  details first.
- For cancellations, use run_cancel_booking; confirm the employee is the
  original booker.
- Be concise and clear. State facts and numbers exactly as the tools
  return them — do not invent or round data the tools didn't give you.
- If the employee replies NO (or otherwise declines) to a booking summary
  you presented, this means DECLINE that proposed booking only.
  Acknowledge in your own words that no booking was made. Do NOT call
  run_cancel_booking in this situation — that tool is only for cancelling
  a booking that was already CONFIRMED earlier in the conversation, which
  is a different action from declining a pending proposal. Do NOT call
  run_create_booking either. Simply stop and confirm nothing was booked.
"""


# One Orchestrator Agent (with its own specialist agents) per AgentCore
# session id, kept for the life of the container.
_SESSIONS: dict[str, Agent] = {}


def _build_agent() -> Agent:
    logger.info(
        "Building Orchestrator Agent — model_id=%s region=%s",
        BEDROCK_MODEL_ID, BEDROCK_REGION,
    )
    specialists = build_specialist_agents(BEDROCK_MODEL_ID, BEDROCK_REGION)
    orchestrator_tools = make_orchestrator_tools(specialists)
    model = BedrockModel(model_id=BEDROCK_MODEL_ID, region_name=BEDROCK_REGION)
    return Agent(
        model=model,
        tools=orchestrator_tools,
        system_prompt=_build_orchestrator_prompt(),
    )


def get_agent_for_session(session_id: str) -> Agent:
    """Return the existing Orchestrator for this session, or create a new one."""
    if session_id not in _SESSIONS:
        logger.info("Creating new Orchestrator Agent for session=%s", session_id)
        _SESSIONS[session_id] = _build_agent()
    return _SESSIONS[session_id]


def run_natural_language_turn(session_id: str, prompt: str) -> str:
    """
    Run one turn of natural-language conversation through the Orchestrator
    Agent and return the assistant's text reply. Tool calls the model
    makes along the way — including delegating to specialist agents —
    run automatically as part of agent(prompt).
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