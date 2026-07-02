# Architecture & Deployment — Conference Room Booking Agent

## Overview

A multi-agent conference room booking system built with the AWS Strands Agents SDK, deployed
to Amazon Bedrock AgentCore Runtime as an ARM64 container, with Amazon DynamoDB as the
persistence layer.

## System Components

```
┌─────────────────────┐
│  agentcore invoke    │  (CLI / any HTTPS client with IAM auth)
└──────────┬───────────┘
           │ JSON payload
           ▼
┌─────────────────────────────────────────────┐
│  Bedrock AgentCore Runtime (ARM64 container) │
│  ┌─────────────────────────────────────────┐ │
│  │  main.py                                 │ │
│  │  @app.entrypoint  async def invoke()     │ │
│  │  routes on payload["action"]:            │ │
│  │    sequential | parallel | confirm       │ │
│  └───────────────┬───────────────────────────┘ │
│                  ▼                              │
│  ┌─────────────────────────────────────────┐  │
│  │  booking_agent.py                        │  │
│  │  ToolExecutor        — individual tools  │  │
│  │  BookingOrchestrator — workflow control  │  │
│  └───────────────┬───────────────────────────┘  │
└──────────────────┼──────────────────────────────┘
                    ▼
┌─────────────────────────────────────────────┐
│  Amazon DynamoDB (ap-south-1)                │
│  Employees | ConferenceRooms | Bookings      │
│  RoomFeatures | AccessLevels                 │
└─────────────────────────────────────────────┘
```

## Data Model

### `AccessLevel` (enum, `booking_agent.py`)
```
BASIC = 0, STANDARD = 1, PREMIUM = 2, EXECUTIVE = 3
```
Ordered hierarchy — a room requiring `STANDARD` accepts `STANDARD`, `PREMIUM`, or `EXECUTIVE`
employees.

### `BookingStatus` (enum)
```
PENDING_CONFIRMATION | CONFIRMED | CANCELLED | FAILED
```

### `BookingRequest` (dataclass)
```python
employee_id: str
room_id: str
start_time: str   # ISO 8601
end_time: str     # ISO 8601
attendee_count: int
meeting_title: str
```

### DynamoDB tables

| Table | Partition Key | Sort Key | Notes |
|---|---|---|---|
| `Employees` | `EmployeeID` | — | Name, Department, Email, AccessLevel |
| `ConferenceRooms` | `RoomID` | — | Capacity, Location, RequiredAccessLevel |
| `RoomFeatures` | `RoomID` | `Feature` (or similar) | Projector, Video Conferencing, etc. |
| `Bookings` | `RoomID` | `StartTime` | See note below on key design |
| `AccessLevels` | `AccessLevel` | — | Max booking hours per level |

**Key design note:** `Bookings` uses `(RoomID, StartTime)` as its composite key. This means a
second confirmed booking for the *same room and exact same start time* overwrites the prior
record rather than creating a duplicate — which is what makes the "no duplicate booking on
re-run" requirement hold for bookings created through the agent (which always use real,
caller-supplied timestamps). It does **not** protect against `initialize_dynamodb.py`'s sample
data, which computes its three seed bookings' start times relative to `datetime.utcnow()` at run
time — re-running the seed script produces new keys each time rather than reusing the same three
sample slots. Fixing this would mean hardcoding fixed ISO timestamps in the seed script rather
than deriving them from the current time.

## Execution Patterns

### Sequential (`action: "sequential"`, or omitted — this is the default)

`BookingOrchestrator.execute_sequential()`, each step gated on the previous succeeding:

1. `verify_employee_access(employee_id, room_id)` — employee lookup + access-level comparison
   against the room's required level
2. `check_room_availability(room_id, start_time, end_time)` — scans existing bookings for the
   room, applying a 15-minute buffer on either side of the requested slot
3. `calculate_meeting_duration(start_time, end_time, access_level)` — computes duration in
   hours/minutes, compares against the employee's access-level max
