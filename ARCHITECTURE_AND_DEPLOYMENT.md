# Architecture & Deployment Guide

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    AWS Bedrock AgentCore                         │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │         Claude 3 Sonnet Language Model                   │   │
│  │  ┌────────────────────────────────────────────────────┐  │   │
│  │  │  Conference Room Booking Agent                     │  │   │
│  │  │  - Understands natural language requests           │  │   │
│  │  │  - Orchestrates multi-step workflows               │  │   │
│  │  │  - Handles human-in-the-loop confirmation          │  │   │
│  │  └────────────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────┘   │
│                             │                                    │
│                             ▼                                    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Tool Execution Layer (6 Available Tools)                │   │
│  │  ├─ verify_employee_access()                            │   │
│  │  ├─ check_room_availability()                           │   │
│  │  ├─ calculate_meeting_duration()                        │   │
│  │  ├─ get_room_details()                                  │   │
│  │  ├─ validate_attendee_count()                           │   │
│  │  └─ create_booking()                                    │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    AWS Lambda Functions                          │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Lambda: booking-tool-executor                          │   │
│  │  - Executes Bedrock tools                               │   │
│  │  - Handles async operations                             │   │
│  │  - Returns structured results                           │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Amazon DynamoDB                               │
│  ┌──────────────────┐  ┌──────────────────┐                     │
│  │   Employees      │  │ ConferenceRooms  │                     │
│  │  (EmployeeID)    │  │  (RoomID)        │                     │
│  └──────────────────┘  └──────────────────┘                     │
│  ┌──────────────────┐  ┌──────────────────┐                     │
│  │   Bookings       │  │  RoomFeatures    │                     │
│  │  (RoomID-Time)   │  │  (RoomID-Name)   │                     │
│  └──────────────────┘  └──────────────────┘                     │
│  ┌──────────────────┐                                           │
│  │   AccessLevels   │                                           │
│  │  (LevelID)       │                                           │
│  └──────────────────┘                                           │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow Diagram

```
User/Client
    │
    ├─ Natural Language Request
    │  "Book the board room for 2 hours at 2pm"
    │
    ▼
Bedrock Agent
    │
    ├─ Step 1: Verify Access [Sequential/Parallel]
    │    └─ Query: Employees table → Check access level
    │
    ├─ Step 2: Check Availability [Sequential/Parallel]
    │    └─ Query: Bookings table → Detect conflicts
    │
    ├─ Step 3: Calculate Duration [Sequential]
    │    └─ Compute: Start time - End time → Validate limit
    │
    ├─ Step 4: Validate Capacity [Sequential]
    │    └─ Query: ConferenceRooms table → Check capacity
    │
    ├─ Step 5: Get Room Details [Sequential]
    │    └─ Query: RoomFeatures table → Retrieve amenities
    │
    ├─ Step 6: Present Confirmation [Sequential]
    │    └─ Display: Summary to user
    │         "Do you confirm this booking?"
    │
    ├─ Human Input: YES/NO
    │
    ▼
Confirmation Handler
    │
    ├─ If YES:
    │    └─ Write: BookingID + Status=CONFIRMED to DynamoDB
    │       └─ Return: Booking ID and confirmation
    │
    ├─ If NO:
    │    └─ Cancel: No database write
    │       └─ Return: Cancellation confirmation
    │
    ▼
Response to User
```

---

## Deployment Topology

### Option 1: Bedrock AgentCore (Recommended)

**Best for:** Production deployments with high availability

```
AWS Bedrock AgentCore
    │
    ├─ Managed: No infrastructure management
    ├─ Scalable: Auto-scaling included
    ├─ Monitoring: CloudWatch integration
    └─ Cost: Pay-per-invocation
```

**Deployment Steps:**

