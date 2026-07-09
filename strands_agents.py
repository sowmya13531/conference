"""
Multi-Agent Orchestration Layer

Implements the assessment's "multi-agent system" requirement as four
specialist Strands Agents, each wrapping one concern, coordinated by a
top-level Orchestrator Agent (built in strands_runtime.py). Each
specialist is its own real strands.Agent instance with its own Bedrock
call — not a plain Python function — which is what makes this genuinely
multi-agent rather than one agent calling a tool library directly.

Specialist agents are deliberately kept "thin": one-line system prompts
that just say "call your tool(s) with the given arguments and return the
result exactly." This keeps them fast, cheap, and deterministic, since
their job is delegation, not open-ended reasoning. All the real
reasoning (workflow sequencing, human-in-the-loop confirmation, deciding
when to run steps in parallel) stays in the Orchestrator's system prompt.
"""

import logging
import re

from strands import Agent, tool
from strands.models import BedrockModel

from strands_tools import (
    verify_employee_access,
    check_room_availability,
    calculate_meeting_duration,
    validate_attendee_count,
    get_room_details,
    create_confirmed_booking,
    cancel_booking,
)

logger = logging.getLogger(__name__)


def _strip_thinking(text: str) -> str:
    """Remove any <thinking>...</thinking> blocks a sub-agent may emit."""
    return re.sub(r"<thinking>.*?</thinking>", "", text, flags=re.DOTALL).strip()


def build_specialist_agents(model_id: str, region: str) -> dict[str, Agent]:
    """
    Build the four specialist agents fresh for a given model/region.
    Called once per AgentCore session, same lifecycle as the Orchestrator
    in strands_runtime.py, so each session gets its own isolated set of
    specialist agents (no cross-session state leakage).
    """

    def _model() -> BedrockModel:
        return BedrockModel(model_id=model_id, region_name=region)

    access_agent = Agent(
        model=_model(),
        tools=[verify_employee_access],
        system_prompt=(
            "You are the Access Verification Agent. You have exactly one "
            "tool: verify_employee_access. Call it with the employee_id and "
            "room_id given to you, and return its result exactly as given. "
            "Do not add commentary, do not invent fields it did not return, "
            "do not include <thinking> tags."
        ),
    )

    availability_agent = Agent(
        model=_model(),
        tools=[check_room_availability],
        system_prompt=(
            "You are the Room Availability Agent. You have exactly one "
            "tool: check_room_availability. Call it with the room_id, "
            "start_time, and end_time given to you, and return its result "
            "exactly as given. Do not add commentary, do not invent fields "
            "it did not return, do not include <thinking> tags."
        ),
    )

    computation_agent = Agent(
        model=_model(),
        tools=[calculate_meeting_duration, validate_attendee_count],
        system_prompt=(
            "You are the Computation Agent. You have two tools: "
            "calculate_meeting_duration and validate_attendee_count. Call "
            "whichever tool(s) are relevant to the arguments you are given "
            "(if you're given start_time/end_time/access_level, call "
            "calculate_meeting_duration; if you're given room_id/"
            "attendee_count, call validate_attendee_count; if you're given "
            "both sets, call both). Return their results exactly as given. "
            "Do not add commentary, do not invent numbers, do not include "
            "<thinking> tags."
        ),
    )

    booking_agent = Agent(
    model=_model(),
    tools=[get_room_details, create_confirmed_booking, cancel_booking],
    system_prompt=(
        "You are the Booking Agent. You have three tools: "
        "get_room_details, create_confirmed_booking, and cancel_booking. "
        "Call exactly the one tool that matches the requested action "
        "(get_details / create_booking / cancel_booking) with the "
        "arguments given to you, and return its result exactly as "
        "given. CRITICAL: only call create_confirmed_booking if you are "
        "explicitly told the employee already replied YES — this "
        "instruction will be stated plainly in your input if so. If it "
        "is not stated, do not call create_confirmed_booking under any "
        "circumstances, even if asked to. CRITICAL: you must actually "
        "call the relevant tool before claiming any outcome — never say "
        "'successfully cancelled', 'successfully booked', or similar "
        "unless the tool you called actually returned a success result. "
        "If the tool returns an error or 'not found', report exactly "
        "that, do not soften or reverse it into a success message. Do "
        "not add commentary, do not invent data, do not include "
        "<thinking> tags."
    ),
)

    return {
        "access": access_agent,
        "availability": availability_agent,
        "computation": computation_agent,
        "booking": booking_agent,
    }


