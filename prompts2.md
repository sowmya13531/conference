# 1. SEQUENTIAL — Happy path
# Turn 1 — run this, wait for summary response
python invoke_agent.py "I am employee E001. I want to book the Innovation Hub room R001 on 2026-07-20 from 10am to 12pm for a Team Sync meeting with 5 attendees. Use sequential steps." --session seq-demo-1

# Turn 2 — only after Turn 1 responds with summary
python invoke_agent.py "Yes, confirm the booking." --session seq-demo-1



# 2. PARALLEL
# Turn 1
python invoke_agent.py "I am E003. Book Training Center R004 on 2026-07-21 from 2pm to 3:30pm for Quarterly Planning, 12 attendees. Please check my access and room availability at the same time in parallel." --session par-demo-1
# Turn 2
python invoke_agent.py "Yes, go ahead and confirm." --session par-demo-1



# 3. HUMAN-IN-THE-LOOP (reject)
# Turn 1
python invoke_agent.py "I am E002. Book room R004 on 2026-07-22 from 2pm to 4pm for Product Review with 8 attendees." --session hitl-demo-1
# Turn 2 — reject it
python invoke_agent.py "No, cancel that. I don't want to book." --session hitl-demo-1



# 4. DATABASE RETRIEVAL (access denied shows live DynamoDB read)
# Single turn — shows live DynamoDB read of employee + room access levels
python invoke_agent.py "I am employee E004. I want to book the Executive Suite room R003 on 2026-07-22 from 2pm to 4pm for Team Discussion with 3 attendees." --session db-demo-1



# 5. COMPUTATION (duration limit)
# Single turn — E004 is BASIC (max 2h), requesting 4h
python invoke_agent.py "I am E004. Book Innovation Hub R001 on 2026-07-22 from 10am to 2pm for Extended Workshop with 5 people." --session comp-demo-1


# 6. DATA PERSISTENCE (confirm booking and verify in DynamoDB console)
# Turn 1
python invoke_agent.py "I am E001. Book Innovation Hub R001 on 2026-07-25 from 10am to 11am for Final Demo with 5 attendees." --session persist-demo-1
# Turn 2
python invoke_agent.py "Yes, confirmed." --session persist-demo-1

# Then open AWS Console → DynamoDB → Bookings table → verify CONFIRMED record


==============================================================================
==============================================================================
==============================================================================




# Sample Prompts — Conference Room Booking Agent

These are **natural-language** prompts sent to the deployed AgentCore Runtime via the
`prompt` payload field, routed through a `strands.Agent` (Bedrock Claude/Nova model) that
decides which tools to call and in what order. Scenarios that involve confirmation are
multi-turn — reuse the same `session_id` across turns of one conversation.

Invoke shape:
```
agentcore invoke '{\"prompt\": \"<message>\"}' --session-id "<id>-0000000000000000000000"
```
A new `session_id` starts a fresh conversation with no memory of prior turns.

> **Windows PowerShell:** use `'{\"prompt\": \"...\"}' ` (backslash-escape inner quotes,
> single-quote the outer JSON string). Session IDs must be **33+ characters** — examples
> below are already padded with zeros.

---

## Seed Data Reference

### Employees
| ID | Name | Access Level | Max Booking |
|---|---|---|---|
| E001 | Alice Johnson | EXECUTIVE | 24h |
| E002 | Bob Smith | PREMIUM | 8h |
| E003 | Carol Davis | STANDARD | 4h |
| E004 | David Wilson | BASIC | 2h |
| E005 | Emma Martinez | STANDARD | 4h |

### Conference Rooms
| ID | Name | Capacity | Required Access | Features |
|---|---|---|---|---|
| R001 | Innovation Hub | 20 | BASIC | Projector, Video Conferencing, Whiteboard, High Speed Internet |
| R002 | Board Room | 15 | STANDARD | Projector, Video Conferencing, Speakerphone, 4K Display |
| R003 | Executive Suite | 10 | PREMIUM | Video Conferencing, Secure Phone Lines, Premium Sound, 8K Display |
| R004 | Training Center | 30 | BASIC | Projector, Multiple Screens, Whiteboard, Recording Capability |
| R005 | Client Meeting Room | 8 | STANDARD | Video Conferencing, Projector, Coffee Station, 4K Display |
| R006 | C-Suite Presidential Suite | 5 | EXECUTIVE | Premium AV, Video Conferencing, Secure Phone Lines, Smart Controls |

