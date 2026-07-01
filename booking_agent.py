"""
Conference Room Booking Agent - Main Implementation
Handles multi-agent orchestration with AWS Bedrock and DynamoDB
"""

import json
import boto3
import uuid
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple
from enum import Enum
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS Clients
dynamodb = boto3.resource('dynamodb', region_name='ap-south-1')
bedrock_agent = boto3.client('bedrock-agent-runtime', region_name='ap-south-1')

# DynamoDB Tables
EMPLOYEES_TABLE = dynamodb.Table('Employees')
ROOMS_TABLE = dynamodb.Table('ConferenceRooms')
BOOKINGS_TABLE = dynamodb.Table('Bookings')
ROOM_FEATURES_TABLE = dynamodb.Table('RoomFeatures')
ACCESS_LEVELS_TABLE = dynamodb.Table('AccessLevels')


class AccessLevel(Enum):
    """Access level hierarchy"""
    BASIC = 0
    STANDARD = 1
    PREMIUM = 2
    EXECUTIVE = 3


class BookingStatus(Enum):
    """Booking status values"""
    PENDING_CONFIRMATION = "PENDING_CONFIRMATION"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


@dataclass
class BookingRequest:
    """Booking request structure"""
    employee_id: str
    room_id: str
    start_time: str  # ISO 8601 format
    end_time: str    # ISO 8601 format
    attendee_count: int
    meeting_title: str


