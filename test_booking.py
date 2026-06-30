import json
import asyncio
from booking_agent import BookingOrchestrator, BookingRequest

async def test():
    request = BookingRequest(
        employee_id="E001",
        room_id="R001",
        start_time="2026-01-15T10:00:00",
        end_time="2026-01-15T12:00:00",
        attendee_count=5,
        meeting_title="Team Sync"
    )

    orchestrator = BookingOrchestrator()
    result = await orchestrator.execute_sequential(request)

    print(json.dumps(result, indent=2, default=str))

asyncio.run(test())