```bash
# 1. Create IAM Role
aws iam create-role \
  --role-name BedrockAgentRole \
  --assume-role-policy-document file://trust-policy.json

# 2. Attach Policies
aws iam attach-role-policy \
  --role-name BedrockAgentRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess

# 3. Create Agent
aws bedrock-agent create-agent \
  --agent-name ConferenceRoomBookingAgent \
  --foundation-model claude-3-sonnet-20240229 \
  --agent-resource-role-arn arn:aws:iam::ACCOUNT:role/BedrockAgentRole \
  --instruction "System instructions..."

# 4. Add Tools
aws bedrock-agent create-agent-action-group \
  --agent-id AGENT-ID \
  --action-group-name BookingTools \
  --action-group-executor-type LAMBDA \
  --agent-action-group-executor-lambda-arn arn:aws:lambda:region:account:function:booking-tools

# 5. Prepare Agent
aws bedrock-agent prepare-agent --agent-id AGENT-ID
```

### Option 2: AWS Lambda + API Gateway

**Best for:** Serverless API endpoints

```
API Gateway
    │
    ├─ Method: POST /booking
    ├─ Auth: API Key or OAuth
    │
    ▼
Lambda Function (booking_agent)
    │
    ├─ Runtime: Python 3.12
    ├─ Memory: 1024 MB
    ├─ Timeout: 60 seconds
    │
    ▼
DynamoDB
    └─ Tables: Employees, Rooms, Bookings, etc.
```

**Deployment:**

```bash
# 1. Package code
zip -r lambda.zip booking_agent.py agent_tools_config.py

# 2. Create function
aws lambda create-function \
  --function-name conference-room-booking \
  --runtime python3.12 \
  --role arn:aws:iam::ACCOUNT:role/lambda-role \
  --handler lambda_handler.handler \
  --zip-file fileb://lambda.zip \
  --timeout 60 \
  --memory-size 1024

# 3. Create API Gateway
aws apigateway create-rest-api \
  --name booking-api \
  --description "Conference Room Booking API"

# 4. Deploy
aws apigateway create-deployment \
  --rest-api-id API-ID \
  --stage-name prod
```

### Option 3: ECS/Fargate (Containerized)

**Best for:** Long-running processes or workflows

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY booking_agent.py .
COPY initialize_dynamodb.py .

CMD ["python", "-m", "uvicorn", "api:app", "--host", "0.0.0.0"]
```

---

## Performance Optimization

### Database Optimization

**1. DynamoDB Settings:**

```python
# On-demand pricing (recommended for variable load)
table.billing_mode = 'PAY_PER_REQUEST'

# Provisioned capacity (for predictable load)
table.provisioned_throughput = {
    'ReadCapacityUnits': 100,
    'WriteCapacityUnits': 50
}

# Global Secondary Indexes for faster queries
GSI = {
    'IndexName': 'EmployeeIDIndex',
    'KeySchema': [{'AttributeName': 'EmployeeID', 'KeyType': 'HASH'}],
    'Projection': {'ProjectionType': 'ALL'}
}
```

**2. Query Optimization:**

```python
# Use projection expressions to reduce data transfer
response = BOOKINGS_TABLE.query(
    KeyConditionExpression='RoomID = :rid',
    ProjectionExpression='BookingID, StartTime, EndTime, BookingStatus',
    ExpressionAttributeValues={':rid': room_id}
)

# Use batch operations for multiple items
with EMPLOYEES_TABLE.batch_writer() as batch:
    for employee in employees:
        batch.put_item(Item=employee)
```

**3. Caching Strategy:**

```python
import functools
from datetime import datetime, timedelta

# Cache room details for 1 hour
@functools.lru_cache(maxsize=128)
def get_cached_room_details(room_id):
    return ToolExecutor.get_room_details(room_id)

# Cache access levels for 24 hours
def get_cached_access_level(access_level_id):
    cache_key = f"access_level:{access_level_id}"
    cached = CACHE.get(cache_key)
    if cached:
        return cached
    
    level = ToolExecutor.get_access_level(access_level_id)
    CACHE.set(cache_key, level, ex=86400)  # 24 hours
    return level
```

### Lambda Optimization

```python
# 1. Connection pooling for DynamoDB
import concurrent.futures