class ToolExecutor:
    """Executes booking tools with error handling"""
    
    @staticmethod
    def verify_employee_access(employee_id: str, room_id: str) -> Dict:
        """
        Verify employee has access to book a specific room
        
        Args:
            employee_id: Employee ID
            room_id: Room ID
            
        Returns:
            Dict with access_granted, employee_name, access_level, error
        """
        try:
            # Get employee
            emp_response = EMPLOYEES_TABLE.get_item(Key={'EmployeeID': employee_id})
            if 'Item' not in emp_response:
                return {
                    'access_granted': False,
                    'error': f'Employee {employee_id} not found'
                }
            
            employee = emp_response['Item']
            emp_access_level = employee.get('AccessLevel', 'BASIC')
            emp_name = employee.get('Name', 'Unknown')
            
            # Get room requirements
            room_response = ROOMS_TABLE.get_item(Key={'RoomID': room_id})
            if 'Item' not in room_response:
                return {
                    'access_granted': False,
                    'error': f'Room {room_id} not found'
                }
            
            room = room_response['Item']
            required_level = room.get('RequiredAccessLevel', 'BASIC')
            
            # Check access hierarchy
            emp_level_value = AccessLevel[emp_access_level].value
            req_level_value = AccessLevel[required_level].value
            
            access_granted = emp_level_value >= req_level_value
            
            return {
                'access_granted': access_granted,
                'employee_name': emp_name,
                'access_level': emp_access_level,
                'room_required_level': required_level,
                'error': None if access_granted else f'Access level {emp_access_level} insufficient for room {room_id}'
            }
            
        except Exception as e:
            logger.error(f"Error verifying access: {str(e)}")
            return {
                'access_granted': False,
                'error': f'Access verification failed: {str(e)}'
            }
    
    @staticmethod
    def check_room_availability(room_id: str, start_time: str, end_time: str) -> Dict:
        """
        Check if room is available for time slot
        
        Args:
            room_id: Room ID
            start_time: Start time (ISO 8601)
            end_time: End time (ISO 8601)
            
        Returns:
            Dict with available, conflicts, error
        """
        try:
            from datetime import datetime, timedelta
            
            req_start = datetime.fromisoformat(start_time)
            req_end = datetime.fromisoformat(end_time)
            buffer_minutes = 15
            buffer = timedelta(minutes=buffer_minutes)
            
            # Query existing bookings
            response = BOOKINGS_TABLE.query(
                KeyConditionExpression='RoomID = :rid',
                FilterExpression='BookingStatus = :status',
                ExpressionAttributeValues={
                    ':rid': room_id,
                    ':status': 'CONFIRMED'
                }
            )
            
            conflicts = []
            for booking in response.get('Items', []):
                booking_start = datetime.fromisoformat(booking['StartTime'])
                booking_end = datetime.fromisoformat(booking['EndTime'])
                
                # Check for overlap with buffer
                if not (req_end + buffer <= booking_start or req_start - buffer >= booking_end):
                    conflicts.append({
                        'booking_id': booking.get('BookingID'),
                        'existing_start': booking['StartTime'],
                        'existing_end': booking['EndTime']
                    })
            
            return {
                'available': len(conflicts) == 0,
                'conflicts': conflicts,
                'buffer_minutes': buffer_minutes,
                'error': None if not conflicts else f'{len(conflicts)} booking conflict(s) found'
            }
            
        except Exception as e:
            logger.error(f"Error checking availability: {str(e)}")
            return {
                'available': False,
                'conflicts': [],
                'error': f'Availability check failed: {str(e)}'
            }
    
    @staticmethod
    def calculate_meeting_duration(start_time: str, end_time: str, access_level: str) -> Dict:
        """
        Calculate meeting duration and validate against access level limits
        
        Args:
            start_time: Start time (ISO 8601)
            end_time: End time (ISO 8601)
            access_level: Access level of employee
            
        Returns:
            Dict with duration info and validation result
        """
        try:
            from datetime import datetime
            
            start = datetime.fromisoformat(start_time)
            end = datetime.fromisoformat(end_time)
            
            delta = end - start
            hours = delta.total_seconds() / 3600
            minutes = (delta.total_seconds() % 3600) / 60
            
            # Get access level limits
            max_hours_map = {
                'BASIC': 2,
                'STANDARD': 4,
                'PREMIUM': 8,
                'EXECUTIVE': 24
            }
            
            max_hours = max_hours_map.get(access_level, 2)
            within_limit = hours <= max_hours
            
            return {
                'duration_hours': hours,
                'duration_minutes': minutes,
                'max_allowed_hours': max_hours,
                'within_limit': within_limit,
                'error': None if within_limit else f'Duration {hours}h exceeds limit of {max_hours}h for {access_level}'
            }
            
        except Exception as e:
            logger.error(f"Error calculating duration: {str(e)}")
            return {
                'duration_hours': 0,
                'duration_minutes': 0,
                'within_limit': False,
                'error': f'Duration calculation failed: {str(e)}'
            }
    
    @staticmethod
    def get_room_details(room_id: str) -> Dict:
        """
        Get complete room details including features
        
        Args:
            room_id: Room ID
            
        Returns:
            Dict with room details and features
        """
        try:
            # Get room info
            room_response = ROOMS_TABLE.get_item(Key={'RoomID': room_id})
            if 'Item' not in room_response:
                return {
                    'found': False,
                    'error': f'Room {room_id} not found'
                }
            
            room = room_response['Item']
            
            # Get features
            features_response = ROOM_FEATURES_TABLE.query(
                KeyConditionExpression='RoomID = :rid',
                ExpressionAttributeValues={':rid': room_id}
            )
            
            features = [item['FeatureName'] for item in features_response.get('Items', [])]
            
            return {
                'found': True,
                'room_name': room.get('RoomName'),
                'room_id': room_id,
                'capacity': room.get('Capacity'),
                'location': room.get('Location'),
                'floor': room.get('Floor'),
                'required_access_level': room.get('RequiredAccessLevel'),
                'features': features,
                'error': None
            }
            
        except Exception as e:
            logger.error(f"Error getting room details: {str(e)}")
            return {
                'found': False,
                'error': f'Failed to get room details: {str(e)}'
            }
    
    @staticmethod
    def validate_attendee_count(room_id: str, attendee_count: int) -> Dict:
        """
        Validate attendee count against room capacity
        
        Args:
            room_id: Room ID
            attendee_count: Number of attendees
            
        Returns:
            Dict with validation result
        """
        try:
            response = ROOMS_TABLE.get_item(Key={'RoomID': room_id})
            if 'Item' not in response:
                return {
                    'capacity_sufficient': False,
                    'error': f'Room {room_id} not found'
                }
            
            room = response['Item']
            capacity = room.get('Capacity', 0)
            
            capacity_sufficient = attendee_count <= capacity
            
            return {
                'capacity_sufficient': capacity_sufficient,
                'room_capacity': capacity,
                'attendee_count': attendee_count,
                'error': None if capacity_sufficient else f'{attendee_count} attendees exceed capacity of {capacity}'
            }
            
        except Exception as e:
            logger.error(f"Error validating attendee count: {str(e)}")
            return {
                'capacity_sufficient': False,
                'error': f'Attendee validation failed: {str(e)}'
            }
    
    @staticmethod
    def create_booking(booking_request: BookingRequest) -> Dict:
        """
        Create booking in DynamoDB
        
        Args:
            booking_request: BookingRequest object
            
        Returns:
            Dict with success status and booking details
        """
        try:
            booking_id = str(uuid.uuid4())
            created_at = datetime.utcnow().isoformat()
            
            item = {
                'RoomID': booking_request.room_id,
                'StartTime': booking_request.start_time,
                'BookingID': booking_id,
                'EmployeeID': booking_request.employee_id,
                'EndTime': booking_request.end_time,
                'AttendeeCount': booking_request.attendee_count,
                'MeetingTitle': booking_request.meeting_title,
                'BookingStatus': 'CONFIRMED',
                'CreatedAt': created_at,
                'UpdatedAt': created_at
            }
            
            # Atomic write
            BOOKINGS_TABLE.put_item(Item=item)
            
            logger.info(f"Booking created: {booking_id}")
            
            return {
                'success': True,
                'booking_id': booking_id,
                'status': 'CONFIRMED',
                'created_at': created_at,
                'error': None
            }
            
        except Exception as e:
            logger.error(f"Error creating booking: {str(e)}")
            return {
                'success': False,
                'booking_id': None,
                'status': 'FAILED',
                'error': f'Booking creation failed: {str(e)}'
            }


