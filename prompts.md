# Sample Prompts — Conference Room Booking Agent

All payloads below were run live against the deployed `conference_booking_agent_v2` AgentCore
Runtime and produced the responses shown (lightly reformatted for readability). Seed data
reference:

| Employee | Access Level | Max booking |
|---|---|---|
| E001 Alice Johnson | EXECUTIVE | 24h |
| E002 Bob Smith | PREMIUM | 8h |
| E003 Carol Davis | STANDARD | 4h |
| E004 David Wilson | BASIC | 2h |

| Room | Capacity | Required access |
|---|---|---|
| R001 Innovation Hub | 20 | BASIC |
| R003 Executive Suite | 10 | PREMIUM |
| R004 Training Center | 30 | BASIC |

**Windows PowerShell note:** escape inner double quotes with backslashes, e.g.
`agentcore invoke '{\"employee_id\": \"E001\", ...}'`.

---

## 1. Happy Path (Sequential Execution)

Employee lookup → access verification → availability check → duration calculation →
confirmation prompt → booking creation, each step blocked on the previous.

**Step 1 — request the booking:**
```json
{
  "action": "sequential",
  "employee_id": "E001",
  "room_id": "R001",
  "start_time": "2026-07-02T15:00:00",
  "end_time": "2026-07-02T16:00:00",
  "attendee_count": 5,
  "meeting_title": "Team Sync"
}
```

**Response:**
```json
{
  "status": "PENDING_CONFIRMATION",
  "confirmation_summary": {
    "room_name": "Innovation Hub",
    "room_capacity": 20,
    "features": ["High Speed Internet", "Projector", "Video Conferencing", "Whiteboard"],
    "location": "Building A, Floor 2",
    "start_time": "2026-07-02T15:00:00",
    "end_time": "2026-07-02T16:00:00",
    "duration_hours": 1.0,
    "attendee_count": 5,
    "meeting_title": "Team Sync"
  },
  "execution_mode": "sequential",
  "error": null
}
```

**Step 2 — confirm (YES):**
```json
{
  "action": "confirm",
  "employee_id": "E001",
  "room_id": "R001",
  "start_time": "2026-07-02T15:00:00",
  "end_time": "2026-07-02T16:00:00",
  "attendee_count": 5,
  "meeting_title": "Team Sync",
  "confirmed": true
}
```

**Response:**
```json
{
  "status": "CONFIRMED",
  "booking_id": "7699262b-325e-414f-8c78-6cc3008388f7",
  "created_at": "2026-07-01T04:57:19.083043",
  "message": "Booking confirmed and saved",
  "database_record_created": true,
  "error": null
}
```

---

## 2. Parallel Execution

Access check and availability check run concurrently (via `ThreadPoolExecutor`); results are
merged before duration and capacity validation.

**Request:**
```json
{
  "action": "parallel",
  "employee_id": "E001",
  "room_id": "R004",
  "start_time": "2026-07-04T09:00:00",
  "end_time": "2026-07-04T10:00:00",
  "attendee_count": 6,
  "meeting_title": "Parallel Test"
}
```

**Response:**
```json
{
  "workflow": "parallel",
  "status": "PENDING_CONFIRMATION",
  "parallel_execution_note": "Access check and availability check ran concurrently via ThreadPoolExecutor; results merged before duration and capacity validation.",
  "confirmation_summary": {
    "room_name": "Training Center",
    "capacity": 30,
    "features": ["Multiple Screens", "Projector", "Recording Capability", "Whiteboard"],
    "start_time": "2026-07-04T09:00:00",
    "end_time": "2026-07-04T10:00:00",
    "duration_hours": 1.0,
    "duration_minutes": 0.0,
    "attendee_count": 6,
    "meeting_title": "Parallel Test"
  },
  "access_result": {
    "access_granted": true,
    "employee_name": "Alice Johnson",
    "access_level": "EXECUTIVE",
    "room_required_level": "BASIC",
    "error": null
  },
  "availability_result": {
    "available": true,
    "conflicts": [],
    "buffer_minutes": 15,
    "error": null
  },
  "duration_result": {
    "duration_hours": 1.0,
    "duration_minutes": 0.0,
    "max_allowed_hours": 24,
    "within_limit": true,
    "error": null
  },
  "attendee_result": {
    "capacity_sufficient": true,
    "room_capacity": 30,
    "attendee_count": 6,
    "error": null
  }
}
```

