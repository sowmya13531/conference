"""
Lambda Handler for Conference Room Booking Agent
Integrates with AWS Bedrock AgentCore
"""

import json
import boto3
import logging
from booking_agent_fixed import (
    BookingRequest, 
    BookingOrchestrator,
    BookingStatus
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def validate_booking_request(event: dict) -> tuple[bool, str]:
    """
    Validate booking request format and required fields
    
    Args:
        event: Lambda event
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    required_fields = ['action', 'employee_id', 'room_id', 'start_time', 'end_time', 'attendee_count', 'meeting_title']
    
    for field in required_fields:
        if field not in event:
            return False, f'Missing required field: {field}'
    
    # Validate action
    valid_actions = ['sequential', 'parallel', 'confirm']
    if event['action'] not in valid_actions:
        return False, f'Invalid action. Must be one of: {", ".join(valid_actions)}'
    
    # Validate employee_id format
    if not event['employee_id'].startswith('E') or not event['employee_id'][1:].isdigit():
        return False, 'Invalid employee_id format (must be E followed by digits)'
    
    # Validate room_id format
    if not event['room_id'].startswith('R') or not event['room_id'][1:].isdigit():
        return False, 'Invalid room_id format (must be R followed by digits)'
    
    # Validate attendee_count
    try:
        attendee_count = int(event['attendee_count'])
        if attendee_count <= 0 or attendee_count > 500:
            return False, 'Attendee count must be between 1 and 500'
    except (ValueError, TypeError):
        return False, 'Attendee count must be a positive integer'
    
    # Validate times are ISO 8601
    try:
        from datetime import datetime
        start = datetime.fromisoformat(event['start_time'])
        end = datetime.fromisoformat(event['end_time'])
        
        if start >= end:
            return False, 'Start time must be before end time'
    except ValueError:
        return False, 'Times must be in ISO 8601 format'
    
    return True, None


def format_response(status_code: int, body: dict) -> dict:
    """
    Format Lambda response
    
    Args:
        status_code: HTTP status code
        body: Response body
        
    Returns:
        Formatted Lambda response
    """
    return {
        'statusCode': status_code,
        'body': json.dumps(body),
        'headers': {
            'Content-Type': 'application/json'
        }
    }


def handle_sequential_booking(event: dict) -> dict:
    """
    Handle sequential booking execution
    
    Args:
        event: Lambda event
        
    Returns:
        Booking result
    """
    try:
        booking_request = BookingRequest(
            employee_id=event['employee_id'],
            room_id=event['room_id'],
            start_time=event['start_time'],
            end_time=event['end_time'],
            attendee_count=int(event['attendee_count']),
            meeting_title=event['meeting_title']
        )
        
        orchestrator = BookingOrchestrator()
        
        # Execute sequentially (using sync wrapper for Lambda)
        result = execute_sync(orchestrator.execute_sequential(booking_request))
        
        if result['status'] == BookingStatus.PENDING_CONFIRMATION.value:
            return {
                'success': True,
                'status': result['status'],
                'confirmation_required': True,
                'summary': result.get('confirmation_summary'),
                'execution_mode': 'sequential'
            }
        else:
            return {
                'success': False,
                'status': result['status'],
                'error': result.get('error'),
                'step_failed': result.get('step_failed')
            }
            
    except Exception as e:
        logger.error(f"Sequential execution error: {str(e)}")
        return {
            'success': False,
            'status': BookingStatus.FAILED.value,
            'error': f'Sequential execution failed: {str(e)}'
        }


def handle_parallel_booking(event: dict) -> dict:
    """
    Handle parallel booking execution
    
    Args:
        event: Lambda event
        
    Returns:
        Booking result
    """
    try:
        booking_request = BookingRequest(
            employee_id=event['employee_id'],
            room_id=event['room_id'],
            start_time=event['start_time'],
            end_time=event['end_time'],
            attendee_count=int(event['attendee_count']),
            meeting_title=event['meeting_title']
        )
        
        orchestrator = BookingOrchestrator()
        
        # Execute parallely (using sync wrapper for Lambda)
        result = execute_sync(orchestrator.execute_parallel(booking_request))
        
        if result['status'] == BookingStatus.PENDING_CONFIRMATION.value:
            return {
                'success': True,
                'status': result['status'],
                'confirmation_required': True,
                'summary': result.get('confirmation_summary'),
                'execution_mode': 'parallel'
            }
        else:
            return {
                'success': False,
                'status': result['status'],
                'error': result.get('error'),
                'step_failed': result.get('step_failed')
            }
            
    except Exception as e:
        logger.error(f"Parallel execution error: {str(e)}")
        return {
            'success': False,
            'status': BookingStatus.FAILED.value,
            'error': f'Parallel execution failed: {str(e)}'
        }


def handle_confirm_booking(event: dict) -> dict:
    """
    Handle booking confirmation
    
    Args:
        event: Lambda event with 'confirmed' field
        
    Returns:
        Confirmation result
    """
    try:
        if 'confirmed' not in event:
            return {
                'success': False,
                'error': 'Missing confirmed field'
            }
        
        booking_request = BookingRequest(
            employee_id=event['employee_id'],
            room_id=event['room_id'],
            start_time=event['start_time'],
            end_time=event['end_time'],
            attendee_count=int(event['attendee_count']),
            meeting_title=event['meeting_title']
        )
        
        orchestrator = BookingOrchestrator()
        confirmed = event.get('confirmed', False)
        
        result = orchestrator.confirm_booking(booking_request, confirmed)
        
        return {
            'success': result.get('database_record_created', False),
            'status': result.get('status'),
            'booking_id': result.get('booking_id'),
            'message': result.get('message'),
            'error': result.get('error')
        }
        
    except Exception as e:
        logger.error(f"Confirmation error: {str(e)}")
        return {
            'success': False,
            'status': BookingStatus.FAILED.value,
            'error': f'Booking confirmation failed: {str(e)}'
        }


def execute_sync(coro):
    """
    Execute async coroutine synchronously (for Lambda)
    
    Args:
        coro: Coroutine to execute
        
    Returns:
        Coroutine result
    """
    import asyncio
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(coro)


def lambda_handler(event, context):
    """
    Main Lambda handler
    
    Event format:
    {
        "action": "sequential|parallel|confirm",
        "employee_id": "E001",
        "room_id": "R001",
        "start_time": "2026-01-16T09:00:00",
        "end_time": "2026-01-16T11:00:00",
        "attendee_count": 5,
        "meeting_title": "Team Sync",
        "confirmed": true  # Only for confirm action
    }
    
    Returns:
        Lambda response with booking result
    """
    
    logger.info(f"Received event: {json.dumps(event)}")
    
    # Validate request
    is_valid, error = validate_booking_request(event)
    if not is_valid:
        logger.error(f"Validation error: {error}")
        return format_response(400, {
            'error': 'Validation failed',
            'details': error
        })
    
    action = event.get('action')
    
    try:
        if action == 'sequential':
            result = handle_sequential_booking(event)
        elif action == 'parallel':
            result = handle_parallel_booking(event)
        elif action == 'confirm':
            result = handle_confirm_booking(event)
        else:
            return format_response(400, {
                'error': 'Invalid action'
            })
        
        status_code = 200 if result.get('success') else 400
        
        return format_response(status_code, {
            'success': result.get('success'),
            'action': action,
            'result': result
        })
        
    except Exception as e:
        logger.error(f"Handler error: {str(e)}", exc_info=True)
        return format_response(500, {
            'error': 'Internal server error',
            'details': str(e)
        })