class BookingOrchestrator:
    """Orchestrates booking workflow"""
    
    async def execute_sequential(self, booking_request: BookingRequest) -> Dict:
        """
        Execute booking workflow sequentially
        
        Args:
            booking_request: BookingRequest object
            
        Returns:
            Dict with booking result
        """
        try:
            # Step 1: Verify Access
            access_result = ToolExecutor.verify_employee_access(
                booking_request.employee_id,
                booking_request.room_id
            )
            
            if not access_result.get('access_granted'):
                return {
                    'status': BookingStatus.FAILED.value,
                    'error': access_result.get('error'),
                    'step_failed': 'verify_access'
                }
            
            # Step 2: Check Availability
            availability_result = ToolExecutor.check_room_availability(
                booking_request.room_id,
                booking_request.start_time,
                booking_request.end_time
            )
            
            if not availability_result.get('available'):
                return {
                    'status': BookingStatus.FAILED.value,
                    'error': availability_result.get('error'),
                    'conflicts': availability_result.get('conflicts'),
                    'step_failed': 'check_availability'
                }
            
            # Step 3: Calculate Duration
            duration_result = ToolExecutor.calculate_meeting_duration(
                booking_request.start_time,
                booking_request.end_time,
                access_result.get('access_level')
            )
            
            if not duration_result.get('within_limit'):
                return {
                    'status': BookingStatus.FAILED.value,
                    'error': duration_result.get('error'),
                    'step_failed': 'calculate_duration'
                }
            
            # Step 4: Validate Capacity
            capacity_result = ToolExecutor.validate_attendee_count(
                booking_request.room_id,
                booking_request.attendee_count
            )
            
            if not capacity_result.get('capacity_sufficient'):
                return {
                    'status': BookingStatus.FAILED.value,
                    'error': capacity_result.get('error'),
                    'step_failed': 'validate_capacity'
                }
            
            # Step 5: Get Room Details
            details_result = ToolExecutor.get_room_details(booking_request.room_id)
            
            if not details_result.get('found'):
                return {
                    'status': BookingStatus.FAILED.value,
                    'error': details_result.get('error'),
                    'step_failed': 'get_room_details'
                }
            
            # Step 6: Prepare Confirmation Summary
            confirmation_summary = {
                'room_name': details_result.get('room_name'),
                'room_capacity': details_result.get('capacity'),
                'features': details_result.get('features'),
                'location': details_result.get('location'),
                'start_time': booking_request.start_time,
                'end_time': booking_request.end_time,
                'duration_hours': duration_result.get('duration_hours'),
                'attendee_count': booking_request.attendee_count,
                'meeting_title': booking_request.meeting_title
            }
            
            return {
                'status': BookingStatus.PENDING_CONFIRMATION.value,
                'confirmation_summary': confirmation_summary,
                'execution_mode': 'sequential',
                'error': None
            }
            
        except Exception as e:
            logger.error(f"Error in sequential execution: {str(e)}")
            return {
                'status': BookingStatus.FAILED.value,
                'error': f'Sequential execution failed: {str(e)}'
            }
    
    async def execute_parallel(self, booking_request: BookingRequest) -> Dict:
        """
        Execute booking workflow with parallel checks
        
        Args:
            booking_request: BookingRequest object
            
        Returns:
            Dict with booking result
        """
        try:
            import asyncio
            
            # Parallel Phase: Access + Availability
            access_result, availability_result = await asyncio.gather(
                self._async_verify_access(booking_request.employee_id, booking_request.room_id),
                self._async_check_availability(booking_request.room_id, booking_request.start_time, booking_request.end_time)
            )
            
            # Check parallel results
            if not access_result.get('access_granted'):
                return {
                    'status': BookingStatus.FAILED.value,
                    'error': access_result.get('error'),
                    'step_failed': 'verify_access'
                }
            
            if not availability_result.get('available'):
                return {
                    'status': BookingStatus.FAILED.value,
                    'error': availability_result.get('error'),
                    'conflicts': availability_result.get('conflicts'),
                    'step_failed': 'check_availability'
                }
            
            # Sequential from here
            duration_result = ToolExecutor.calculate_meeting_duration(
                booking_request.start_time,
                booking_request.end_time,
                access_result.get('access_level')
            )
            
            if not duration_result.get('within_limit'):
                return {
                    'status': BookingStatus.FAILED.value,
                    'error': duration_result.get('error'),
                    'step_failed': 'calculate_duration'
                }
            
            capacity_result = ToolExecutor.validate_attendee_count(
                booking_request.room_id,
                booking_request.attendee_count
            )
            
            if not capacity_result.get('capacity_sufficient'):
                return {
                    'status': BookingStatus.FAILED.value,
                    'error': capacity_result.get('error'),
                    'step_failed': 'validate_capacity'
                }
            
            details_result = ToolExecutor.get_room_details(booking_request.room_id)
            
            if not details_result.get('found'):
                return {
                    'status': BookingStatus.FAILED.value,
                    'error': details_result.get('error'),
                    'step_failed': 'get_room_details'
                }
            
            confirmation_summary = {
                'room_name': details_result.get('room_name'),
                'room_capacity': details_result.get('capacity'),
                'features': details_result.get('features'),
                'location': details_result.get('location'),
                'start_time': booking_request.start_time,
                'end_time': booking_request.end_time,
                'duration_hours': duration_result.get('duration_hours'),
                'attendee_count': booking_request.attendee_count,
                'meeting_title': booking_request.meeting_title
            }
            
            return {
                'status': BookingStatus.PENDING_CONFIRMATION.value,
                'confirmation_summary': confirmation_summary,
                'execution_mode': 'parallel',
                'error': None
            }
            
        except Exception as e:
            logger.error(f"Error in parallel execution: {str(e)}")
            return {
                'status': BookingStatus.FAILED.value,
                'error': f'Parallel execution failed: {str(e)}'
            }
    
    def confirm_booking(self, booking_request: BookingRequest, confirmed: bool) -> Dict:
        """
        Confirm or cancel booking
        
        Args:
            booking_request: BookingRequest object
            confirmed: Whether user confirmed
            
        Returns:
            Dict with confirmation result
        """
        try:
            if not confirmed:
                return {
                    'status': BookingStatus.CANCELLED.value,
                    'message': 'Booking cancelled by user',
                    'database_record_created': False
                }
            
            # Create booking
            result = ToolExecutor.create_booking(booking_request)
            
            return {
                'status': result.get('status'),
                'booking_id': result.get('booking_id'),
                'created_at': result.get('created_at'),
                'message': 'Booking confirmed and saved' if result.get('success') else result.get('error'),
                'database_record_created': result.get('success'),
                'error': result.get('error')
            }
            
        except Exception as e:
            logger.error(f"Error confirming booking: {str(e)}")
            return {
                'status': BookingStatus.FAILED.value,
                'message': f'Booking confirmation failed: {str(e)}',
                'database_record_created': False,
                'error': str(e)
            }
    
    async def _async_verify_access(self, employee_id: str, room_id: str) -> Dict:
        """Async wrapper for verify_employee_access"""
        return ToolExecutor.verify_employee_access(employee_id, room_id)
    
    async def _async_check_availability(self, room_id: str, start_time: str, end_time: str) -> Dict:
        """Async wrapper for check_room_availability"""
        return ToolExecutor.check_room_availability(room_id, start_time, end_time)