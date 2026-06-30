"""
Initialize DynamoDB Tables and Seed Data
Run this script once to set up the database
"""

import boto3
import time
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

dynamodb = boto3.resource('dynamodb', region_name='ap-south-1')


def create_employees_table():
    """Create Employees table"""
    try:
        table = dynamodb.create_table(
            TableName='Employees',
            KeySchema=[
                {'AttributeName': 'EmployeeID', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'EmployeeID', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        table.meta.client.get_waiter('table_exists').wait(TableName='Employees')
        logger.info("✓ Employees table created")
        return table
    except dynamodb.meta.client.exceptions.ResourceInUseException:
        logger.info("✓ Employees table already exists")
        return dynamodb.Table('Employees')


def create_conference_rooms_table():
    """Create ConferenceRooms table"""
    try:
        table = dynamodb.create_table(
            TableName='ConferenceRooms',
            KeySchema=[
                {'AttributeName': 'RoomID', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'RoomID', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        table.meta.client.get_waiter('table_exists').wait(TableName='ConferenceRooms')
        logger.info("✓ ConferenceRooms table created")
        return table
    except dynamodb.meta.client.exceptions.ResourceInUseException:
        logger.info("✓ ConferenceRooms table already exists")
        return dynamodb.Table('ConferenceRooms')


def create_bookings_table():
    """Create Bookings table with composite key"""
    try:
        table = dynamodb.create_table(
            TableName='Bookings',
            KeySchema=[
                {'AttributeName': 'RoomID', 'KeyType': 'HASH'},
                {'AttributeName': 'StartTime', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'RoomID', 'AttributeType': 'S'},
                {'AttributeName': 'StartTime', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        table.meta.client.get_waiter('table_exists').wait(TableName='Bookings')
        logger.info("✓ Bookings table created")
        return table
    except dynamodb.meta.client.exceptions.ResourceInUseException:
        logger.info("✓ Bookings table already exists")
        return dynamodb.Table('Bookings')


def create_room_features_table():
    """Create RoomFeatures table"""
    try:
        table = dynamodb.create_table(
            TableName='RoomFeatures',
            KeySchema=[
                {'AttributeName': 'RoomID', 'KeyType': 'HASH'},
                {'AttributeName': 'FeatureName', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'RoomID', 'AttributeType': 'S'},
                {'AttributeName': 'FeatureName', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        table.meta.client.get_waiter('table_exists').wait(TableName='RoomFeatures')
        logger.info("✓ RoomFeatures table created")
        return table
    except dynamodb.meta.client.exceptions.ResourceInUseException:
        logger.info("✓ RoomFeatures table already exists")
        return dynamodb.Table('RoomFeatures')


def create_access_levels_table():
    """Create AccessLevels table"""
    try:
        table = dynamodb.create_table(
            TableName='AccessLevels',
            KeySchema=[
                {'AttributeName': 'AccessLevelID', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'AccessLevelID', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        table.meta.client.get_waiter('table_exists').wait(TableName='AccessLevels')
        logger.info("✓ AccessLevels table created")
        return table
    except dynamodb.meta.client.exceptions.ResourceInUseException:
        logger.info("✓ AccessLevels table already exists")
        return dynamodb.Table('AccessLevels')


def seed_access_levels():
    """Seed access levels"""
    table = dynamodb.Table('AccessLevels')
    
    levels = [
        {
            'AccessLevelID': 'BASIC',
            'Name': 'Basic Access',
            'Description': 'Can book up to 2 hours',
            'MaxBookingHours': 2,
            'Priority': 0
        },
        {
            'AccessLevelID': 'STANDARD',
            'Name': 'Standard Access',
            'Description': 'Can book up to 4 hours',
            'MaxBookingHours': 4,
            'Priority': 1
        },
        {
            'AccessLevelID': 'PREMIUM',
            'Name': 'Premium Access',
            'Description': 'Can book up to 8 hours',
            'MaxBookingHours': 8,
            'Priority': 2
        },
        {
            'AccessLevelID': 'EXECUTIVE',
            'Name': 'Executive Access',
            'Description': 'Can book up to 24 hours',
            'MaxBookingHours': 24,
            'Priority': 3
        }
    ]
    
    for level in levels:
        table.put_item(Item=level)
    
    logger.info(f"✓ Seeded {len(levels)} access levels")


def seed_employees():
    """Seed employee data"""
    table = dynamodb.Table('Employees')
    
    employees = [
        {
            'EmployeeID': 'E001',
            'Name': 'Alice Johnson',
            'Email': 'alice.johnson@company.com',
            'Department': 'Engineering',
            'AccessLevel': 'EXECUTIVE',
            'CreatedAt': datetime.utcnow().isoformat()
        },
        {
            'EmployeeID': 'E002',
            'Name': 'Bob Smith',
            'Email': 'bob.smith@company.com',
            'Department': 'Product',
            'AccessLevel': 'PREMIUM',
            'CreatedAt': datetime.utcnow().isoformat()
        },
        {
            'EmployeeID': 'E003',
            'Name': 'Carol Davis',
            'Email': 'carol.davis@company.com',
            'Department': 'Sales',
            'AccessLevel': 'STANDARD',
            'CreatedAt': datetime.utcnow().isoformat()
        },
        {
            'EmployeeID': 'E004',
            'Name': 'David Wilson',
            'Email': 'david.wilson@company.com',
            'Department': 'Support',
            'AccessLevel': 'BASIC',
            'CreatedAt': datetime.utcnow().isoformat()
        },
        {
            'EmployeeID': 'E005',
            'Name': 'Emma Martinez',
            'Email': 'emma.martinez@company.com',
            'Department': 'Marketing',
            'AccessLevel': 'STANDARD',
            'CreatedAt': datetime.utcnow().isoformat()
        }
    ]
    
    for emp in employees:
        table.put_item(Item=emp)
    
    logger.info(f"✓ Seeded {len(employees)} employees")


def seed_conference_rooms():
    """Seed conference room data"""
    table = dynamodb.Table('ConferenceRooms')
    
    rooms = [
        {
            'RoomID': 'R001',
            'RoomName': 'Innovation Hub',
            'Capacity': 20,
            'Location': 'Building A, Floor 2',
            'Floor': '2',
            'RequiredAccessLevel': 'BASIC',
            'Amenities': 'Whiteboard, 4K Display, Video Conferencing',
            'CreatedAt': datetime.utcnow().isoformat()
        },
        {
            'RoomID': 'R002',
            'RoomName': 'Board Room',
            'Capacity': 15,
            'Location': 'Building A, Floor 3',
            'Floor': '3',
            'RequiredAccessLevel': 'STANDARD',
            'Amenities': 'Speakerphone, Video Conferencing, 4K Display',
            'CreatedAt': datetime.utcnow().isoformat()
        },
        {
            'RoomID': 'R003',
            'RoomName': 'Executive Suite',
            'Capacity': 10,
            'Location': 'Building B, Floor 1',
            'Floor': '1',
            'RequiredAccessLevel': 'PREMIUM',
            'Amenities': 'Premium AV, Secure Phone, 8K Display',
            'CreatedAt': datetime.utcnow().isoformat()
        },
        {
            'RoomID': 'R004',
            'RoomName': 'Training Center',
            'Capacity': 30,
            'Location': 'Building C, Floor 1',
            'Floor': '1',
            'RequiredAccessLevel': 'BASIC',
            'Amenities': 'Projector, Multiple Screens, Recording Capability',
            'CreatedAt': datetime.utcnow().isoformat()
        },
        {
            'RoomID': 'R005',
            'RoomName': 'Client Meeting Room',
            'Capacity': 8,
            'Location': 'Building A, Floor 1',
            'Floor': '1',
            'RequiredAccessLevel': 'STANDARD',
            'Amenities': 'Video Conferencing, Projector, Coffee Station',
            'CreatedAt': datetime.utcnow().isoformat()
        },
        {
            'RoomID': 'R006',
            'RoomName': 'C-Suite Presidential Suite',
            'Capacity': 5,
            'Location': 'Building B, Floor 5',
            'Floor': '5',
            'RequiredAccessLevel': 'EXECUTIVE',
            'Amenities': 'Premium AV, Smart Controls, Secure Lines',
            'CreatedAt': datetime.utcnow().isoformat()
        }
    ]
    
    for room in rooms:
        table.put_item(Item=room)
    
    logger.info(f"✓ Seeded {len(rooms)} conference rooms")


def seed_room_features():
    """Seed room features"""
    table = dynamodb.Table('RoomFeatures')
    
    features = [
        # R001 Features
        {'RoomID': 'R001', 'FeatureName': 'Projector', 'AddedAt': datetime.utcnow().isoformat()},
        {'RoomID': 'R001', 'FeatureName': 'Video Conferencing', 'AddedAt': datetime.utcnow().isoformat()},
        {'RoomID': 'R001', 'FeatureName': 'Whiteboard', 'AddedAt': datetime.utcnow().isoformat()},
        {'RoomID': 'R001', 'FeatureName': 'High Speed Internet', 'AddedAt': datetime.utcnow().isoformat()},
        # R002 Features
        {'RoomID': 'R002', 'FeatureName': 'Projector', 'AddedAt': datetime.utcnow().isoformat()},
        {'RoomID': 'R002', 'FeatureName': 'Video Conferencing', 'AddedAt': datetime.utcnow().isoformat()},
        {'RoomID': 'R002', 'FeatureName': 'Speakerphone', 'AddedAt': datetime.utcnow().isoformat()},
        {'RoomID': 'R002', 'FeatureName': '4K Display', 'AddedAt': datetime.utcnow().isoformat()},
        # R003 Features
        {'RoomID': 'R003', 'FeatureName': 'Video Conferencing', 'AddedAt': datetime.utcnow().isoformat()},
        {'RoomID': 'R003', 'FeatureName': 'Secure Phone Lines', 'AddedAt': datetime.utcnow().isoformat()},
        {'RoomID': 'R003', 'FeatureName': 'Premium Sound System', 'AddedAt': datetime.utcnow().isoformat()},
        {'RoomID': 'R003', 'FeatureName': '8K Display', 'AddedAt': datetime.utcnow().isoformat()},
        # R004 Features
        {'RoomID': 'R004', 'FeatureName': 'Projector', 'AddedAt': datetime.utcnow().isoformat()},
        {'RoomID': 'R004', 'FeatureName': 'Multiple Screens', 'AddedAt': datetime.utcnow().isoformat()},
        {'RoomID': 'R004', 'FeatureName': 'Whiteboard', 'AddedAt': datetime.utcnow().isoformat()},
        {'RoomID': 'R004', 'FeatureName': 'Recording Capability', 'AddedAt': datetime.utcnow().isoformat()},
        # R005 Features
        {'RoomID': 'R005', 'FeatureName': 'Video Conferencing', 'AddedAt': datetime.utcnow().isoformat()},
        {'RoomID': 'R005', 'FeatureName': 'Projector', 'AddedAt': datetime.utcnow().isoformat()},
        {'RoomID': 'R005', 'FeatureName': 'Coffee Station', 'AddedAt': datetime.utcnow().isoformat()},
        {'RoomID': 'R005', 'FeatureName': '4K Display', 'AddedAt': datetime.utcnow().isoformat()},
        # R006 Features
        {'RoomID': 'R006', 'FeatureName': 'Premium AV System', 'AddedAt': datetime.utcnow().isoformat()},
        {'RoomID': 'R006', 'FeatureName': 'Video Conferencing', 'AddedAt': datetime.utcnow().isoformat()},
        {'RoomID': 'R006', 'FeatureName': 'Secure Phone Lines', 'AddedAt': datetime.utcnow().isoformat()},
        {'RoomID': 'R006', 'FeatureName': 'Smart Controls', 'AddedAt': datetime.utcnow().isoformat()},
    ]
    
    for feature in features:
        table.put_item(Item=feature)
    
    logger.info(f"✓ Seeded {len(features)} room features")


def seed_sample_bookings():
    """Seed sample bookings for testing"""
    table = dynamodb.Table('Bookings')
    
    bookings = [
        {
            'RoomID': 'R001',
            'StartTime': '2026-01-16T02:00:00',
            'BookingID': '550e8400-e29b-41d4-a716-446655440001',
            'EmployeeID': 'E001',
            'EndTime': '2026-01-16T03:00:00',
            'AttendeeCount': 5,
            'MeetingTitle': 'Team Standup',
            'BookingStatus': 'CONFIRMED',
            'CreatedAt': datetime.utcnow().isoformat(),
            'UpdatedAt': datetime.utcnow().isoformat()
        },
        {
            'RoomID': 'R002',
            'StartTime': '2026-01-16T04:00:00',
            'BookingID': '550e8400-e29b-41d4-a716-446655440002',
            'EmployeeID': 'E002',
            'EndTime': '2026-01-16T06:00:00',
            'AttendeeCount': 8,
            'MeetingTitle': 'Product Review',
            'BookingStatus': 'CONFIRMED',
            'CreatedAt': datetime.utcnow().isoformat(),
            'UpdatedAt': datetime.utcnow().isoformat()
        },
        {
            'RoomID': 'R004',
            'StartTime': '2026-01-16T01:00:00',
            'BookingID': '550e8400-e29b-41d4-a716-446655440003',
            'EmployeeID': 'E003',
            'EndTime': '2026-01-16T02:00:00',
            'AttendeeCount': 15,
            'MeetingTitle': 'Training Session',
            'BookingStatus': 'CONFIRMED',
            'CreatedAt': datetime.utcnow().isoformat(),
            'UpdatedAt': datetime.utcnow().isoformat()
        }
    ]
    
    for booking in bookings:
        table.put_item(Item=booking)
    
    logger.info(f"✓ Seeded {len(bookings)} sample bookings")


def verify_tables():
    """Verify all tables exist"""
    try:
        tables = ['Employees', 'ConferenceRooms', 'Bookings', 'RoomFeatures', 'AccessLevels']
        existing_tables = dynamodb.meta.client.list_tables()['TableNames']
        
        for table_name in tables:
            if table_name in existing_tables:
                logger.info(f"✓ {table_name} table verified")
            else:
                logger.error(f"✗ {table_name} table NOT found")
                return False
        
        return True
    except Exception as e:
        logger.error(f"Error verifying tables: {str(e)}")
        return False


def main():
    """Main initialization function"""
    logger.info("=" * 60)
    logger.info("DynamoDB Table Initialization & Seeding")
    logger.info("=" * 60)
    
    try:
        # Create tables
        logger.info("\n[1/3] Creating DynamoDB tables...")
        create_access_levels_table()
        create_employees_table()
        create_conference_rooms_table()
        create_bookings_table()
        create_room_features_table()
        
        # Wait for table creation
        time.sleep(2)
        
        # Seed data
        logger.info("\n[2/3] Seeding data...")
        seed_access_levels()
        seed_employees()
        seed_conference_rooms()
        seed_room_features()
        seed_sample_bookings()
        
        # Verify
        logger.info("\n[3/3] Verifying tables...")
        if verify_tables():
            logger.info("\n" + "=" * 60)
            logger.info("✓ DATABASE INITIALIZATION COMPLETE!")
            logger.info("=" * 60)
            return True
        else:
            logger.error("\n✗ Table verification failed")
            return False
            
    except Exception as e:
        logger.error(f"Error during initialization: {str(e)}")
        return False


if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)