### Pre-Seeded Bookings (use these for conflict/buffer tests)
| Booking ID | Room | Start Time | End Time | Employee |
|---|---|---|---|---|
| B001 | R001 Innovation Hub | 2026-01-15T11:00:00 | 2026-01-15T12:00:00 | E001 |
| B002 | R002 Board Room | 2026-01-15T13:00:00 | 2026-01-15T15:00:00 | E002 |
| B003 | R004 Training Center | 2026-01-15T10:00:00 | 2026-01-15T11:00:00 | E003 |

---

## 1. Happy Path — Sequential Execution ✅

Employee lookup → access verification → availability check → duration calculation →
capacity check → summary presented → employee confirms → booking saved to DynamoDB.
Each step waits for the previous to complete (sequential).

**Turn 1 — booking request:**
```
agentcore invoke '{\"prompt\": \"Hi, I am employee E001. I want to book the Innovation Hub R001 on 2026-07-26 from 10am to 12pm for a Team Sync meeting with 5 attendees.\"}' --session-id "happy-path-1-0000000000000000000000"
```
**Expected:** Agent verifies E001 (EXECUTIVE access), checks R001 availability, calculates
2h duration (within 24h EXECUTIVE limit), validates 5 < 20 capacity, then presents
full booking summary (room name, capacity, features, times, duration, attendee count)
and asks: "Do you confirm this booking? (YES / NO)"

**Turn 2 — confirm:**
```
agentcore invoke '{\"prompt\": \"Yes, please confirm it.\"}' --session-id "happy-path-1-0000000000000000000000"
```
**Expected:** Booking written to DynamoDB with BookingStatus = CONFIRMED. Agent replies
with a booking ID (UUID). Verify in AWS Console → DynamoDB → Bookings table.

---

## 2. Parallel Execution ✅

Access check and availability check run **concurrently** (both tool calls issued in the
same model turn), results merged before duration and capacity validation continue.

**Turn 1 — parallel booking request:**
```
agentcore invoke '{\"prompt\": \"Book Training Center R004 for employee E003 on 2026-07-27 from 2pm to 3:30pm, 12 attendees, title Quarterly Planning. Please check my access and room availability at the same time.\"}' --session-id "parallel-1-0000000000000000000000"
```
**Expected:** Agent calls `verify_employee_access` and `check_room_availability` together
in one turn (parallel), then runs duration and capacity checks, then shows summary.

**Turn 2 — confirm:**
```
agentcore invoke '{\"prompt\": \"Yes, go ahead.\"}' --session-id "parallel-1-0000000000000000000000"
```
**Expected:** Booking confirmed and saved to DynamoDB.

**Alternative — Structured JSON (explicitly triggers ThreadPoolExecutor parallel path):**
```
agentcore invoke '{\"action\": \"parallel\", \"employee_id\": \"E001\", \"room_id\": \"R004\", \"start_time\": \"2026-07-28T09:00:00\", \"end_time\": \"2026-07-28T10:00:00\", \"attendee_count\": 6, \"meeting_title\": \"Parallel Test\"}'
```
**Expected:** Response includes `"parallel_execution_note"` confirming ThreadPoolExecutor
was used, and shows `access_result` + `availability_result` side by side.

---

## 3. Insufficient Access Permissions ✅

Agent reads employee access level and room requirement from DynamoDB, denies booking
when employee level is below room requirement. Does not proceed to further checks.

**E004 (BASIC) trying R003 (requires PREMIUM):**
```
agentcore invoke '{\"prompt\": \"I am employee E004. I would like to book the Executive Suite R003 on 2026-07-15 from 2pm to 4pm for 3 people, meeting title Team Discussion.\"}' --session-id "access-denied-1-0000000000000000000000"
```
**Expected:** Agent reads E004 = BASIC, R003 requires PREMIUM. Reports access denied.
Does NOT proceed to availability, duration, or capacity checks.

**E003 (STANDARD) trying R003 (requires PREMIUM):**
```
agentcore invoke '{\"prompt\": \"I am E003. Book Executive Suite R003 on 2026-07-15 from 10am to 12pm for Client Call with 5 people.\"}'
```
**Expected:** STANDARD < PREMIUM. Access denied at step 1.

**E002 (PREMIUM) trying R006 (requires EXECUTIVE):**
```
agentcore invoke '{\"prompt\": \"I am E002. Book the C-Suite Presidential Suite R006 on 2026-07-15 from 10am to 11am for Board Call with 3 people.\"}'
```
**Expected:** PREMIUM < EXECUTIVE. Access denied at step 1.

---

## 4. Room Unavailable ✅

Agent queries DynamoDB Bookings table for existing CONFIRMED bookings and detects
a time overlap with the requested slot.

