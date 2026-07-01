"""
Bedrock Agent Tools Configuration
Defines all available tools for the booking agent
"""

TOOL_DEFINITIONS = [
    {
        "toolName": "verify_employee_access",
        "description": "Verifies if an employee has access to book a specific conference room based on their access level and room requirements",
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "employee_id": {
                        "type": "string",
                        "description": "The employee ID (e.g., E001)"
                    },
                    "room_id": {
                        "type": "string",
                        "description": "The conference room ID (e.g., R001)"
                    }
                },
                "required": ["employee_id", "room_id"]
            }
        }
    },
    {
        "toolName": "check_room_availability",
        "description": "Checks if a conference room is available for a requested time slot, considering existing bookings and 15-minute buffer time",
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "room_id": {
                        "type": "string",
                        "description": "The conference room ID (e.g., R001)"
                    },
                    "start_time": {
                        "type": "string",
                        "description": "Meeting start time in ISO 8601 format (e.g., 2026-01-16T09:00:00)"
                    },
                    "end_time": {
                        "type": "string",
                        "description": "Meeting end time in ISO 8601 format (e.g., 2026-01-16T11:00:00)"
                    }
                },
                "required": ["room_id", "start_time", "end_time"]
            }
        }
    },
    {
        "toolName": "calculate_meeting_duration",
        "description": "Calculates the duration of a meeting and validates it against the employee's access level time limits",
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "start_time": {
                        "type": "string",
                        "description": "Meeting start time in ISO 8601 format"
                    },
                    "end_time": {
                        "type": "string",
                        "description": "Meeting end time in ISO 8601 format"
                    },
                    "access_level": {
                        "type": "string",
                        "enum": ["BASIC", "STANDARD", "PREMIUM", "EXECUTIVE"],
                        "description": "Employee's access level for time limit checking"
                    }
                },
                "required": ["start_time", "end_time", "access_level"]
            }
        }
    },
    {
        "toolName": "get_room_details",
        "description": "Retrieves comprehensive details about a conference room including capacity, location, features, and amenities",
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "room_id": {
                        "type": "string",
                        "description": "The conference room ID (e.g., R001)"
                    }
                },
                "required": ["room_id"]
            }
        }
    },
    {
        "toolName": "validate_attendee_count",
        "description": "Validates that the number of attendees does not exceed the room's capacity",
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "room_id": {
                        "type": "string",
                        "description": "The conference room ID (e.g., R001)"
                    },
                    "attendee_count": {
                        "type": "integer",
                        "description": "Number of people attending the meeting"
                    }
                },
                "required": ["room_id", "attendee_count"]
            }
        }
    },
    {
        "toolName": "create_booking",
        "description": "Creates a new conference room booking in the database with all required details",
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "employee_id": {
                        "type": "string",
                        "description": "Employee ID making the booking"
                    },
                    "room_id": {
                        "type": "string",
                        "description": "Conference room ID"
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
                        "description": "Number of attendees"
                    },
                    "meeting_title": {
                        "type": "string",
                        "description": "Title or purpose of the meeting"
                    }
                },
                "required": ["employee_id", "room_id", "start_time", "end_time", "attendee_count", "meeting_title"]
            }
        }
    }
]


AGENT_CONFIG = {
    "agentName": "ConferenceRoomBookingAgent",
    "description": "Intelligent conference room booking assistant with multi-step verification",
    "agentAliasId": "AIDACKVF75FCK",
    "agentVersion": "DRAFT",
    "tools": TOOL_DEFINITIONS,
    "instructions": """You are an intelligent Conference Room Booking Assistant. 

Your primary responsibility is to help employees book conference rooms efficiently and ensure all requirements are met.

## Booking Workflow

When processing a booking request, follow this systematic approach:

1. **Verify Employee Access**: Always start by verifying that the employee has the necessary access level to book the requested room
2. **Check Availability**: Ensure the room is available for the requested time slot (accounting for 15-minute buffers)
3. **Calculate Duration**: Verify the meeting duration doesn't exceed limits for the employee's access level
4. **Validate Capacity**: Confirm the room can accommodate all attendees
5. **Get Room Details**: Retrieve complete room information to present to the user
6. **Present Summary**: Show the booking details to the user for confirmation

## Access Level Hierarchy

- **BASIC** (Level 0): Max 2-hour bookings, access to basic rooms only
- **STANDARD** (Level 1): Max 4-hour bookings, access to standard and basic rooms
- **PREMIUM** (Level 2): Max 8-hour bookings, access to premium and below
- **EXECUTIVE** (Level 3): Max 24-hour bookings, access to all rooms

## Important Rules

- Always enforce the 15-minute buffer between consecutive bookings
- Reject bookings that exceed the employee's time allocation
- Verify room capacity before confirming
- Never skip access verification steps
- Provide clear, actionable error messages when bookings cannot be processed

## Response Format

Always provide structured responses with:
- Clear status (success/failure)
- Specific error reasons when applicable
- Room details in confirmation summaries
- Booking confirmation with booking ID when successful

## Error Handling

When errors occur:
1. Identify which step failed
2. Provide the specific reason
3. Suggest corrective actions
4. Maintain professional tone in all communications
"""
}


