"""
DynamoDB Initialization Script
Creates tables and seeds sample data for Conference Room Booking System
Run this once to set up the database
"""

import boto3
import json
from datetime import datetime, timedelta
import sys

# AWS DynamoDB Client
dynamodb = boto3.resource('dynamodb', region_name='ap-south-1')

# Table names
TABLES_TO_CREATE = {
    'Employees': {
        'KeySchema': [{'AttributeName': 'EmployeeID', 'KeyType': 'HASH'}],
        'AttributeDefinitions': [{'AttributeName': 'EmployeeID', 'AttributeType': 'S'}],
        'BillingMode': 'PAY_PER_REQUEST'
    },
    'ConferenceRooms': {
        'KeySchema': [{'AttributeName': 'RoomID', 'KeyType': 'HASH'}],
        'AttributeDefinitions': [{'AttributeName': 'RoomID', 'AttributeType': 'S'}],
        'BillingMode': 'PAY_PER_REQUEST'
    },
    'Bookings': {
        'KeySchema': [
            {'AttributeName': 'RoomID', 'KeyType': 'HASH'},
            {'AttributeName': 'StartTime', 'KeyType': 'RANGE'}
        ],
        'AttributeDefinitions': [
            {'AttributeName': 'RoomID', 'AttributeType': 'S'},
            {'AttributeName': 'StartTime', 'AttributeType': 'S'}
        ],
        'BillingMode': 'PAY_PER_REQUEST'
    },
    'RoomFeatures': {
        'KeySchema': [
            {'AttributeName': 'RoomID', 'KeyType': 'HASH'},
            {'AttributeName': 'FeatureName', 'KeyType': 'RANGE'}
        ],
        'AttributeDefinitions': [
            {'AttributeName': 'RoomID', 'AttributeType': 'S'},
            {'AttributeName': 'FeatureName', 'AttributeType': 'S'}
        ],
        'BillingMode': 'PAY_PER_REQUEST'
    },
    'AccessLevels': {
        'KeySchema': [{'AttributeName': 'AccessLevelID', 'KeyType': 'HASH'}],
        'AttributeDefinitions': [{'AttributeName': 'AccessLevelID', 'AttributeType': 'S'}],
        'BillingMode': 'PAY_PER_REQUEST'
    }
}


def create_tables():
    """Create all required DynamoDB tables"""
    print("Creating DynamoDB tables...")
    
    for table_name, table_config in TABLES_TO_CREATE.items():
        try:
            # Check if table already exists
            existing_tables = dynamodb.meta.client.list_tables()['TableNames']
            
            if table_name in existing_tables:
                print(f"✓ Table '{table_name}' already exists, skipping creation")
                continue
            
            # Create table
            table = dynamodb.create_table(
                TableName=table_name,
                KeySchema=table_config['KeySchema'],
                AttributeDefinitions=table_config['AttributeDefinitions'],
                BillingMode=table_config['BillingMode']
            )
            
            # Wait for table to be created
            print(f"Creating table '{table_name}'... ", end='', flush=True)
            table.wait_until_exists()
            print("✓")
            
        except Exception as e:
            print(f"✗ Error creating table '{table_name}': {str(e)}")
            return False
    
    print("\n✓ All tables created successfully!\n")
    return True