**Conflict with seeded booking B001 (R001 is booked 11:00–12:00 on 2026-01-15):**
```
agentcore invoke '{\"prompt\": \"Book Innovation Hub R001 for employee E001 on 2026-01-15 from 11:30am to 12:30pm, 5 attendees, Emergency Meeting.\"}' --session-id "unavailable-1-0000000000000000000000"
```
**Expected:** Agent finds conflict with B001 (11:00–12:00). Reports room unavailable
and lists the conflicting booking details read from DynamoDB.

**Conflict with seeded booking B003 (R004 is booked 10:00–11:00 on 2026-01-15):**
```
agentcore invoke '{\"prompt\": \"Book Training Center R004 for employee E001 on 2026-01-15 from 10:30am to 11:30am, 10 attendees, Overlap Test.\"}'
```
**Expected:** Overlap with B003 (10:00–11:00). Room unavailable.

---

## 5. Booking Duration Exceeds Limit ✅

Agent calculates meeting duration in hours and minutes, then checks it against the
maximum allowed for the employee's access level. Stops if limit is exceeded.

**E004 (BASIC = 2h max) requesting 4 hours:**
```
agentcore invoke '{\"prompt\": \"I am E004. Book Innovation Hub R001 on 2026-07-15 from 10am to 2pm for Extended Workshop with 5 people.\"}'
```
**Expected:** Duration = 4h. BASIC limit = 2h. Agent reports duration exceeds limit
and does NOT proceed to confirmation.

**E003 (STANDARD = 4h max) requesting 6 hours:**
```
agentcore invoke '{\"prompt\": \"I am E003. Book Training Center R004 on 2026-07-15 from 9am to 3pm for All Day Training with 20 people.\"}'
```
**Expected:** Duration = 6h. STANDARD limit = 4h. Duration check fails.

---

## 6. Human-in-the-Loop — User says NO ✅

Agent presents full booking summary and waits for explicit YES/NO. If NO, booking
is cancelled without writing any record to DynamoDB.

**Turn 1 — booking request:**
```
agentcore invoke '{\"prompt\": \"Book Board Room R002 for E002 on 2026-07-22 from 2pm to 4pm, 8 attendees, Product Review.\"}' --session-id "rejection-1-0000000000000000000000"
```
**Expected:** Agent shows full booking summary and asks for YES/NO confirmation.

**Turn 2 — reject:**
```
agentcore invoke '{\"prompt\": \"No, cancel that. I changed my mind.\"}' --session-id "rejection-1-0000000000000000000000"
```
**Expected:** "Booking cancelled. No record has been saved."
Verify in DynamoDB → Bookings table → NO new entry for R002 on 2026-07-22.

---

## 7. Back-to-Back Booking — 15-Minute Buffer ✅

Agent blocks bookings that start within 15 minutes of an existing booking's end time,
even if the time slots don't literally overlap.

**B001 ends at 2026-01-15T12:00:00 — trying to book R001 at 12:10 (only 10 min gap):**
```
agentcore invoke '{\"prompt\": \"Book Innovation Hub R001 for E001 on 2026-01-15 from 12:10pm to 1:10pm, 5 attendees, Quick Sync.\"}' --session-id "back-to-back-1-0000000000000000000000"
```
**Expected:** Agent detects B001 ends at 12:00. Requested start 12:10 is within the
15-minute buffer. Reports conflict even though time slots don't overlap. Room blocked.

**Booking just outside the buffer (should succeed — 16 min gap):**
```
agentcore invoke '{\"prompt\": \"Book Innovation Hub R001 for E001 on 2026-01-15 from 12:16pm to 1:16pm, 5 attendees, Safe Sync.\"}' --session-id "buffer-ok-1-00000000000000000000000"
```
**Expected:** 12:16 is 16 minutes after B001 ends (12:00) — outside the 15-min buffer.
Room is available. Agent proceeds to show booking summary.

---

## 8. Cancellation ✅

Agent cancels an existing CONFIRMED booking, verifies the employee is the original
booker, and marks the record CANCELLED in DynamoDB (does not delete it).

**Step 1 — create a booking to cancel:**
```
agentcore invoke '{\"prompt\": \"I am E001. Book Training Center R004 on 2026-07-30 from 10am to 11am for Cancel Demo with 5 people.\"}' --session-id "cancel-setup-000000000000000000000"
```
```
agentcore invoke '{\"prompt\": \"Yes confirm.\"}' --session-id "cancel-setup-000000000000000000000"
```
**Expected:** Booking confirmed. Note the booking ID from the response.

**Step 2 — cancel it:**
```
agentcore invoke '{\"prompt\": \"I am E001. Please cancel my booking for Training Center R004 that starts at 2026-07-30T10:00:00.\"}' --session-id "cancel-1-0000000000000000000000"
```
**Expected:** Agent verifies E001 is the original booker, marks booking CANCELLED.
Verify in DynamoDB → Bookings table → BookingStatus changed to CANCELLED (record
still exists for audit trail, not deleted).