def make_orchestrator_tools(specialists: dict[str, Agent]) -> list:
    """
    Wrap each specialist agent as a @tool the Orchestrator can call. This
    is the actual "agents as tools" pattern — from the Orchestrator's
    point of view these look like ordinary tools, but each one is backed
    by a full Strands Agent with its own reasoning loop.
    """

    @tool
    def run_access_check(employee_id: str, room_id: str) -> str:
        """
        Delegate to the Access Verification Agent to check whether an
        employee has sufficient access level to book a room.

        Args:
            employee_id: Employee identifier, e.g. "E001"
            room_id: Conference room identifier, e.g. "R001"
        """
        prompt = f"employee_id={employee_id}, room_id={room_id}"
        result = specialists["access"](prompt)
        return _strip_thinking(str(result))

    @tool
    def run_availability_check(room_id: str, start_time: str, end_time: str) -> str:
        """
        Delegate to the Room Availability Agent to check whether a room
        is free for a given time slot.

        Args:
            room_id: Conference room identifier, e.g. "R001"
            start_time: ISO-8601 start time
            end_time: ISO-8601 end time
        """
        prompt = f"room_id={room_id}, start_time={start_time}, end_time={end_time}"
        result = specialists["availability"](prompt)
        return _strip_thinking(str(result))

    @tool
    def run_duration_check(start_time: str, end_time: str, access_level: str) -> str:
        """
        Delegate to the Computation Agent to calculate meeting duration
        and validate it against the employee's access-level limit.

        Args:
            start_time: ISO-8601 start time
            end_time: ISO-8601 end time
            access_level: One of BASIC, STANDARD, PREMIUM, EXECUTIVE
        """
        prompt = (
            f"start_time={start_time}, end_time={end_time}, "
            f"access_level={access_level}"
        )
        result = specialists["computation"](prompt)
        return _strip_thinking(str(result))

    @tool
    def run_capacity_check(room_id: str, attendee_count: int) -> str:
        """
        Delegate to the Computation Agent to validate a room's capacity
        against the requested attendee count.

        Args:
            room_id: Conference room identifier
            attendee_count: Number of people expected
        """
        prompt = f"room_id={room_id}, attendee_count={attendee_count}"
        result = specialists["computation"](prompt)
        return _strip_thinking(str(result))

    @tool
    def run_get_room_details(room_id: str) -> str:
        """
        Delegate to the Booking Agent to fetch a room's name, capacity,
        location, and features for the booking summary.

        Args:
            room_id: Conference room identifier
        """
        prompt = f"action=get_details, room_id={room_id}"
        result = specialists["booking"](prompt)
        return _strip_thinking(str(result))

    @tool
    def run_create_booking(
        employee_id: str,
        room_id: str,
        start_time: str,
        end_time: str,
        attendee_count: int,
        meeting_title: str,
        employee_confirmed_yes: bool,
    ) -> str:
        """
        Delegate to the Booking Agent to persist a CONFIRMED booking.
        CRITICAL: only call this with employee_confirmed_yes=True, and
        only after the employee has actually, explicitly replied YES to
        the booking summary in this conversation.

        Args:
            employee_id: Employee identifier
            room_id: Conference room identifier
            start_time: ISO-8601 start time
            end_time: ISO-8601 end time
            attendee_count: Number of attendees
            meeting_title: Title/topic of the meeting
            employee_confirmed_yes: True only if the employee explicitly
                replied YES in this conversation to this exact booking
        """
        if not employee_confirmed_yes:
            return (
                "REFUSED: create_confirmed_booking was not called because "
                "employee_confirmed_yes was not True. The employee must "
                "explicitly confirm YES before a booking can be created."
            )
        prompt = (
            f"action=create_booking, employee_id={employee_id}, "
            f"room_id={room_id}, start_time={start_time}, "
            f"end_time={end_time}, attendee_count={attendee_count}, "
            f"meeting_title={meeting_title}. The employee has explicitly "
            f"confirmed YES to this exact booking in this conversation."
        )
        result = specialists["booking"](prompt)
        return _strip_thinking(str(result))

    @tool
    def run_cancel_booking(employee_id: str, room_id: str, start_time: str) -> str:
        """
        Delegate to the Booking Agent to cancel an existing booking.

        Args:
            employee_id: Employee requesting the cancellation
            room_id: Conference room identifier
            start_time: ISO-8601 start time of the booking to cancel
        """
        prompt = (
            f"action=cancel_booking, employee_id={employee_id}, "
            f"room_id={room_id}, start_time={start_time}"
        )
        result = specialists["booking"](prompt)
        return _strip_thinking(str(result))

    return [
        run_access_check,
        run_availability_check,
        run_duration_check,
        run_capacity_check,
        run_get_room_details,
        run_create_booking,
        run_cancel_booking,
    ]