def seed_access_levels():
    """Seed access levels data"""
    print("Seeding Access Levels...")
    table = dynamodb.Table('AccessLevels')
    
    access_levels = [
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
    
    for level in access_levels:
        table.put_item(Item=level)
        print(f"  ✓ {level['AccessLevelID']}: {level['Description']}")
    
    print()


def seed_employees():
    """Seed employee data"""
    print("Seeding Employees...")
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
    
    for employee in employees:
        table.put_item(Item=employee)
        print(f"  ✓ {employee['EmployeeID']}: {employee['Name']} ({employee['AccessLevel']})")
    
    print()


def seed_conference_rooms():
    """Seed conference room data"""
    print("Seeding Conference Rooms...")
    table = dynamodb.Table('ConferenceRooms')
    
    rooms = [
        {
            'RoomID': 'R001',
            'RoomName': 'Innovation Hub',
            'Location': 'Building A, Floor 2',
            'Floor': '2',
            'Capacity': 20,
            'RequiredAccessLevel': 'BASIC',
            'Amenities': 'Whiteboard, 4K Display',
            'CreatedAt': datetime.utcnow().isoformat()
        },
        {
            'RoomID': 'R002',
            'RoomName': 'Board Room',
            'Location': 'Building A, Floor 5',
            'Floor': '5',
            'Capacity': 15,
            'RequiredAccessLevel': 'STANDARD',
            'Amenities': 'Video Conference System, Projector',
            'CreatedAt': datetime.utcnow().isoformat()
        },
        {
            'RoomID': 'R003',
            'RoomName': 'Executive Suite',
            'Location': 'Building B, Floor 8',
            'Floor': '8',
            'Capacity': 10,
            'RequiredAccessLevel': 'PREMIUM',
            'Amenities': 'Premium Sound System, Secure Phone Lines',
            'CreatedAt': datetime.utcnow().isoformat()
        },
        {
            'RoomID': 'R004',
            'RoomName': 'Training Center',
            'Location': 'Building A, Floor 3',
            'Floor': '3',
            'Capacity': 30,
            'RequiredAccessLevel': 'BASIC',
            'Amenities': 'Projector, Multiple Screens',
            'CreatedAt': datetime.utcnow().isoformat()
        },
        {
            'RoomID': 'R005',
            'RoomName': 'Client Meeting Room',
            'Location': 'Building C, Floor 1',
            'Floor': '1',
            'Capacity': 8,
            'RequiredAccessLevel': 'STANDARD',
            'Amenities': 'Video Conference, Coffee Station',
            'CreatedAt': datetime.utcnow().isoformat()
        },
        {
            'RoomID': 'R006',
            'RoomName': 'C-Suite Presidential Suite',
            'Location': 'Building B, Floor 10',
            'Floor': '10',
            'Capacity': 5,
            'RequiredAccessLevel': 'EXECUTIVE',
            'Amenities': 'Premium AV System, Private Elevator Access',
            'CreatedAt': datetime.utcnow().isoformat()
        }
    ]
    
    for room in rooms:
        table.put_item(Item=room)
        print(f"  ✓ {room['RoomID']}: {room['RoomName']} (Capacity: {room['Capacity']}, Access: {room['RequiredAccessLevel']})")
    
    print()


def seed_room_features():
    """Seed room features data"""
    print("Seeding Room Features...")
    table = dynamodb.Table('RoomFeatures')
    
    features = [
        # R001 - Innovation Hub
        ('R001', 'Projector'),
        ('R001', 'Video Conferencing'),
        ('R001', 'Whiteboard'),
        ('R001', 'High Speed Internet'),
        
        # R002 - Board Room
        ('R002', 'Projector'),
        ('R002', 'Video Conferencing'),
        ('R002', 'Speakerphone'),
        ('R002', '4K Display'),
        
        # R003 - Executive Suite
        ('R003', 'Video Conferencing'),
        ('R003', 'Secure Phone Lines'),
        ('R003', 'Premium Sound System'),
        ('R003', '8K Display'),
        
        # R004 - Training Center
        ('R004', 'Projector'),
        ('R004', 'Multiple Screens'),
        ('R004', 'Whiteboard'),
        ('R004', 'Recording Capability'),
        
        # R005 - Client Meeting Room
        ('R005', 'Video Conferencing'),
        ('R005', 'Projector'),
        ('R005', 'Coffee Station'),
        ('R005', '4K Display'),
        
        # R006 - C-Suite Presidential Suite
        ('R006', 'Premium AV System'),
        ('R006', 'Video Conferencing'),
        ('R006', 'Secure Phone Lines'),
        ('R006', 'Smart Controls'),
    ]
    
    for room_id, feature in features:
        table.put_item(Item={
            'RoomID': room_id,
            'FeatureName': feature,
            'AddedAt': datetime.utcnow().isoformat()
        })
        print(f"  ✓ {room_id}: {feature}")
    
    print()


def seed_sample_bookings():
    """Seed sample booking data for testing"""
    print("Seeding Sample Bookings...")
    table = dynamodb.Table('Bookings')
    
    base_date = datetime.utcnow()
    
    bookings = [
        {
            'BookingID': 'B001',
            'RoomID': 'R001',
            'StartTime': (base_date + timedelta(hours=2)).isoformat(),
            'EndTime': (base_date + timedelta(hours=3)).isoformat(),
            'EmployeeID': 'E001',
            'AttendeeCount': 10,
            'MeetingTitle': 'Team Standup',
            'BookingStatus': 'CONFIRMED',
            'CreatedAt': base_date.isoformat(),
            'UpdatedAt': base_date.isoformat()
        },
        {
            'BookingID': 'B002',
            'RoomID': 'R002',
            'StartTime': (base_date + timedelta(hours=4)).isoformat(),
            'EndTime': (base_date + timedelta(hours=6)).isoformat(),
            'EmployeeID': 'E002',
            'AttendeeCount': 8,
            'MeetingTitle': 'Product Review',
            'BookingStatus': 'CONFIRMED',
            'CreatedAt': base_date.isoformat(),
            'UpdatedAt': base_date.isoformat()
        },
        {
            'BookingID': 'B003',
            'RoomID': 'R004',
            'StartTime': (base_date + timedelta(hours=1)).isoformat(),
            'EndTime': (base_date + timedelta(hours=2)).isoformat(),
            'EmployeeID': 'E003',
            'AttendeeCount': 25,
            'MeetingTitle': 'Training Session',
            'BookingStatus': 'CONFIRMED',
            'CreatedAt': base_date.isoformat(),
            'UpdatedAt': base_date.isoformat()
        }
    ]
    
    for booking in bookings:
        table.put_item(Item=booking)
        print(f"  ✓ {booking['BookingID']}: {booking['MeetingTitle']} at {booking['RoomID']}")
    
    print()


def verify_tables():
    """Verify all tables were created successfully"""
    print("Verifying tables...")
    existing_tables = dynamodb.meta.client.list_tables()['TableNames']
    
    for table_name in TABLES_TO_CREATE.keys():
        if table_name in existing_tables:
            table = dynamodb.Table(table_name)
            item_count = table.item_count
            print(f"  ✓ {table_name} (Items: {item_count})")
        else:
            print(f"  ✗ {table_name} (NOT FOUND)")
            return False
    
    print("\n✓ All tables verified successfully!\n")
    return True


def main():
    """Main initialization function"""
    print("=" * 60)
    print("Conference Room Booking System - DynamoDB Initialization")
    print("=" * 60)
    print()
    
    try:
        # Step 1: Create tables
        if not create_tables():
            print("✗ Failed to create tables. Aborting.")
            return False
        
        # Step 2: Seed data
        seed_access_levels()
        seed_employees()
        seed_conference_rooms()
        seed_room_features()
        seed_sample_bookings()
        
        # Step 3: Verify
        if not verify_tables():
            print("✗ Verification failed.")
            return False
        
        print("=" * 60)
        print("✓ Database initialization completed successfully!")
        print("=" * 60)
        print()
        print("Sample Data Summary:")
        print(f"  • Access Levels: 4 levels (BASIC, STANDARD, PREMIUM, EXECUTIVE)")
        print(f"  • Employees: 5 employees with varying access levels")
        print(f"  • Rooms: 6 conference rooms with different capacities")
        print(f"  • Features: 23 room features distributed across rooms")
        print(f"  • Sample Bookings: 3 existing bookings for reference")
        print()
        return True
        
    except Exception as e:
        print(f"✗ Fatal error: {str(e)}")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)