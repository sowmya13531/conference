"""
Conference Room Booking Agent — Tool Schema Reference & Prompt Templates

Centralises two things used across the project:

1. TOOL_DEFINITIONS
   JSON-schema descriptions of every tool the agent exposes. These mirror
   the @tool-decorated functions in strands_tools.py 1-to-1 with the
   ToolExecutor methods in booking_agent.py — kept here as a readable
   reference / for the Lambda handler, not as the live tool schema (Strands
   derives that directly from strands_tools.py's type hints at runtime).

2. PROMPT_TEMPLATES
   Example natural-language prompts for each demonstration scenario. See
   prompts.md for the full, current set used in the actual demo.

The live agent's model id, region, and system prompt are configured in
strands_runtime.py (BEDROCK_MODEL_ID, BEDROCK_REGION, SYSTEM_PROMPT) — that
is the file to edit to change agent behavior, not this one.
"""


TOOL_DEFINITIONS = [
    {
        "toolName": "verify_employee_access",
        "description": "Verifies if an employee has the required access permissions to book a specific conference room. Returns employee profile and access level.",
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "employee_id": {
                        "type": "string",
                        "description": "The unique identifier of the employee (e.g., E001)"
                    },
                    "room_id": {
                        "type": "string",
                        "description": "The unique identifier of the conference room (e.g., R001)"
                    }
                },
                "required": ["employee_id", "room_id"]
            }
        }
    },
    {
        "toolName": "check_room_availability",
        "description": "Checks if a conference room is available for the requested time slot. Returns availability status and lists any conflicting bookings with a 15-minute buffer.",
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "room_id": {
                        "type": "string",
                        "description": "The unique identifier of the conference room (e.g., R001)"
                    },
                    "start_time": {
                        "type": "string",
                        "description": "Meeting start time in ISO 8601 format (e.g., 2026-01-15T10:00:00)"
                    },
                    "end_time": {
                        "type": "string",
                        "description": "Meeting end time in ISO 8601 format (e.g., 2026-01-15T12:00:00)"
                    }
                },
                "required": ["room_id", "start_time", "end_time"]
            }
        }
    },
    {
        "toolName": "calculate_meeting_duration",
        "description": "Calculates the meeting duration and validates it against the employee's access level booking limit. Returns duration in hours and minutes, and whether it's within limits.",
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "start_time": {
                        "type": "string",
                        "description": "Meeting start time in ISO 8601 format (e.g., 2026-01-15T10:00:00)"
                    },
                    "end_time": {
                        "type": "string",
                        "description": "Meeting end time in ISO 8601 format (e.g., 2026-01-15T12:00:00)"
                    },
                    "access_level": {
                        "type": "string",
                        "enum": ["BASIC", "STANDARD", "PREMIUM", "EXECUTIVE"],
                        "description": "The employee's access level (determines max booking hours)"
                    }
                },
                "required": ["start_time", "end_time", "access_level"]
            }
        }
    },
    {
        "toolName": "get_room_details",
        "description": "Retrieves detailed information about a conference room including capacity, location, features, and access requirements.",
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "room_id": {
                        "type": "string",
                        "description": "The unique identifier of the conference room (e.g., R001)"
                    }
                },
                "required": ["room_id"]
            }
        }
    },
    {
        "toolName": "validate_attendee_count",
        "description": "Validates that the conference room has sufficient capacity for the requested number of attendees.",
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "room_id": {
                        "type": "string",
                        "description": "The unique identifier of the conference room (e.g., R001)"
                    },
                    "attendee_count": {
                        "type": "integer",
                        "description": "The number of attendees expected for the meeting"
                    }
                },
                "required": ["room_id", "attendee_count"]
            }
        }
    },
    {
        "toolName": "create_booking",
        "description": "Creates and persists a confirmed booking to DynamoDB. This should only be called after human confirmation. Returns the booking ID and confirmation status.",
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "employee_id": {
                        "type": "string",
                        "description": "The unique identifier of the employee making the booking"
                    },
                    "room_id": {
                        "type": "string",
                        "description": "The unique identifier of the conference room"
                    },
                    "start_time": {
                        "type": "string",
                        "description": "Meeting start time in ISO 8601 format"
                    },
                    "end_time": {
                        "type": "string",
                        "description": "Meeting end time in ISO 8601 format"
                    },
                    "attendee_count": {
                        "type": "integer",
                        "description": "The number of attendees for this meeting"
                    },
                    "meeting_title": {
                        "type": "string",
                        "description": "The title or topic of the meeting"
                    }
                },
                "required": ["employee_id", "room_id", "start_time", "end_time", "attendee_count", "meeting_title"]
            }
        }
    }
]


