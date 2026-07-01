"""
Conference Room Booking Agent
Amazon Bedrock AgentCore Runtime Entry Point

This file is the entry point for Bedrock AgentCore Runtime.
It uses the Strands Agents SDK with the bedrock_agentcore app wrapper.
"""

import logging
import asyncio
import concurrent.futures
from decimal import Decimal
from typing import Dict, Any

from bedrock_agentcore import BedrockAgentCoreApp
from booking_agent import BookingOrchestrator, BookingRequest, ToolExecutor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

app = BedrockAgentCoreApp()


def _make_json_safe(obj: Any) -> Any:
    """
    Recursively convert DynamoDB Decimal values (and other non-JSON-native
    types) into plain int/float so the AgentCore Runtime can cleanly
    JSON-serialize the response (it falls back to Python repr ??? single
    quotes ??? when it encounters un-serializable types like Decimal).
    """
    if isinstance(obj, Decimal):
        return int(obj) if obj == obj.to_integral_value() else float(obj)
    if isinstance(obj, dict):
        return {k: _make_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_make_json_safe(v) for v in obj]
    return obj


def _run_parallel_checks(booking: BookingRequest):
    """
    Truly parallel execution: access check and availability check run concurrently
    using a ThreadPoolExecutor since DynamoDB calls are I/O bound.
    """
    executor = ToolExecutor()

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        access_future = pool.submit(
            executor.verify_employee_access,
            booking.employee_id,
            booking.room_id,
        )
        availability_future = pool.submit(
            executor.check_room_availability,
            booking.room_id,
            booking.start_time,
            booking.end_time,
        )
        access_result = access_future.result(timeout=15)
        availability_result = availability_future.result(timeout=15)

    return access_result, availability_result


