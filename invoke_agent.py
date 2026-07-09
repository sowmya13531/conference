"""
Invoke the deployed AgentCore Runtime directly via boto3, bypassing the
`agentcore` CLI entirely. Useful on Windows/PowerShell where the CLI's
.cmd shim mangles quoting on JSON payloads with embedded double quotes.

Usage:
    python invoke_agent.py "I want to book room R001 tomorrow 10-12 for 5 people, employee E001" --session happy-path-1
    python invoke_agent.py "Yes, please confirm it." --session happy-path-1

Set AGENT_ARN below (or via env var) to your deployed agent's ARN — the
same one printed at the end of `agentcore deploy`.

NOTE: runtimeSessionId must be at least 33 characters (AWS requirement).
Short ids you pass with --session are padded automatically so you can
still use memorable names like "happy-path-1" across turns.
"""

import argparse
import json
import os
import uuid

import boto3

AGENT_ARN = os.environ.get(
    "AGENT_ARN",
    "arn:aws:bedrock-agentcore:ap-south-1:211374268044:runtime/conference_booking_agent_v2-9qR8P3GJsG",
)
REGION = os.environ.get("AGENT_REGION", "ap-south-1")
MIN_SESSION_LEN = 33


def _normalize_session_id(raw: str) -> str:
    """Pad short, human-friendly session names out to the 33-char minimum
    the API requires, so the same padded id is reproducible across calls
    as long as you pass the same --session value each time."""
    if len(raw) >= MIN_SESSION_LEN:
        return raw
    return (raw + "-" + "0" * MIN_SESSION_LEN)[:MIN_SESSION_LEN]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("prompt", help="Natural language message to send the agent")
    parser.add_argument("--session", default=None, help="Session id to reuse across turns")
    args = parser.parse_args()

    session_id = _normalize_session_id(args.session) if args.session else str(uuid.uuid4())
    payload = {"prompt": args.prompt, "session_id": session_id}

    client = boto3.client("bedrock-agentcore", region_name=REGION)
    response = client.invoke_agent_runtime(
        agentRuntimeArn=AGENT_ARN,
        runtimeSessionId=session_id,
        payload=json.dumps(payload).encode("utf-8"),
        qualifier="DEFAULT",
    )

    # response["response"] can come back as a StreamingBody (supports
    # .read()) or as an iterable of byte chunks depending on content
    # type — handle both so this script works either way.
    raw = response["response"]
    if hasattr(raw, "read"):
        body = raw.read().decode("utf-8")
    else:
        body = b"".join(chunk for chunk in raw).decode("utf-8")

    print(f"\nsession_id: {session_id}")
    try:
        # Line 70 — fixed
        print(json.dumps(json.loads(body), indent=2, ensure_ascii=False))
    except json.JSONDecodeError:
        print(body)


if __name__ == "__main__":
    main()