# ─────────────────────────────────────────────────────────────────────────
# REMOVED: AGENT_CONFIG dict (previously hardcoded "amazon.nova-micro-v1:0"
# here). It was dead code — never imported or used by main.py or
# booking_agent.py — but its presence caused real confusion during
# development (its model/instructions got mistaken for the live config and
# copy-pasted into the actual runtime, breaking the deployed agent).
#
# The system prompt, model id, and region that ACTUALLY drive the deployed
# agent live in strands_runtime.py (SYSTEM_PROMPT, BEDROCK_MODEL_ID,
# BEDROCK_REGION). Edit those, not this file, to change agent behavior.
# ─────────────────────────────────────────────────────────────────────────


# Prompt templates for common scenarios
PROMPT_TEMPLATES = {
    "sequential": """Book a conference room for me with these details:
- Employee ID: {employee_id}
- Room ID: {room_id}
- Start Time: {start_time}
- End Time: {end_time}
- Number of Attendees: {attendee_count}
- Meeting Title: {meeting_title}

Please verify my access, check availability, and present the booking summary for confirmation. Use SEQUENTIAL execution (each step waits for the previous one).""",

    "parallel": """Book a conference room for me with these details:
- Employee ID: {employee_id}
- Room ID: {room_id}
- Start Time: {start_time}
- End Time: {end_time}
- Number of Attendees: {attendee_count}
- Meeting Title: {meeting_title}

Please verify my access and check availability in PARALLEL, then proceed with other validations and present the booking summary.""",

    "insufficient_access": """I want to book the Executive Suite (R006) as an employee with BASIC access level:
- Employee ID: E004
- Room ID: R006
- Start Time: 2026-01-15T14:00:00
- End Time: 2026-01-15T16:00:00
- Number of Attendees: 3
- Meeting Title: Team Discussion

Please attempt the booking and show me what happens when I don't have sufficient access permissions.""",

    "room_unavailable": """Book a conference room that has conflicts:
- Employee ID: E001
- Room ID: R001
- Start Time: 2026-01-15T02:30:00 (This conflicts with existing booking)
- End Time: 2026-01-15T03:30:00
- Number of Attendees: 5
- Meeting Title: Emergency Meeting

Please check availability and show me the conflicting bookings.""",

    "duration_exceeds_limit": """Try booking a room for longer than my access level allows:
- Employee ID: E004 (BASIC access, max 2 hours)
- Room ID: R001
- Start Time: 2026-01-15T10:00:00
- End Time: 2026-01-15T14:00:00 (4 hours total)
- Number of Attendees: 5
- Meeting Title: Extended Workshop

Show me the duration validation error.""",

    "insufficient_capacity": """Try booking a room without enough capacity:
- Employee ID: E001
- Room ID: R006 (Capacity: 5 people)
- Start Time: 2026-01-16T10:00:00
- End Time: 2026-01-16T12:00:00
- Number of Attendees: 8
- Meeting Title: Large Team Meeting

Show me the capacity validation error.""",

    "user_rejection": """Book a room and then reject the confirmation:
- Employee ID: E002
- Room ID: R002
- Start Time: 2026-01-15T14:00:00
- End Time: 2026-01-15T16:00:00
- Number of Attendees: 8
- Meeting Title: Product Review

When asked to confirm, please respond with NO and show that no record is created.""",

    "back_to_back_bookings": """Try booking a room with back-to-back bookings:
- Employee ID: E001
- Room ID: R001
- Start Time: 2026-01-15T03:00:00 (Only 30 minutes after existing booking)
- End Time: 2026-01-15T04:00:00
- Number of Attendees: 5
- Meeting Title: Quick Sync

Show me how the 15-minute buffer prevents back-to-back bookings."""
}