4. `validate_attendee_count(room_id, attendee_count)` — compares against room capacity
5. `get_room_details(room_id)` — fetches full room info (name, capacity, features, location) for
   the confirmation summary
6. Returns `status: PENDING_CONFIRMATION` with the full booking summary; no DynamoDB write yet

### Parallel (`action: "parallel"`)

`_run_parallel_checks()` in `main.py` submits `verify_employee_access` and
`check_room_availability` to a `concurrent.futures.ThreadPoolExecutor` (2 workers), since both
are independent, I/O-bound DynamoDB calls with no dependency on each other. Once both complete,
results are merged; duration and capacity validation then run sequentially against the merged
result, same as the sequential path. The response includes a `parallel_execution_note` field and
the full intermediate results (`access_result`, `availability_result`, `duration_result`,
`attendee_result`) so the concurrent execution is directly inspectable in the output.

### Confirm (`action: "confirm"`)

Requires the full booking fields plus a boolean `confirmed` field. Routes to
`BookingOrchestrator.confirm_booking(booking, confirmed)`:
- `confirmed: true` → writes a `CONFIRMED` record to `Bookings` (via `PutItem` on the
  `RoomID`/`StartTime` key) and returns the generated `booking_id`
- `confirmed: false` → returns `status: CANCELLED`, `database_record_created: false`, no write

Note: the `confirm` action re-derives the booking from the payload fields but does not currently
re-run the availability check before writing — it trusts that the caller confirmed shortly after
receiving a `PENDING_CONFIRMATION` response from `sequential`/`parallel`. A production hardening
would re-verify availability immediately before the write to guard against a race between two
users confirming the same slot concurrently.

## Deployment

### Why AgentCore Runtime requires a container build, not a local zip

Bedrock AgentCore Runtime requires **linux/arm64** containers. Any dependency with native
compiled code (e.g. `pydantic-core`, `awscrt`, `cffi`) must be built for that exact platform.
Manually `pip install`-ing on a Windows/x86_64 machine and zipping the result produces Windows
`.pyd` binaries that fail to import at runtime (`ModuleNotFoundError:
No module named 'pydantic_core._pydantic_core'`) — this is what the project hit early in
development, and is why deployment goes through `agentcore launch`, which builds via AWS
CodeBuild targeting the correct architecture, rather than any manual packaging step.

### Deployment flow

```
agentcore configure --entrypoint main.py --name conference_booking_agent
  → generates .bedrock_agentcore.yaml + Dockerfile

agentcore launch
  → zips source, uploads to S3
  → CodeBuild project builds an ARM64 image from the Dockerfile (pip install runs
    inside the Linux ARM64 build environment — no cross-compilation flags needed)
  → pushes image to ECR
  → creates/updates the AgentCore Runtime + endpoint
```

Subsequent deployments after a code change use:
```
agentcore launch --auto-update-on-conflict
```

### IAM

`agentcore configure` auto-creates an execution role
(`AmazonBedrockAgentCoreSDKRuntime-<region>-<hash>`) with baseline Bedrock/CloudWatch/X-Ray
permissions. DynamoDB access is **not** included by default and must be attached separately —
see `dynamodb-policy.json` and the README's deployment section.

### Server startup

`main.py`'s `if __name__ == "__main__":` block calls `app.run()`, which starts the HTTP server
AgentCore Runtime's health check and `/invocations` endpoint require (bound to `0.0.0.0:8080`
inside the container). A `RUN_LOCAL_TEST=1` environment variable switches to a one-off local
smoke test instead, for quick offline sanity checks without needing a running server.

## Testing

- `test_scenarios.py` — local test runner exercising all execution patterns and edge cases
  directly against `BookingOrchestrator`, without going through the deployed runtime
- `prompts.md` — the six required scenarios (happy path, insufficient access, room unavailable,
  duration exceeded, human rejection, back-to-back buffer conflict) with real payloads and
  responses captured from the deployed agent via `agentcore invoke`