**Cancel already-cancelled booking (should fail gracefully):**
```
agentcore invoke '{\"prompt\": \"I am E001. Cancel my booking for Training Center R004 at 2026-07-30T10:00:00.\"}'
```
**Expected:** Agent reports "booking is already cancelled" — does not create a duplicate
or change the record again.

---

## 9. Data Persistence Verification ✅

Confirm a booking and verify the record in DynamoDB console.

**Turn 1:**
```
agentcore invoke '{\"prompt\": \"I am E001. Book Training Center R004 on 2026-07-31 from 2pm to 3pm for Final Demo Persistence Test with 5 attendees.\"}' --session-id "persist-demo-1-000000000000000000000"
```
**Turn 2:**
```
agentcore invoke '{\"prompt\": \"Yes, confirmed.\"}' --session-id "persist-demo-1-000000000000000000000"
```

**Verify in AWS Console:**
1. Open AWS Console → DynamoDB → Tables → Bookings → Explore items
2. Look for: `RoomID = R004`, `MeetingTitle = Final Demo Persistence Test`
3. Confirm fields: `BookingStatus = CONFIRMED`, `EmployeeID = E001`, `BookingID = <UUID>`

**No duplicate on re-run (idempotency check):**
```
agentcore invoke '{\"action\": \"sequential\", \"employee_id\": \"E001\", \"room_id\": \"R004\", \"start_time\": \"2026-07-31T14:00:00\", \"end_time\": \"2026-07-31T15:00:00\", \"attendee_count\": 5, \"meeting_title\": \"Final Demo Persistence Test\"}'
```
**Expected:** FAILED — availability check finds the existing booking, no duplicate created.

---

## Legacy Structured JSON Payloads

Bypass the LLM entirely for deterministic testing of tool logic. Useful for CI/regression
checks but does **not** satisfy the "Agent Framework: Strands / LLM: Bedrock" requirement
on its own — use the `prompt` payloads above for the actual assessment demonstration.

**Sequential:**
```
agentcore invoke '{\"action\": \"sequential\", \"employee_id\": \"E002\", \"room_id\": \"R002\", \"start_time\": \"2026-07-20T14:00:00\", \"end_time\": \"2026-07-20T16:00:00\", \"attendee_count\": 8, \"meeting_title\": \"Product Review\"}'
```

**Parallel:**
```
agentcore invoke '{\"action\": \"parallel\", \"employee_id\": \"E001\", \"room_id\": \"R004\", \"start_time\": \"2026-07-20T09:00:00\", \"end_time\": \"2026-07-20T10:00:00\", \"attendee_count\": 6, \"meeting_title\": \"Parallel Test\"}'
```

**Confirm YES:**
```
agentcore invoke '{\"action\": \"confirm\", \"employee_id\": \"E001\", \"room_id\": \"R004\", \"start_time\": \"2026-07-20T09:00:00\", \"end_time\": \"2026-07-20T10:00:00\", \"attendee_count\": 6, \"meeting_title\": \"Parallel Test\", \"confirmed\": true}'
```

**Confirm NO (human rejection):**
```
agentcore invoke '{\"action\": \"confirm\", \"employee_id\": \"E001\", \"room_id\": \"R004\", \"start_time\": \"2026-07-20T09:00:00\", \"end_time\": \"2026-07-20T10:00:00\", \"attendee_count\": 6, \"meeting_title\": \"Parallel Test\", \"confirmed\": false}'
```

**Cancel:**
```
agentcore invoke '{\"action\": \"cancel\", \"employee_id\": \"E001\", \"room_id\": \"R004\", \"start_time\": \"2026-07-20T09:00:00\"}'
```







==============================================================
==============================================================



# Conference Room Booking Agent — Complete Demo Guide
### Tachyon AIML Internship | AWS Track | Sowmya Kanithi

---

## Reference Data (from DynamoDB seed)

### Employees
| ID | Name | Access Level | Max Booking |
|---|---|---|---|
| E001 | Alice Johnson | EXECUTIVE | 24 hours |
| E002 | Bob Smith | PREMIUM | 8 hours |
| E003 | Carol Davis | STANDARD | 4 hours |
| E004 | David Wilson | BASIC | 2 hours |
| E005 | Emma Martinez | STANDARD | 4 hours |