---

## 3. Insufficient Access Permissions

E004 (BASIC access) attempts to book R003 (requires PREMIUM).

**Request:**
```json
{
  "employee_id": "E004",
  "room_id": "R003",
  "start_time": "2026-07-03T14:00:00",
  "end_time": "2026-07-03T15:00:00",
  "attendee_count": 4,
  "meeting_title": "Access Test"
}
```

**Response:**
```json
{
  "status": "FAILED",
  "error": "Access level BASIC insufficient for room R003",
  "step_failed": "verify_access"
}
```

---

## 4. Room Unavailable

A second employee attempts to book a room/time slot that's already confirmed.

**Request:**
```json
{
  "employee_id": "E002",
  "room_id": "R001",
  "start_time": "2026-07-02T15:00:00",
  "end_time": "2026-07-02T16:00:00",
  "attendee_count": 3,
  "meeting_title": "Conflict Test"
}
```

**Response:**
```json
{
  "status": "FAILED",
  "error": "1 booking conflict(s) found",
  "conflicts": [
    {
      "booking_id": "7699262b-325e-414f-8c78-6cc3008388f7",
      "existing_start": "2026-07-02T15:00:00",
      "existing_end": "2026-07-02T16:00:00"
    }
  ],
  "step_failed": "check_availability"
}
```

---

## 5. Booking Duration Exceeding Limit

E004 (BASIC, 2-hour max) attempts a 3-hour booking.

**Request:**
```json
{
  "employee_id": "E004",
  "room_id": "R001",
  "start_time": "2026-07-03T09:00:00",
  "end_time": "2026-07-03T12:00:00",
  "attendee_count": 4,
  "meeting_title": "Long Meeting Test"
}
```

**Response:**
```json
{
  "status": "FAILED",
  "error": "Duration 3.0h exceeds limit of 2h for BASIC",
  "step_failed": "calculate_duration"
}
```

---

## 6. Human Rejection (User says NO)

Same flow as the Happy Path, but the employee declines at the confirmation step. No database
record should be created.

**Request:**
```json
{
  "action": "confirm",
  "employee_id": "E002",
  "room_id": "R002",
  "start_time": "2026-07-03T10:00:00",
  "end_time": "2026-07-03T11:00:00",
  "attendee_count": 4,
  "meeting_title": "Cancelled Test",
  "confirmed": false
}
```

**Response:**
```json
{
  "status": "CANCELLED",
  "message": "Booking cancelled by user",
  "database_record_created": false
}
```

Verified via `aws dynamodb get-item` on `(RoomID: R002, StartTime: 2026-07-03T10:00:00)` —
no item exists.

---

## Bonus: Back-to-Back Booking (15-Minute Buffer)

Not one of the six required scenarios explicitly, but demonstrates the buffer logic inside
Availability Check / Computation: a request starting only 10 minutes after an existing booking
ends (no direct time overlap) is still correctly rejected, because it falls inside the 15-minute
buffer.

**Request** (existing booking on R001 ends at 16:00; this one starts at 16:10):
```json
{
  "employee_id": "E003",
  "room_id": "R001",
  "start_time": "2026-07-02T16:10:00",
  "end_time": "2026-07-02T17:00:00",
  "attendee_count": 4,
  "meeting_title": "Buffer Test"
}
```

**Response:**
```json
{
  "status": "FAILED",
  "error": "1 booking conflict(s) found",
  "conflicts": [
    {
      "booking_id": "7699262b-325e-414f-8c78-6cc3008388f7",
      "existing_start": "2026-07-02T15:00:00",
      "existing_end": "2026-07-02T16:00:00"
    }
  ],
  "step_failed": "check_availability"
}
```