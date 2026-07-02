"""
Conference Room Booking Agent — Tool Definitions & Agent Configuration

Centralises two things used across the project:

1. TOOL_DEFINITIONS
   JSON-schema descriptions of every tool the agent exposes.  These are the
   canonical contracts imported by the Lambda handler (lambda_handler.py) and
   can be registered directly with Bedrock Agents or any Strands Agent that
   wraps this service.  Each schema maps 1-to-1 with a method on ToolExecutor
   in booking_agent.py.

2. AGENT_CONFIG
   Runtime configuration for the Bedrock AgentCore deployment: model ID,
   system instructions, tool list, and generation parameters.  The
   instructions encode the full booking workflow and the per-access-level
   booking limits so the model always follows the correct business rules.

Model choice — amazon.nova-micro-v1:0
   Nova Micro is the lowest-latency, lowest-cost Bedrock model that supports
   structured tool-calling.  It is well-suited to this task because every
   decision is deterministic (access hierarchy lookups, time arithmetic,
   capacity comparisons) and the model's role is primarily orchestration and
   natural-language summarisation rather than open-ended reasoning.
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


# Agent configuration for Bedrock AgentCore
# "model" updated to Amazon Nova Micro — the lowest-cost Bedrock model
# suitable for structured tool-calling/reasoning tasks like this one.
# See the module docstring above: this dict is currently unused by the
# live pipeline in main.py/booking_agent.py.
AGENT_CONFIG = {
    "agentName": "ConferenceRoomBookingAgent",
    "description": "Multi-agent system for conference room booking with access control, availability checking, and human-in-the-loop confirmation",
    "model": "amazon.nova-micro-v1:0",  # Amazon Nova Micro — low-cost Bedrock model
    "tools": TOOL_DEFINITIONS,
    "instructions": """You are an intelligent Conference Room Booking Assistant. Your role is to help employees book conference rooms efficiently.

WORKFLOW:
1. First, verify the employee has access permissions for the requested room
2. Check if the room is available for the requested time slot
3. Calculate the meeting duration and ensure it's within the employee's booking limits
4. Validate that the room has sufficient capacity for the attendee count
5. Get detailed room information for confirmation
6. Present a booking summary to the employee for confirmation
7. Only create the booking after receiving explicit confirmation

IMPORTANT RULES:
- Always verify access permissions FIRST before any other checks
- Always check room availability including the 15-minute buffer
- Always validate meeting duration against access level limits
- Always ensure room capacity is sufficient
- Present a clear summary before asking for confirmation
- Only save to database after human confirmation
- If the user says NO, cancel without saving any record
- Handle all edge cases gracefully with clear error messages

BOOKING LIMITS BY ACCESS LEVEL:
- BASIC: 2 hours max per booking
- STANDARD: 4 hours max per booking
- PREMIUM: 8 hours max per booking
- EXECUTIVE: 24 hours max per booking

When presenting the booking summary, include:
- Room name and capacity
- Room features available
- Start time and end time
- Calculated duration
- Number of attendees
- Meeting title

Ask the employee to confirm with a YES/NO response.""",
    "maxTokens": 4096,
    "temperature": 0.5
}


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