### Rooms
| ID | Name | Capacity | Required Access | Features |
|---|---|---|---|---|
| R001 | Innovation Hub | 20 | BASIC | Projector, Video Conferencing, Whiteboard, High Speed Internet |
| R002 | Board Room | 15 | STANDARD | Projector, Video Conferencing, Speakerphone, 4K Display |
| R003 | Executive Suite | 10 | PREMIUM | Video Conferencing, Secure Phone Lines, Premium Sound, 8K Display |
| R004 | Training Center | 30 | BASIC | Projector, Multiple Screens, Whiteboard, Recording Capability |
| R005 | Client Meeting Room | 8 | STANDARD | Video Conferencing, Projector, Coffee Station, 4K Display |
| R006 | C-Suite Presidential Suite | 5 | EXECUTIVE | Premium AV, Video Conferencing, Secure Phone Lines, Smart Controls |

### Pre-seeded Bookings (conflict slots for testing)
| Booking | Room | Time Slot | Employee |
|---|---|---|---|
| B001 | R001 | 2026-01-15 11:00–12:00 | E001 |
| B002 | R002 | 2026-01-15 13:00–15:00 | E002 |
| B003 | R004 | 2026-01-15 10:00–11:00 | E003 |

---

## HOW TO RUN COMMANDS

### Format A — agentcore invoke (single turn, no session)
```
agentcore invoke '{\"prompt\": \"your message here\"}'
```

### Format B — agentcore invoke with session (multi-turn, YES/NO confirmation)
```
agentcore invoke '{\"prompt\": \"your message here\"}' --session-id "name-0000000000000000000000"
agentcore invoke '{\"prompt\": \"Yes, confirm.\"}' --session-id "name-0000000000000000000000"
```
> Session ID must be 33+ characters. Pad short names with zeros.

### Format C — python invoke_agent.py (same as B, easier on Windows)
```
python invoke_agent.py "your message here" --session name-1
python invoke_agent.py "Yes, confirm." --session name-1
```

### Format D — agentcore invoke structured JSON (bypasses LLM, direct tool call)
```
agentcore invoke '{\"action\": \"sequential\", \"employee_id\": \"E001\", \"room_id\": \"R001\", \"start_time\": \"2026-07-20T10:00:00\", \"end_time\": \"2026-07-20T12:00:00\", \"attendee_count\": 5, \"meeting_title\": \"Team Sync\"}'
```

---

# THE 6 REQUIRED DEMO PATTERNS

---

## PATTERN 1 — Sequential Execution ✅
> Each step waits for the previous: access → availability → duration → capacity → summary → confirm → book

### Natural Language (agentcore invoke with session)
```
# TURN 1 — sends booking request, agent runs all checks sequentially
agentcore invoke '{\"prompt\": \"I am employee E001. I want to book Innovation Hub R001 on 2026-07-20 from 10am to 12pm for a Team Sync meeting with 5 attendees.\"}' --session-id "seq-demo-1-0000000000000000000000"
```
**Expected:** Agent verifies E001 (EXECUTIVE), checks R001 availability, calculates 2h duration (within 24h limit), validates 5 < 20 capacity, then shows booking summary and asks YES/NO.

```
# TURN 2 — confirm booking, saved to DynamoDB
agentcore invoke '{\"prompt\": \"Yes, confirm the booking.\"}' --session-id "seq-demo-1-0000000000000000000000"
```
**Expected:** Booking written to DynamoDB with status CONFIRMED. Agent replies with a booking ID.

### Alternative — python invoke_agent.py
```
python invoke_agent.py "I am E001. Book Innovation Hub R001 on 2026-07-20 from 10am to 12pm for Team Sync with 5 people." --session seq-1
python invoke_agent.py "Yes, confirm." --session seq-1
```

### Alternative — Structured JSON (shows deterministic sequential flow)
```
agentcore invoke '{\"action\": \"sequential\", \"employee_id\": \"E001\", \"room_id\": \"R001\", \"start_time\": \"2026-07-20T10:00:00\", \"end_time\": \"2026-07-20T12:00:00\", \"attendee_count\": 5, \"meeting_title\": \"Team Sync\"}'
```
**Expected:** Returns `PENDING_CONFIRMATION` with full summary JSON showing each step result.

---

## PATTERN 2 — Parallel Execution ✅
> Access check AND availability check run simultaneously via ThreadPoolExecutor, merged before next steps

### Natural Language (agentcore invoke with session)
```
# TURN 1 — ask agent to check access and availability at the same time
agentcore invoke '{\"prompt\": \"I am E003. Book Training Center R004 on 2026-07-21 from 2pm to 3:30pm for Quarterly Planning with 12 attendees. Please check my access and room availability at the same time.\"}' --session-id "par-demo-1-0000000000000000000000"
```
**Expected:** Agent runs verify_employee_access + check_room_availability in one turn (parallel), then continues with duration and capacity checks, then shows summary.

