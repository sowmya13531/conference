"""
Amazon Bedrock AgentCore Runtime
Conference Room Booking Multi-Agent System
"""

import logging
from typing import Dict, Any

from bedrock_agentcore import BedrockAgentCoreApp

from booking_agent import (
    BookingOrchestrator,
    BookingRequest,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = BedrockAgentCoreApp()


@app.entrypoint
async def invoke(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    AgentCore Runtime Entry Point
    """

    logger.info("Received AgentCore request")

    try:

        action = payload.get("action", "sequential").lower()

        booking = BookingRequest(
            employee_id=payload["employee_id"],
            room_id=payload["room_id"],
            start_time=payload["start_time"],
            end_time=payload["end_time"],
            attendee_count=int(payload["attendee_count"]),
            meeting_title=payload["meeting_title"],
        )

        orchestrator = BookingOrchestrator()

        if action == "sequential":

            result = await orchestrator.execute_sequential(
                booking
            )

        elif action == "parallel":

            result = await orchestrator.execute_parallel(
                booking
            )

        elif action == "confirm":

            confirmed = payload.get("confirmed", False)

            result = orchestrator.confirm_booking(
                booking,
                confirmed
            )

        else:

            result = {
                "status": "FAILED",
                "error": f"Unknown action: {action}"
            }

        return result

    except Exception as e:

        logger.exception("Runtime Error")

        return {
            "status": "FAILED",
            "error": str(e)
        }


if __name__ == "__main__":

    import asyncio

    sample = {
        "action": "sequential",
        "employee_id": "E001",
        "room_id": "R001",
        "start_time": "2026-01-15T10:00:00",
        "end_time": "2026-01-15T12:00:00",
        "attendee_count": 5,
        "meeting_title": "Team Sync"
    }

    print(
        asyncio.run(
            invoke(sample)
        )
    )