dynamodb_resource = boto3.resource('dynamodb')
# Resource reused across invocations

# 2. Lazy imports
def handler(event, context):
    from booking_agent import BookingOrchestrator
    orchestrator = BookingOrchestrator()
    # ...

# 3. Memory optimization
# Allocate sufficient memory for Python interpreter
# 1024 MB minimum recommended
```

### Parallel Execution Performance

```python
# Use ThreadPoolExecutor for parallel checks
import concurrent.futures

def execute_parallel_optimized(booking_request):
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        # Submit parallel tasks
        access_future = executor.submit(
            ToolExecutor.verify_employee_access,
            booking_request.employee_id,
            booking_request.room_id
        )
        availability_future = executor.submit(
            ToolExecutor.check_room_availability,
            booking_request.room_id,
            booking_request.start_time,
            booking_request.end_time
        )
        
        # Wait for both to complete
        access_result = access_future.result(timeout=5)
        availability_result = availability_future.result(timeout=5)
        
        return access_result, availability_result
```

---

## Monitoring & Logging

### CloudWatch Logging

```python
import logging
import json

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def log_booking_event(event_type, booking_id, details):
    """Log structured booking events"""
    log_entry = {
        'timestamp': datetime.utcnow().isoformat(),
        'event_type': event_type,
        'booking_id': booking_id,
        'details': details
    }
    logger.info(json.dumps(log_entry))

# Usage
log_booking_event('BOOKING_CREATED', booking_id, {
    'employee_id': 'E001',
    'room_id': 'R001',
    'duration_hours': 2
})
```

### CloudWatch Metrics

```python
import boto3

cloudwatch = boto3.client('cloudwatch')

def put_booking_metric(metric_name, value):
    """Push custom metrics to CloudWatch"""
    cloudwatch.put_metric_data(
        Namespace='ConferenceRoomBooking',
        MetricData=[
            {
                'MetricName': metric_name,
                'Value': value,
                'Unit': 'Count',
                'Timestamp': datetime.utcnow()
            }
        ]
    )

# Usage
put_booking_metric('BookingsCreated', 1)
put_booking_metric('BookingsFailed', 0)
put_booking_metric('AverageProcessingTime', 450)  # milliseconds
```

### Alarms

```bash
# Create alarm for failed bookings
aws cloudwatch put-metric-alarm \
  --alarm-name BookingProcessingFailures \
  --metric-name BookingsFailed \
  --namespace ConferenceRoomBooking \
  --statistic Sum \
  --period 300 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions arn:aws:sns:region:account:topic/alerts
```

---

## Security Hardening

### 1. IAM Least Privilege

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:Query",
        "dynamodb:PutItem"
      ],
      "Resource": [
        "arn:aws:dynamodb:region:account:table/Employees",
        "arn:aws:dynamodb:region:account:table/Bookings",
        "arn:aws:dynamodb:region:account:table/ConferenceRooms"
      ]
    }
  ]
}
```

### 2. VPC Endpoints for DynamoDB

```bash
# Create VPC endpoint to avoid internet gateway
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-xxxxx \
  --service-name com.amazonaws.region.dynamodb \
  --route-table-ids rtb-xxxxx
```

### 3. Encryption

```python
# DynamoDB encryption at rest (enabled by default)
# Lambda environment variable encryption
table = dynamodb.Table('Bookings')
table_arn = table.table_arn

# Enable encryption at rest
dynamodb.meta.client.update_table(
    TableName='Bookings',
    SSESpecification={'Enabled': True}
)
```

### 4. Input Validation

```python
def validate_and_sanitize_input(user_input):
    """Validate and sanitize all user inputs"""
    import re
    
    # Validate employee ID format
    if not re.match(r'^E\d{3}$', user_input.get('employee_id')):
        raise ValueError('Invalid employee ID format')
    
    # Validate room ID format
    if not re.match(r'^R\d{3}$', user_input.get('room_id')):
        raise ValueError('Invalid room ID format')
    
    # Validate attendee count
    if not (1 <= user_input.get('attendee_count') <= 500):
        raise ValueError('Invalid attendee count')
    
    return True
```