```
# TURN 2
agentcore invoke '{\"prompt\": \"Yes, go ahead.\"}' --session-id "par-demo-1-0000000000000000000000"
```
**Expected:** Booking confirmed and saved to DynamoDB.

### Alternative — Structured JSON (explicitly triggers ThreadPoolExecutor parallel path)
```
agentcore invoke '{\"action\": \"parallel\", \"employee_id\": \"E001\", \"room_id\": \"R004\", \"start_time\": \"2026-07-21T14:00:00\", \"end_time\": \"2026-07-21T15:30:00\", \"attendee_count\": 6, \"meeting_title\": \"Parallel Test\"}'
```
**Expected:** Response includes `parallel_execution_note` confirming ThreadPoolExecutor was used, and shows `access_result` + `availability_result` side by side.

---

## PATTERN 3 — Human-in-the-Loop ✅
> Summary shown → Employee says NO → No record written to DynamoDB

### Natural Language — User says NO (agentcore invoke with session)
```
# TURN 1
agentcore invoke '{\"prompt\": \"I am E002. Book Board Room R002 on 2026-07-22 from 2pm to 4pm for Product Review with 8 attendees.\"}' --session-id "hitl-no-1-000000000000000000000000"
```
**Expected:** Agent shows full booking summary and asks "Do you confirm? YES/NO"

```
# TURN 2 — REJECT
agentcore invoke '{\"prompt\": \"No, cancel that. I changed my mind.\"}' --session-id "hitl-no-1-000000000000000000000000"
```
**Expected:** "Booking cancelled. No record has been saved." — verify in DynamoDB that NO record was written.

### Natural Language — User says YES (to show contrast)
```
# TURN 1
agentcore invoke '{\"prompt\": \"I am E002. Book Board Room R002 on 2026-07-23 from 10am to 12pm for Strategy Meeting with 8 attendees.\"}' --session-id "hitl-yes-1-00000000000000000000000"
```
```
# TURN 2 — CONFIRM
agentcore invoke '{\"prompt\": \"Yes, confirmed.\"}' --session-id "hitl-yes-1-00000000000000000000000"
```
**Expected:** Booking ID returned, record visible in DynamoDB Bookings table with BookingStatus = CONFIRMED.

---

## PATTERN 4 — Database Retrieval ✅
> Agent reads live DynamoDB — employee profile, room details, existing bookings, access levels

### 4a — Shows employee profile + room access level read
```
agentcore invoke '{\"prompt\": \"I am E004. I want to book Executive Suite R003 on 2026-07-22 from 2pm to 4pm for Team Discussion with 3 people.\"}'
```
**Expected:** Agent reads E004 from Employees table (BASIC), reads R003 from ConferenceRooms (requires PREMIUM), denies access — showing live DynamoDB reads of both employee and room.

### 4b — Shows existing bookings read (room unavailable)
```
agentcore invoke '{\"prompt\": \"I am E001. Book Innovation Hub R001 on 2026-01-15 from 11am to 12pm for Quick Sync with 5 people.\"}'
```
**Expected:** Agent queries Bookings table, finds seeded booking B001 (R001, 11:00–12:00), reports conflict with booking details from DynamoDB.

### 4c — Shows booking history / room catalogue
```
agentcore invoke '{\"prompt\": \"What are the details and features of room R003?\"}'
```
**Expected:** Agent calls get_room_details, returns Executive Suite details read live from ConferenceRooms + RoomFeatures tables.

---

## PATTERN 5 — Computation ✅
> Duration in hours/minutes, access level limit check, 15-minute buffer, capacity flag

### 5a — Duration exceeds access level limit
```
# E004 is BASIC (max 2h), requesting 4h — should fail duration check
agentcore invoke '{\"prompt\": \"I am E004. Book Innovation Hub R001 on 2026-07-22 from 10am to 2pm for Extended Workshop with 5 people.\"}'
```
**Expected:** Agent calculates 4h duration, checks BASIC limit = 2h, reports "Duration 4h exceeds limit of 2h for BASIC access level."

### 5b — Back-to-back booking (15-minute buffer)
```
# B001 seeded booking: R001, 11:00-12:00
# Trying to book 12:05-13:05 — within 15-min buffer of B001's end time
agentcore invoke '{\"prompt\": \"I am E001. Book Innovation Hub R001 on 2026-01-15 from 12:05pm to 1:05pm for Quick Follow-up with 5 people.\"}'
```
**Expected:** Agent detects conflict because 12:05 is within 15 minutes of existing booking end (12:00). Reports buffer conflict even though times don't literally overlap.