@app.entrypoint
async def invoke(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    AgentCore Runtime Entry Point

    Accepted payload keys:
      action         : "sequential" | "parallel" | "confirm"
      employee_id    : str  e.g. "E001"
      room_id        : str  e.g. "R001"
      start_time     : ISO-8601 str  e.g. "2026-07-01T10:00:00"
      end_time       : ISO-8601 str  e.g. "2026-07-01T12:00:00"
      attendee_count : int  e.g. 5
      meeting_title  : str  e.g. "Team Sync"
      confirmed      : bool (only required for action="confirm")
    """

    logger.info("AgentCore invocation received ??? action=%s", payload.get("action"))

    try:
        action = payload.get("action", "sequential").lower()

        # ?????? Validate required fields ???????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????
        required = ["employee_id", "room_id", "start_time", "end_time",
                    "attendee_count", "meeting_title"]
        missing = [f for f in required if f not in payload]
        if missing:
            return {
                "status": "FAILED",
                "error": f"Missing required fields: {', '.join(missing)}",
            }

        if action not in ("sequential", "parallel", "confirm"):
            return {
                "status": "FAILED",
                "error": f"Unknown action '{action}'. Use: sequential | parallel | confirm",
            }

        # ?????? Build BookingRequest ???????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????
        booking = BookingRequest(
            employee_id=str(payload["employee_id"]),
            room_id=str(payload["room_id"]),
            start_time=str(payload["start_time"]),
            end_time=str(payload["end_time"]),
            attendee_count=int(payload["attendee_count"]),
            meeting_title=str(payload["meeting_title"]),
        )

        orchestrator = BookingOrchestrator()

        # ?????? Route action ???????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????
        if action == "sequential":
            logger.info(
                "SEQUENTIAL workflow ??? employee=%s room=%s",
                booking.employee_id, booking.room_id,
            )
            result = await orchestrator.execute_sequential(booking)

        elif action == "parallel":
            logger.info(
                "PARALLEL workflow ??? employee=%s room=%s",
                booking.employee_id, booking.room_id,
            )
            # Run both I/O-bound checks in a thread pool, then merge
            loop = asyncio.get_event_loop()
            access_result, availability_result = await loop.run_in_executor(
                None, _run_parallel_checks, booking
            )

            # Merge results back into the orchestrator's parallel flow
            executor = ToolExecutor()

            # NOTE: verify_employee_access() and check_room_availability() do
            # NOT return a "success" key ??? only "access_granted"/"available"
            # plus "error". The original code gated on result.get("success"),
            # which is always None/falsy, so this branch failed on every
            # request regardless of the actual access/availability outcome.
            # Fixed to check the real keys these functions return.
            if not access_result.get("access_granted"):
                result = {
                    "workflow": "parallel",
                    "status": "FAILED",
                    "step": "access_verification",
                    "error": access_result.get("error", "Access denied"),
                }
            elif not availability_result.get("available"):
                result = {
                    "workflow": "parallel",
                    "status": "FAILED",
                    "step": "availability_check",
                    "error": availability_result.get("error", "Room not available"),
                    "conflicts": availability_result.get("conflicts", []),
                }
            else:
                duration_result = executor.calculate_meeting_duration(
                    booking.start_time, booking.end_time,
                    access_result["access_level"],
                )
                if not duration_result.get("within_limit"):
                    result = {
                        "workflow": "parallel",
                        "status": "FAILED",
                        "step": "duration_validation",
                        "error": duration_result.get("error", "Duration limit exceeded"),
                    }
                else:
                    attendee_result = executor.validate_attendee_count(
                        booking.room_id, booking.attendee_count
                    )
                    if not attendee_result.get("capacity_sufficient"):
                        result = {
                            "workflow": "parallel",
                            "status": "FAILED",
                            "step": "capacity_validation",
                            "error": attendee_result.get("error", "Insufficient capacity"),
                        }
                    else:
                        room_details = executor.get_room_details(booking.room_id)
                        result = {
                            "workflow": "parallel",
                            "status": "PENDING_CONFIRMATION",
                            "parallel_execution_note": (
                                "Access check and availability check ran concurrently "
                                "via ThreadPoolExecutor; results merged before duration "
                                "and capacity validation."
                            ),
                            "booking_request": booking.__dict__,
                            "confirmation_summary": {
                                "room_name": room_details.get("room_name"),
                                "capacity": room_details.get("capacity"),
                                "features": room_details.get("features"),
                                "start_time": booking.start_time,
                                "end_time": booking.end_time,
                                "duration_hours": duration_result["duration_hours"],
                                "duration_minutes": duration_result["duration_minutes"],
                                "attendee_count": booking.attendee_count,
                                "meeting_title": booking.meeting_title,
                            },
                            "access_result": access_result,
                            "availability_result": availability_result,
                            "duration_result": duration_result,
                            "attendee_result": attendee_result,
                        }

        elif action == "confirm":
            confirmed = payload.get("confirmed")
            if not isinstance(confirmed, bool):
                return {
                    "status": "FAILED",
                    "error": "'confirmed' must be a boolean (true/false)",
                }
            logger.info(
                "CONFIRM workflow ??? employee=%s confirmed=%s",
                booking.employee_id, confirmed,
            )
            result = orchestrator.confirm_booking(booking, confirmed)

        result = _make_json_safe(result)
        logger.info("Invocation complete ??? status=%s", result.get("status"))
        return result

    except KeyError as exc:
        logger.error("Missing field: %s", exc)
        return {"status": "FAILED", "error": f"Missing required field: {exc}"}
    except ValueError as exc:
        logger.error("Value error: %s", exc)
        return {"status": "FAILED", "error": str(exc)}
    except Exception as exc:
        logger.exception("Unexpected runtime error")
        return {"status": "FAILED", "error": str(exc)}


if __name__ == "__main__":
    import os

    # CRITICAL: when AgentCore Runtime starts the container, it runs
    # `python main.py` and expects this process to start an HTTP server
    # bound to 0.0.0.0:8080 (via app.run()) so its health check and
    # /invocations endpoint become reachable. Previously this block only
    # ran a one-off local test and exited immediately ??? no server ever
    # started, so AgentCore's health check waited the full 30s for a port
    # that would never open, and the deployment timed out.
    #
    # Set RUN_LOCAL_TEST=1 to instead run a single offline smoke test
    # (useful for quick local sanity checks); otherwise this starts the
    # real server, exactly as AgentCore Runtime requires.
    if os.environ.get("RUN_LOCAL_TEST") == "1":
        sample_sequential = {
            "action": "sequential",
            "employee_id": "E001",
            "room_id": "R001",
            "start_time": "2026-07-10T10:00:00",
            "end_time": "2026-07-10T12:00:00",
            "attendee_count": 5,
            "meeting_title": "Team Sync",
        }
        print("=== LOCAL TEST ??? Sequential workflow ===")
        result = asyncio.run(invoke(sample_sequential))
        import json
        print(json.dumps(result, indent=2, default=str))
    else:
        logger.info("Starting Bedrock AgentCore Runtime server on port 8080...")
        app.run()