EXECUTION_PATTERNS = {
    "sequential": {
        "description": "Sequential execution - validates all conditions before confirmation",
        "steps": [
            "verify_employee_access",
            "check_room_availability",
            "calculate_meeting_duration",
            "validate_attendee_count",
            "get_room_details",
            "present_confirmation_summary"
        ],
        "use_when": "Standard booking flow, maximum safety"
    },
    "parallel": {
        "description": "Parallel execution - optimizes speed by running non-dependent checks simultaneously",
        "concurrent_phase": ["verify_employee_access", "check_room_availability"],
        "sequential_phase": [
            "calculate_meeting_duration",
            "validate_attendee_count",
            "get_room_details",
            "present_confirmation_summary"
        ],
        "use_when": "Time is critical, parallel checks can run independently"
    }
}


DATABASE_SCHEMA = {
    "Employees": {
        "PrimaryKey": "EmployeeID",
        "Attributes": {
            "EmployeeID": "String (E001, E002, ...)",
            "Name": "String",
            "Email": "String",
            "Department": "String",
            "AccessLevel": "String (BASIC|STANDARD|PREMIUM|EXECUTIVE)",
            "CreatedAt": "ISO 8601 String"
        }
    },
    "ConferenceRooms": {
        "PrimaryKey": "RoomID",
        "Attributes": {
            "RoomID": "String (R001, R002, ...)",
            "RoomName": "String",
            "Capacity": "Number",
            "Location": "String",
            "Floor": "String",
            "RequiredAccessLevel": "String",
            "Amenities": "String",
            "CreatedAt": "ISO 8601 String"
        }
    },
    "Bookings": {
        "PrimaryKey": ["RoomID", "StartTime"],
        "Attributes": {
            "RoomID": "String (Partition Key)",
            "StartTime": "ISO 8601 String (Sort Key)",
            "BookingID": "UUID String",
            "EmployeeID": "String",
            "EndTime": "ISO 8601 String",
            "AttendeeCount": "Number",
            "MeetingTitle": "String",
            "BookingStatus": "String (CONFIRMED|CANCELLED|PENDING)",
            "CreatedAt": "ISO 8601 String",
            "UpdatedAt": "ISO 8601 String"
        }
    },
    "RoomFeatures": {
        "PrimaryKey": ["RoomID", "FeatureName"],
        "Attributes": {
            "RoomID": "String (Partition Key)",
            "FeatureName": "String (Sort Key)",
            "AddedAt": "ISO 8601 String"
        }
    },
    "AccessLevels": {
        "PrimaryKey": "AccessLevelID",
        "Attributes": {
            "AccessLevelID": "String (BASIC|STANDARD|PREMIUM|EXECUTIVE)",
            "Name": "String",
            "Description": "String",
            "MaxBookingHours": "Number",
            "Priority": "Number"
        }
    }
}


PROMPT_TEMPLATES = {
    "sequential": """
Process the booking request using SEQUENTIAL execution:

1. First, verify the employee '{employee_id}' has access to room '{room_id}'
2. Then, check if room '{room_id}' is available from {start_time} to {end_time}
3. Calculate the meeting duration and validate it against the access level limits
4. Validate that {attendee_count} attendees don't exceed room capacity
5. Get complete details for room '{room_id}'
6. Present a summary to the user for confirmation

Only proceed to the next step if the current step succeeds.
""",
    "parallel": """
Process the booking request using PARALLEL execution:

1. Simultaneously verify employee access AND check room availability
2. Then proceed with duration calculation, capacity validation, and room details
3. Present a summary to the user for confirmation

This approach optimizes speed by running independent checks concurrently.
""",
    "happy_path": """
Employee E002 (Bob Smith, PREMIUM access) wants to book room R001 (Innovation Hub) from 09:00 to 11:00 for 8 people for a team meeting.

Expected flow:
- ✓ Access verified (PREMIUM >= BASIC)
- ✓ Room available (no conflicts)
- ✓ Duration OK (2 hours <= 8 hour limit)
- ✓ Capacity OK (8 <= 20)
- ✓ Room details retrieved
- ✓ Summary presented for confirmation
- ✓ Booking confirmed in database
""",
    "access_denied": """
Employee E004 (David Wilson, BASIC access) wants to book room R003 (Executive Suite, requires PREMIUM).

Expected flow:
- ✗ Access denied (BASIC < PREMIUM required)
- Return error with specific access level mismatch message
""",
    "unavailable": """
Employee E001 (Alice Johnson) wants to book room R001 from 02:30 to 03:30, but a confirmed booking exists from 02:00 to 03:00.

Expected flow:
- ✓ Access verified
- ✗ Availability check fails (conflict within 15-minute buffer)
- Return error with conflict details and alternative times
""",
    "duration_exceeded": """
Employee E003 (Carol Davis, STANDARD access) wants to book a room for 6 hours, but STANDARD is limited to 4 hours max.

Expected flow:
- ✓ Access verified
- ✓ Room available
- ✗ Duration exceeds limit (6 > 4)
- Return error with duration limit information
""",
    "capacity_exceeded": """
Employee E002 wants to book room R005 (Client Meeting Room, capacity 8) for 12 people.

Expected flow:
- ✓ Access verified
- ✓ Room available
- ✓ Duration OK
- ✗ Capacity check fails (12 > 8)
- Return error with capacity information
""",
    "human_confirmation": """
After all validations pass, present the booking summary to the user:

Room: Innovation Hub
Capacity: 20 people
Features: [list features]
Location: Building A, Floor 2
Start: 2026-01-16 09:00:00
End: 2026-01-16 11:00:00
Duration: 2 hours 0 minutes
Attendees: 8 people
Meeting: Team Meeting

Question: "Do you want to confirm this booking?"
Options: [YES] or [NO]

If YES: Create database record with status CONFIRMED
If NO: Cancel without creating record, return cancelled status
"""
}