### 5c — Capacity insufficient
```
# R005 Client Meeting Room capacity = 8, requesting 15 attendees
agentcore invoke '{\"prompt\": \"I am E003. Book Client Meeting Room R005 on 2026-07-22 from 10am to 11am for Team Meeting with 15 attendees.\"}'
```
**Expected:** Agent validates 15 > 8 capacity, reports "15 attendees exceed capacity of 8."

### 5d — All computations passing (happy path showing all checks)
```
agentcore invoke '{\"prompt\": \"I am E002. Book Executive Suite R003 on 2026-07-22 from 10am to 12pm for Strategy Session with 8 people.\"}' --session-id "comp-pass-1-000000000000000000000"
agentcore invoke '{\"prompt\": \"Yes.\"}' --session-id "comp-pass-1-000000000000000000000"
```
**Expected:** E002 (PREMIUM) can book R003 (requires PREMIUM). 2h within 8h limit. 8 = capacity of 10. All pass.

---

## PATTERN 6 — Data Persistence ✅
> Record written to DynamoDB with CONFIRMED status. No duplicates on re-run.

### 6a — Create booking and verify in DynamoDB
```
# TURN 1
agentcore invoke '{\"prompt\": \"I am E001. Book Training Center R004 on 2026-07-25 from 10am to 11am for Final Demo with 5 attendees.\"}' --session-id "persist-1-000000000000000000000000"

# TURN 2
agentcore invoke '{\"prompt\": \"Yes, confirmed.\"}' --session-id "persist-1-000000000000000000000000"
```
**After confirming:** Go to AWS Console → DynamoDB → Tables → Bookings → Explore items
Look for: RoomID=R004, BookingStatus=CONFIRMED, MeetingTitle=Final Demo

### 6b — No duplicate on re-run (idempotency)
Run the SAME booking again with same room + time:
```
agentcore invoke '{\"action\": \"sequential\", \"employee_id\": \"E001\", \"room_id\": \"R004\", \"start_time\": \"2026-07-25T10:00:00\", \"end_time\": \"2026-07-25T11:00:00\", \"attendee_count\": 5, \"meeting_title\": \"Final Demo\"}'
```
**Expected:** Returns FAILED — availability check finds the existing booking conflict, no duplicate record created.

### 6c — Cancellation updates record (not delete)
```
agentcore invoke '{\"prompt\": \"I am E001. Cancel my booking for Training Center R004 that starts at 2026-07-25T10:00:00.\"}'
```
**Expected:** Record in DynamoDB updated from CONFIRMED → CANCELLED (not deleted). Verify in console.

---

# EDGE CASES AND EXTRA TESTS

---

## Insufficient Access — Multiple Scenarios

### E004 (BASIC) trying STANDARD room
```
agentcore invoke '{\"prompt\": \"I am E004. Book Board Room R002 on 2026-07-22 from 10am to 11am for Quick Meeting with 3 people.\"}'
```
**Expected:** BASIC insufficient for STANDARD room. Access denied at step 1.

### E003 (STANDARD) trying PREMIUM room
```
agentcore invoke '{\"prompt\": \"I am E003. Book Executive Suite R003 on 2026-07-22 from 10am to 11am for Client Call with 5 people.\"}'
```
**Expected:** STANDARD insufficient for PREMIUM room. Access denied.

### E002 (PREMIUM) trying EXECUTIVE room
```
agentcore invoke '{\"prompt\": \"I am E002. Book C-Suite Presidential Suite R006 on 2026-07-22 from 10am to 11am for Board Call with 3 people.\"}'
```
**Expected:** PREMIUM insufficient for EXECUTIVE room. Access denied.

---

## Room Unavailable Scenarios

### Exact time conflict with seeded booking
```
# B003 is R004, 2026-01-15 10:00-11:00
agentcore invoke '{\"prompt\": \"I am E001. Book Training Center R004 on 2026-01-15 from 10am to 11am for Team Meeting with 10 people.\"}'
```
**Expected:** Conflict with existing booking B003 shown.

### Partial overlap conflict
```
# B001 is R001, 2026-01-15 11:00-12:00
# New request 10:30-11:30 overlaps by 30 min
agentcore invoke '{\"prompt\": \"I am E001. Book Innovation Hub R001 on 2026-01-15 from 10:30am to 11:30am for Quick Sync with 5 people.\"}'
```
**Expected:** Conflict detected due to overlap.

---

## Structured JSON Tests (All Actions)

### Sequential
```
agentcore invoke '{\"action\": \"sequential\", \"employee_id\": \"E002\", \"room_id\": \"R002\", \"start_time\": \"2026-07-20T14:00:00\", \"end_time\": \"2026-07-20T16:00:00\", \"attendee_count\": 8, \"meeting_title\": \"Product Review\"}'
```

