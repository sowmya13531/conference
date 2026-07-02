# Conference Room Booking Agent

Multi-agent conference room booking system built on the AWS Strands Agents SDK,
deployed to Amazon Bedrock AgentCore Runtime, backed by Amazon DynamoDB.

Built for the Tachyon AIML Internship Training Program — AWS Track (Strands + Bedrock).

## Architecture

- **Runtime**: Amazon Bedrock AgentCore Runtime (ARM64 container, deployed via AWS CodeBuild)
- **Entry point**: `main.py` — implements the `bedrock_agentcore.BedrockAgentCoreApp` `@app.entrypoint`
- **Orchestration logic**: `booking_agent.py` — `ToolExecutor` (individual DynamoDB-backed tools) and
  `BookingOrchestrator` (sequential/parallel workflow + confirmation)
- **Database**: Amazon DynamoDB — 5 tables (`Employees`, `ConferenceRooms`, `Bookings`,
  `RoomFeatures`, `AccessLevels`), seeded by `initialize_dynamodb.py`
- **Package manager**: `uv`

See `ARCHITECTURE_AND_DEPLOYMENT.md` for full design details.

## Prerequisites

- Python 3.12+
- An AWS account with Bedrock AgentCore access, in region `ap-south-1` (or update the region
  throughout if deploying elsewhere)
- AWS CLI configured with credentials that can create IAM roles, ECR repos, CodeBuild projects,
  and DynamoDB tables
- [`uv`](https://docs.astral.sh/uv/) installed (`pip install uv` if you don't have it)

## 1. Environment setup (uv)

```powershell
uv python install 3.12
uv venv --python 3.12
.venv\Scripts\activate   # macOS/Linux: source .venv/bin/activate
uv sync
```

## 2. AWS credentials

Configure credentials for an IAM principal with permissions to create/manage IAM roles, ECR,
CodeBuild, Bedrock AgentCore, and DynamoDB:

```powershell
aws configure
```

Verify:
```powershell
aws sts get-caller-identity
```

## 3. Initialize DynamoDB

Creates all 5 tables and seeds sample data (employees, rooms, room features, access levels,
and a few sample bookings):

```powershell
python initialize_dynamodb.py
```

Re-running this script is safe for tables/employees/rooms/features (idempotent, `already exists`
messages are expected on reruns). Sample data seeded:

| Employee | Access Level | Booking limit |
|---|---|---|
| E001 (Alice Johnson) | EXECUTIVE | 24h |
| E002 (Bob Smith) | PREMIUM | 8h |
| E003 (Carol Davis) | STANDARD | 4h |
| E004 (David Wilson) | BASIC | 2h |
| E005 (Emma Martinez) | STANDARD | 4h |

| Room | Capacity | Required access |
|---|---|---|
| R001 Innovation Hub | 20 | BASIC |
| R002 Board Room | 15 | STANDARD |
| R003 Executive Suite | 10 | PREMIUM |
| R004 Training Center | 30 | BASIC |
| R005 Client Meeting Room | 8 | STANDARD |
| R006 C-Suite Presidential Suite | 5 | EXECUTIVE |

## 4. Deploy to Bedrock AgentCore Runtime

Install the deployment toolkit (already included via `uv sync`, but confirm it's on PATH):

```powershell
uv pip install bedrock-agentcore-starter-toolkit
```

Configure the agent (one-time; generates `.bedrock_agentcore.yaml` and a Dockerfile):

```powershell
agentcore configure --entrypoint main.py --name conference_booking_agent
```

When prompted:
- Dependency file: accept the detected `requirements.txt`
- Deployment type: **Container** (Direct Code Deploy is unavailable on Windows without a zip
  utility — Container/CodeBuild is the correct, recommended path regardless)
- Execution role / ECR repository: accept auto-create on first run
- Authorization: IAM (default)
- Memory: skip (not required for this project)

Deploy — this builds a proper **ARM64** container via AWS CodeBuild (no local Docker required;
Bedrock AgentCore Runtime requires ARM64, and local Windows/x86 builds cannot target it directly):

```powershell
agentcore launch
```

On subsequent deployments (after code changes), use:

```powershell
agentcore launch --auto-update-on-conflict
```

### Grant the execution role DynamoDB access

The auto-created execution role has Bedrock/CloudWatch/X-Ray permissions but not DynamoDB by
default. Attach the included policy (replace the role name with the one printed by
`agentcore configure`/`agentcore launch`, e.g. `AmazonBedrockAgentCoreSDKRuntime-ap-south-1-xxxx`):

```powershell
aws iam put-role-policy `
  --role-name <YOUR_EXECUTION_ROLE_NAME> `
  --policy-name ConferenceBookingDynamoDBAccess `
  --policy-document file://dynamodb-policy.json
```

Wait ~10–15 seconds for IAM propagation before invoking.

## 5. Invoke the agent

**Windows PowerShell note**: escape inner double quotes with backslashes when passing JSON to
`agentcore invoke`, otherwise PowerShell's native argument parsing splits on the embedded quotes:

```powershell
agentcore invoke '{\"employee_id\": \"E001\", \"room_id\": \"R001\", \"start_time\": \"2026-07-10T15:00:00\", \"end_time\": \"2026-07-10T16:00:00\", \"attendee_count\": 5, \"meeting_title\": \"Team Sync\"}'
```

This runs the **sequential** workflow by default. For **parallel** execution, add
`"action": "parallel"`. To **confirm** a pending booking, resend the same fields plus
`"action": "confirm"` and `"confirmed": true` (or `false` to cancel). See `prompts.md` for the
full set of example payloads and expected responses covering all six required scenarios.

Check status and logs:
```powershell
agentcore status
aws logs tail /aws/bedrock-agentcore/runtimes/<runtime-id>-DEFAULT --follow
```

## Known limitations / notes

- `lambda_handler.py` is included per the deliverable checklist but is not wired into the live
  AgentCore Runtime invocation path — `main.py`'s `@app.entrypoint` is the actual entry point
  used by `agentcore launch`.
- `initialize_dynamodb.py` uses a fixed `base_date = datetime(2026, 1, 15, 9, 0, 0)` for the
  three sample bookings, so re-running the script always produces the same `(RoomID, StartTime)`
  composite keys and overwrites in place — no duplicate rows accumulate.