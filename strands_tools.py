"""
Strands Agent Tool Definitions

Thin @tool wrappers around booking_agent.ToolExecutor. Business logic and
DynamoDB access stay exactly where they already are (booking_agent.py) —
this file's only job is to expose those functions to a strands.Agent with
type-hinted signatures and docstrings, which Strands uses to build the
tool schema it hands to the Bedrock model.

Nothing here talks to DynamoDB directly. If you need to change booking
rules (buffers, limits, etc.) edit booking_agent.py, not this file.
"""

import logging
from typing import Dict

from strands import tool

from booking_agent import ToolExecutor, BookingRequest, BookingOrchestrator

logger = logging.getLogger(__name__)

_orchestrator = BookingOrchestrator()


@tool
def verify_employee_access(employee_id: str, room_id: str) -> Dict:
    """
    Verify that an employee has sufficient access level to book a given
    conference room. Always call this before checking availability or
    creating a booking.

    Args:
        employee_id: Employee identifier, e.g. "E001"
        room_id: Conference room identifier, e.g. "R001"

    Returns:
        access_granted (bool), employee_name, access_level,
        room_required_level, error (str or None)
    """
    return ToolExecutor.verify_employee_access(employee_id, room_id)


@tool
def check_room_availability(room_id: str, start_time: str, end_time: str) -> Dict:
    """
    Check whether a conference room is free for the requested time slot,
    including a 15-minute buffer against existing bookings.

    Args:
        room_id: Conference room identifier, e.g. "R001"
        start_time: ISO-8601 start time, e.g. "2026-07-10T10:00:00"
        end_time: ISO-8601 end time, e.g. "2026-07-10T12:00:00"

    Returns:
        available (bool), conflicts (list), error (str or None)
    """
    return ToolExecutor.check_room_availability(room_id, start_time, end_time)


@tool
def calculate_meeting_duration(start_time: str, end_time: str, access_level: str) -> Dict:
    """
    Calculate meeting duration in hours/minutes and check it against the
    employee's access-level booking limit (BASIC=2h, STANDARD=4h,
    PREMIUM=8h, EXECUTIVE=24h).

    Args:
        start_time: ISO-8601 start time
        end_time: ISO-8601 end time
        access_level: One of BASIC, STANDARD, PREMIUM, EXECUTIVE — use the
            access_level returned by verify_employee_access

    Returns:
        duration_hours, duration_minutes, within_limit (bool), error
    """
    return ToolExecutor.calculate_meeting_duration(start_time, end_time, access_level)


@tool
def get_room_details(room_id: str) -> Dict:
    """
    Get a conference room's name, capacity, location, and features
    (projector, video conferencing, etc). Use this to build the booking
    summary you present to the employee for confirmation.

    Args:
        room_id: Conference room identifier, e.g. "R001"
    """
    return ToolExecutor.get_room_details(room_id)


@tool
def validate_attendee_count(room_id: str, attendee_count: int) -> Dict:
    """
    Check that a room's capacity is sufficient for the number of attendees.

    Args:
        room_id: Conference room identifier
        attendee_count: Number of people expected
    """
    return ToolExecutor.validate_attendee_count(room_id, attendee_count)


@tool
def create_confirmed_booking(
    employee_id: str,
    room_id: str,
    start_time: str,
    end_time: str,
    attendee_count: int,
    meeting_title: str,
) -> Dict:
    """
    Persist a CONFIRMED booking to DynamoDB.

    CRITICAL: only call this tool after the employee has seen the full
    booking summary (room, capacity, features, start/end time, duration,
    attendee count) and has explicitly replied YES/confirm. If the
    employee has not yet confirmed, or replies NO, do NOT call this tool —
    ask for confirmation instead, or acknowledge the cancellation in text.

    Args:
        employee_id: Employee identifier
        room_id: Conference room identifier
        start_time: ISO-8601 start time
        end_time: ISO-8601 end time
        attendee_count: Number of attendees
        meeting_title: Title/topic of the meeting
    """
    booking = BookingRequest(
        employee_id=employee_id,
        room_id=room_id,
        start_time=start_time,
        end_time=end_time,
        attendee_count=int(attendee_count),
        meeting_title=meeting_title,
    )
    return ToolExecutor.create_booking(booking)


@tool
def cancel_booking(employee_id: str, room_id: str, start_time: str) -> Dict:
    """
    Cancel an existing CONFIRMED booking. The requesting employee must be
    the original booker. Marks the record CANCELLED rather than deleting
    it (audit trail).

    Args:
        employee_id: Employee requesting the cancellation
        room_id: Conference room identifier
        start_time: ISO-8601 start time of the booking to cancel — must
            match exactly what was used to create the booking
    """
    return ToolExecutor.cancel_existing_booking(employee_id, room_id, start_time)


ALL_TOOLS = [
    verify_employee_access,
    check_room_availability,
    calculate_meeting_duration,
    get_room_details,
    validate_attendee_count,
    create_confirmed_booking,
    cancel_booking,
]