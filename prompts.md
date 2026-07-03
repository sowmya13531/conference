# Sample Prompts — Conference Room Booking Agent

These are **natural-language** prompts sent to the deployed AgentCore Runtime via the
`prompt` payload field, routed through a `strands.Agent` (Bedrock Claude model) that
decides which tools to call and in what order. Scenarios that involve confirmation are
multi-turn — reuse the same `session_id` across turns of one conversation.

Invoke shape:
```
agentcore invoke '{"prompt": "<message>"}' --session-id "<id>-0000000000000000000000"
```
A new `session_id` starts a fresh conversation with no memory of prior turns.

Seed data reference:

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

**Windows PowerShell note:** escape inner double quotes with backslashes and use double
quotes for the outer string, e.g. `agentcore invoke "{\"prompt\": \"...\"}" --session-id "..."`
— PowerShell's single-quote strings get re-parsed by the CLI's `.cmd` shim on Windows and
will silently split your JSON on spaces if you use single quotes around it there.

**Session ids must be 33+ characters** (an AWS requirement on `runtimeSessionId`) — the
examples below pad short names with trailing zeros for you.

---

## 1. Happy Path (Sequential Execution)

Employee lookup, access verification, availability check, duration calculation,
confirmation summary, booking creation — each step blocked on the previous.

**Turn 1:**
```
agentcore invoke '{"prompt": "Hi, I am employee E001. I want to book the Innovation Hub (R001) tomorrow from 10am to 12pm for a Team Sync with 5 attendees."}' --session-id "happy-path-1-0000000000000000000000"
```
Expect: the agent verifies access, checks availability, calculates duration, checks
capacity, then presents a summary (room name, capacity, features, times, duration,
attendee count) and asks for YES/NO.

**Turn 2 — confirm:**
```
agentcore invoke '{"prompt": "Yes, please confirm it."}' --session-id "happy-path-1-0000000000000000000000"
```
Expect: booking written to DynamoDB with status CONFIRMED, agent replies with a
booking ID.

---

## 2. Parallel Execution

Access check and availability check run concurrently (the agent issues both tool calls
in a single turn), merged before duration/capacity validation.

```
agentcore invoke '{"prompt": "Book room R004 for employee E003 on 2026-07-10 from 2pm to 3:30pm, 12 attendees, title Quarterly Planning. Please check my access and the room availability at the same time."}' --session-id "parallel-1-0000000000000000000000"
```
Expect: the response/logs show access and availability were checked together in one
model turn (two tool calls issued at once) rather than as two separate round trips,
before duration and capacity validation run.

---

## 3. Insufficient Access Permissions

```
agentcore invoke '{"prompt": "I am employee E004, I would like to book the Executive Suite (R003) on 2026-07-15 from 2pm to 4pm for 3 people, Team Discussion."}' --session-id "access-denied-1-0000000000000000000000"
```
Expect: E004 is BASIC, R003 requires PREMIUM. Agent reports access denied and does not
proceed to availability/duration checks.

---

## 4. Room Unavailable

```
agentcore invoke '{"prompt": "Book R001 for employee E001 from 2026-07-10T02:30:00 to 2026-07-10T03:30:00, 5 attendees, Emergency Meeting."}' --session-id "unavailable-1-0000000000000000000000"
```
(Use a slot overlapping an existing seeded booking.) Expect: agent reports the room
unavailable and lists the conflicting booking(s).

---

## 5. Booking Duration Exceeds Limit

```
agentcore invoke '{"prompt": "I am E004, book R001 from 2026-07-15T10:00:00 to 2026-07-15T14:00:00 for 5 people, Extended Workshop."}' --session-id "duration-limit-1-0000000000000000000000"
```
Expect: E004 is BASIC (2h max), requested duration is 4h. Agent reports the duration
exceeds the access-level limit and stops before presenting a confirmation summary.

---

## 6. Human Rejection (user says NO)

**Turn 1:**
```
agentcore invoke '{"prompt": "Book R004 for E002 on 2026-07-15 from 2pm to 4pm, 8 attendees, Product Review."}' --session-id "rejection-1-0000000000000000000000"
```
**Turn 2 — reject:**
```
agentcore invoke '{"prompt": "No, cancel that."}' --session-id "rejection-1-0000000000000000000000"
```
Expect: no record written to DynamoDB; agent confirms the booking was not made.

---

## 7. Back-to-Back Booking (15-minute buffer)

```
agentcore invoke '{"prompt": "Book R001 for E001 from 2026-07-10T03:00:00 to 2026-07-10T04:00:00, 5 attendees, Quick Sync."}' --session-id "back-to-back-1-0000000000000000000000"
```
(Use a slot starting ~30 minutes after an existing seeded booking ends.) Expect: agent
reports the room unavailable due to the 15-minute buffer and shows the conflicting
booking, even though the two time ranges don't literally overlap.

---

## 8. Cancellation

```
agentcore invoke '{"prompt": "I am E001, please cancel my booking for room R001 that starts at 2026-07-10T10:00:00."}' --session-id "cancel-1-0000000000000000000000"
```
Expect: agent verifies E001 is the original booker and marks the booking CANCELLED.

---

## Legacy structured payloads (deterministic tool testing, no LLM)

For automated regression tests of the underlying tool logic independent of the model,
the old structured `action` payloads still work and bypass the LLM entirely:
```
agentcore invoke '{"action": "sequential", "employee_id": "E001", "room_id": "R001", "start_time": "2026-07-10T10:00:00", "end_time": "2026-07-10T12:00:00", "attendee_count": 5, "meeting_title": "Team Sync"}'
```
This is useful for CI/unit-style checks but does **not** by itself satisfy the
assessment's "Agent Framework: Strands / LLM: Bedrock Claude" requirement — use the
`prompt` payloads above for the actual demonstration.