### Parallel
```
agentcore invoke '{\"action\": \"parallel\", \"employee_id\": \"E001\", \"room_id\": \"R004\", \"start_time\": \"2026-07-20T09:00:00\", \"end_time\": \"2026-07-20T10:00:00\", \"attendee_count\": 6, \"meeting_title\": \"Parallel Test\"}'
```

### Confirm (YES)
```
agentcore invoke '{\"action\": \"confirm\", \"employee_id\": \"E001\", \"room_id\": \"R004\", \"start_time\": \"2026-07-20T09:00:00\", \"end_time\": \"2026-07-20T10:00:00\", \"attendee_count\": 6, \"meeting_title\": \"Parallel Test\", \"confirmed\": true}'
```

### Confirm (NO — human rejection)
```
agentcore invoke '{\"action\": \"confirm\", \"employee_id\": \"E001\", \"room_id\": \"R004\", \"start_time\": \"2026-07-20T09:00:00\", \"end_time\": \"2026-07-20T10:00:00\", \"attendee_count\": 6, \"meeting_title\": \"Parallel Test\", \"confirmed\": false}'
```

### Cancel
```
agentcore invoke '{\"action\": \"cancel\", \"employee_id\": \"E001\", \"room_id\": \"R004\", \"start_time\": \"2026-07-20T09:00:00\"}'
```

---

## python invoke_agent.py — All Scenarios

```
# Happy path sequential
python invoke_agent.py "I am E001. Book Innovation Hub R001 on 2026-07-20 from 10am to 12pm for Team Sync with 5 people." --session seq-py-1
python invoke_agent.py "Yes confirm." --session seq-py-1

# Parallel
python invoke_agent.py "I am E003. Book Training Center R004 on 2026-07-21 from 2pm to 3:30pm for Quarterly Planning with 12 people. Check access and availability in parallel." --session par-py-1
python invoke_agent.py "Yes go ahead." --session par-py-1

# Human rejection
python invoke_agent.py "I am E002. Book Board Room R002 on 2026-07-22 from 2pm to 4pm for Product Review with 8 people." --session hitl-py-1
python invoke_agent.py "No cancel it." --session hitl-py-1

# Access denied
python invoke_agent.py "I am E004. Book Executive Suite R003 on 2026-07-22 from 2pm to 4pm for meeting with 3 people."

# Duration exceeded
python invoke_agent.py "I am E004. Book Innovation Hub R001 on 2026-07-22 from 10am to 2pm for Extended Workshop with 5 people."

# Capacity exceeded
python invoke_agent.py "I am E003. Book Client Meeting Room R005 on 2026-07-22 from 10am to 11am for big team meeting with 15 people."

# Room unavailable (uses seeded conflict)
python invoke_agent.py "I am E001. Book Innovation Hub R001 on 2026-01-15 from 11am to 12pm for Quick Sync with 5 people."

# Back-to-back buffer
python invoke_agent.py "I am E001. Book Innovation Hub R001 on 2026-01-15 from 12:05pm to 1:05pm for Follow-up with 5 people."

# Cancellation
python invoke_agent.py "I am E001. Cancel my booking for room R004 starting at 2026-07-25T10:00:00."
```

---

## DynamoDB Console Verification Steps

After each confirmed booking, verify at:
**AWS Console → DynamoDB → Tables → Bookings → Explore items**

What to check:
| Field | Expected Value |
|---|---|
| RoomID | e.g. R001 |
| StartTime | e.g. 2026-07-20T10:00:00 |
| BookingStatus | CONFIRMED |
| EmployeeID | e.g. E001 |
| BookingID | auto-generated UUID |
| AttendeeCount | e.g. 5 |
| MeetingTitle | e.g. Team Sync |

After cancellation:
| Field | Expected Value |
|---|---|
| BookingStatus | CANCELLED (not deleted) |
| UpdatedAt | updated timestamp |

---

## Quick Demo Order (Recommended for Presentation)

1. **Pattern 4 (DB Retrieval)** — access denied, shows DynamoDB reads → single command, fast
2. **Pattern 5a (Computation)** — duration exceeded → single command, fast  
3. **Pattern 5b (Buffer)** — back-to-back conflict → single command, fast
4. **Pattern 1 (Sequential)** — happy path, 2 turns, confirm YES → show DynamoDB after
5. **Pattern 2 (Parallel)** — structured JSON to show `parallel_execution_note` clearly
6. **Pattern 3 (Human-in-Loop)** — 2 turns, say NO → show no DynamoDB record
7. **Pattern 6 (Persistence)** — confirm booking → open DynamoDB console live to show record