---

## Cost Optimization

### Estimated Monthly Costs

| Service | Usage | Cost |
|---------|-------|------|
| DynamoDB | 100K read, 50K write | $25 |
| Lambda | 100K invocations, 2s avg | $20 |
| Bedrock | 10M input tokens, 1M output | $1.50 |
| CloudWatch | Logs + metrics | $10 |
| **TOTAL** | | **$56.50** |

### Cost Reduction Strategies

```python
# 1. Use TTL for old bookings
table.update_ttl(
    AttributeName='ExpiresAt',
    Enabled=True
)

# 2. Archive old data
def archive_old_bookings(days=90):
    """Move old bookings to S3 Archive"""
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Scan and archive
    response = BOOKINGS_TABLE.scan(
        FilterExpression='CreatedAt < :date',
        ExpressionAttributeValues={':date': cutoff_date.isoformat()}
    )
    
    # Export to S3 for long-term storage
    s3.put_object(
        Bucket='booking-archive',
        Key=f'bookings/{cutoff_date.date()}.json',
        Body=json.dumps(response['Items'])
    )

# 3. Compress responses
def compress_response(data):
    import gzip
    return gzip.compress(json.dumps(data).encode())
```

---

## Disaster Recovery

### Backup Strategy

```bash
# Enable point-in-time recovery
aws dynamodb update-continuous-backups \
  --table-name Bookings \
  --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true

# Create on-demand backup
aws dynamodb create-backup \
  --table-name Bookings \
  --backup-name Bookings-$(date +%Y%m%d)

# Restore from backup
aws dynamodb restore-table-from-backup \
  --target-table-name BookingsRestored \
  --backup-arn arn:aws:dynamodb:region:account:table/Bookings/backup/xxxxx
```

### Multi-Region Deployment

```python
# Global Tables for multi-region replication
dynamodb = boto3.client('dynamodb')

dynamodb.create_global_table(
    GlobalTableName='Bookings',
    ReplicationGroup=[
        {'RegionName': 'us-east-1'},
        {'RegionName': 'eu-west-1'},
        {'RegionName': 'ap-southeast-1'}
    ]
)
```

---

## Testing Strategy

### Unit Tests

```python
import unittest
from unittest.mock import patch, MagicMock

class TestToolExecutor(unittest.TestCase):
    def setUp(self):
        self.executor = ToolExecutor()
    
    @patch('booking_agent.EMPLOYEES_TABLE')
    def test_verify_employee_access_granted(self, mock_table):
        mock_table.get_item.return_value = {
            'Item': {
                'EmployeeID': 'E001',
                'AccessLevel': 'EXECUTIVE'
            }
        }
        
        result = self.executor.verify_employee_access('E001', 'R001')
        self.assertTrue(result['access_granted'])
```

### Integration Tests

```python
import boto3
from moto import mock_dynamodb

@mock_dynamodb
def test_full_booking_workflow():
    """Test complete booking workflow with mocked DynamoDB"""
    # Create DynamoDB tables
    create_test_tables()
    
    # Run booking workflow
    result = orchestrator.execute_sequential(test_booking_request)
    
    # Verify database state
    assert result['status'] == 'PENDING_CONFIRMATION'
```

### Load Testing

```bash
# Using Apache JMeter or Locust
locust -f locustfile.py --host=https://api.endpoint.com
```

---

## Troubleshooting Guide

### Common Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| "Access Denied" | Missing IAM permissions | Attach required policies |
| "Table not found" | DynamoDB table not created | Run initialize_dynamodb.py |
| "Model not accessible" | Bedrock model not enabled | Enable in Bedrock console |
| "Lambda timeout" | Function takes too long | Increase timeout / optimize code |
| "Capacity exceeded" | DynamoDB throttling | Switch to on-demand billing |

---

**Document Version:** v1.0 — 2026