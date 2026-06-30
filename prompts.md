# Sample Prompts - Conference Room Booking System

This document contains comprehensive sample prompts for testing all execution patterns and edge cases of the Conference Room Booking system.

---

## Test Data Reference

### Employees
- **E001** - Alice Johnson | EXECUTIVE | Department: Engineering
- **E002** - Bob Smith | PREMIUM | Department: Product
- **E003** - Carol Davis | STANDARD | Department: Sales
- **E004** - David Wilson | BASIC | Department: Support
- **E005** - Emma Martinez | STANDARD | Department: Marketing

### Conference Rooms
- **R001** - Innovation Hub | Capacity: 20 | Access: BASIC | Floor 2
- **R002** - Board Room | Capacity: 15 | Access: STANDARD | Floor 5
- **R003** - Executive Suite | Capacity: 10 | Access: PREMIUM | Floor 8
- **R004** - Training Center | Capacity: 30 | Access: BASIC | Floor 3
- **R005** - Client Meeting Room | Capacity: 8 | Access: STANDARD | Floor 1
- **R006** - C-Suite Presidential Suite | Capacity: 5 | Access: EXECUTIVE | Floor 10

### Existing Bookings (for conflict testing)
- **B001** - R001 | 02:00-03:00 | Team Standup
- **B002** - R002 | 04:00-06:00 | Product Review
- **B003** - R004 | 01:00-02:00 | Training Session

### Access Level Limits
- **BASIC** - 2 hours max per booking
- **STANDARD** - 4 hours max per booking
- **PREMIUM** - 8 hours max per booking
- **EXECUTIVE** - 24 hours max per booking

---

## 1. HAPPY PATH - Successful Booking

### Scenario 1.1: Simple Conference Room Booking
```
I need to book the Innovation Hub (R001) for a team meeting.

Details:
- Employee ID: E002
- Room: R001 (Innovation Hub)
- Time: 2026-01-16T09:00:00 to 2026-01-16T11:00:00
- Attendees: 8 people
- Meeting: "Q1 Planning Session"

Please verify my access, check availability, and book the room for me.
```

**Expected Flow:**
1. ✓ Access verification: Bob Smith (PREMIUM) can access R001 (BASIC required)
2. ✓ Availability check: 09:00-11:00 is free (no conflicts)
3. ✓ Duration validation: 2 hours is within PREMIUM limit (8 hours max)
4. ✓ Capacity validation: 8 attendees fit in R001 (capacity 20)
5. ✓ Present confirmation summary
6. → User confirms: "YES"
7. ✓ Booking created with status CONFIRMED

**Database Result:**
- BookingID: [Generated UUID]
- Status: CONFIRMED
- Record created in Bookings table

---

### Scenario 1.2: Executive Books Premium Room
```
Executive booking request:

Employee: E001 (Alice Johnson - EXECUTIVE)
Room: R003 (Executive Suite)
Start Time: 2026-01-17T14:00:00
End Time: 2026-01-17T16:00:00
Attendees: 5
Meeting Title: "Board Meeting"

Process this booking with full validation.
```

**Expected Flow:**
1. ✓ Access verification: Alice (EXECUTIVE) can access R003 (PREMIUM required)
2. ✓ Availability check: No conflicts at this time
3. ✓ Duration validation: 2 hours is within EXECUTIVE limit (24 hours max)
4. ✓ Capacity validation: 5 attendees fit in R003 (capacity 10)
5. ✓ Room details retrieved with features
6. → Confirmation summary with room amenities presented
7. → User confirms: "YES"
8. ✓ Booking persisted to database

---

### Scenario 1.3: Full Duration Booking
```
I want to book the Training Center for a full-day workshop.

Details:
- Employee ID: E001 (EXECUTIVE)
- Room: R004 (Training Center)
- Start: 2026-01-18T08:00:00
- End: 2026-01-18T17:00:00 (9 hours)
- Attendees: 25
- Title: "Annual Training Workshop"

Please process this full-day booking.
```

**Expected Flow:**
1. ✓ Access: Alice (EXECUTIVE) can book R004 (BASIC required)
2. ✓ Availability: No conflicts during 08:00-17:00
3. ✓ Duration: 9 hours within EXECUTIVE limit (24 hours max)
4. ✓ Capacity: 25 attendees fit in R004 (capacity 30)
5. ✓ Features listed: Projector, Multiple Screens, Whiteboard, Recording
6. → Confirmation requested
7. → User confirms: "YES"
8. ✓ Long booking created successfully

---

## 2. INSUFFICIENT ACCESS - Permission Denied

### Scenario 2.1: Basic Employee Tries Premium Room
```
I want to book the Executive Suite for a quick team sync.

Employee: E004 (David Wilson - BASIC access)
Room: R003 (Executive Suite)
Start Time: 2026-01-15T15:00:00
End Time: 2026-01-15T17:00:00
Attendees: 3
Meeting: "Quick Sync"

Please attempt to book this room.
```

**Expected Flow:**
1. ✗ Access verification FAILS
   - David (BASIC) trying to access R003 (PREMIUM required)
   - Error: "Insufficient access level. Required: PREMIUM, Have: BASIC"
2. ✗ Workflow blocked at access verification
3. ✗ No further checks executed
4. ✗ No confirmation prompt shown
5. ✗ No database record created

**Error Response:**
```json
{
  "status": "FAILED",
  "step": "access_verification",
  "error": "Insufficient access level. Required: PREMIUM, Have: BASIC",
  "access_granted": false
}
```

---

### Scenario 2.2: Non-Executive Tries C-Suite Room
```
I need the C-Suite Presidential Suite for an all-hands meeting.

Employee: E002 (Bob Smith - PREMIUM)
Room: R006 (C-Suite Presidential Suite)
Start: 2026-01-16T10:00:00
End: 2026-01-16T12:00:00
Attendees: 20
Title: "All-Hands Meeting"

Try to book this room.
```

**Expected Result:**
- ✗ Access denied: Bob (PREMIUM) cannot access R006 (EXECUTIVE required)
- Error message clearly states access level requirement
- Booking workflow terminates at verification step

---

## 3. ROOM UNAVAILABLE - Conflicting Bookings

### Scenario 3.1: Direct Conflict with Existing Booking
```
I want to book Innovation Hub during an existing meeting.

Employee: E001
Room: R001
Start Time: 2026-01-15T02:30:00
End Time: 2026-01-15T03:30:00
Attendees: 5
Meeting: "Emergency Meeting"

Note: R001 has existing booking B001 from 02:00-03:00
```

**Expected Flow:**
1. ✓ Access verification: PASSES
2. ✗ Availability check: FAILS
   - Existing booking B001: 02:00-03:00
   - Requested: 02:30-03:30
   - Direct overlap detected
3. ✗ Workflow stops at availability check
4. Error shows conflicting booking details:
   - Booking ID: B001
   - Meeting: Team Standup
   - Time: 02:00-03:00
   - Organizer: E001

**Database Result:** No record created

---

### Scenario 3.2: Back-to-Back Booking Conflict (15-minute buffer)
```
I want to book the Board Room after an existing meeting.

Employee: E001
Room: R002
Start Time: 2026-01-15T06:00:00
End Time: 2026-01-15T08:00:00
Attendees: 8
Meeting: "Budget Review"

Note: R002 has existing booking B002 from 04:00-06:00
The 15-minute buffer means earliest start is 06:15
```

**Expected Flow:**
1. ✓ Access verification: PASSES
2. ✗ Availability check: FAILS
   - Existing booking: 04:00-06:00
   - Requested: 06:00-08:00
   - Buffer violation: New booking starts only 0 minutes after previous end
   - 15-minute buffer required
3. ✗ Workflow blocked
4. Error: "Room has 1 conflicting booking(s)"
5. Conflict details show buffer requirement

**Solution for User:**
- Start time must be 06:15 or later (06:00 + 15 minutes)

---

### Scenario 3.3: Multiple Overlapping Bookings
```
Try to book a room with multiple conflicts.

Employee: E001
Room: R004
Start Time: 2026-01-15T00:30:00
End Time: 2026-01-15T03:30:00
Attendees: 15
Meeting: "Extended Training"

Note: R004 has existing booking B003 from 01:00-02:00
Additional bookings may overlap
```

**Expected Result:**
- Availability check detects the overlap with B003
- Lists all conflicting bookings
- Suggests available time slots
- Workflow terminates without booking creation

---

## 4. DURATION EXCEEDS LIMIT - Booking Too Long

### Scenario 4.1: Basic Employee Exceeds 2-Hour Limit
```
I want to book a room for a 4-hour workshop.

Employee: E004 (David Wilson - BASIC)
Room: R001 (Innovation Hub)
Start Time: 2026-01-15T09:00:00
End Time: 2026-01-15T13:00:00 (4 hours total)
Attendees: 10
Meeting: "Extended Workshop"

BASIC access allows maximum 2 hours per booking.
```

**Expected Flow:**
1. ✓ Access verification: PASSES
2. ✓ Availability check: PASSES
3. ✗ Duration validation: FAILS
   - Calculated duration: 4 hours
   - Maximum allowed: 2 hours (BASIC level)
   - Exceeded by: 2 hours
   - Error: "Duration exceeds limit of 2 hours for BASIC access"
4. ✗ Workflow blocked
5. ✗ No confirmation shown
6. ✗ No database record

**Recommendation for User:**
- Book maximum 2-hour session
- Or request access level upgrade

---

### Scenario 4.2: Standard Employee Exceeds 4-Hour Limit
```
Request a 6-hour booking with STANDARD access.

Employee: E003 (Carol Davis - STANDARD)
Room: R002 (Board Room)
Start Time: 2026-01-16T09:00:00
End Time: 2026-01-16T15:00:00 (6 hours)
Attendees: 8
Meeting: "Full-Day Training"

STANDARD access max is 4 hours.
```

**Expected Result:**
- Duration calculation: 6 hours
- Limit check: STANDARD = 4 hours max
- Validation: FAILS
- Error message specifies the 4-hour limit
- Workflow terminates at duration validation step

---

### Scenario 4.3: Premium Employee Within Limit
```
Same request but with PREMIUM employee.

Employee: E002 (Bob Smith - PREMIUM)
Room: R002 (Board Room)
Start Time: 2026-01-16T09:00:00
End Time: 2026-01-16T15:00:00 (6 hours)
Attendees: 8
Meeting: "Full-Day Training"

PREMIUM access allows 8 hours max.
```

**Expected Result:**
- Duration: 6 hours
- Limit: 8 hours (PREMIUM)
- Validation: ✓ PASSES
- Workflow continues to next step

---

## 5. INSUFFICIENT CAPACITY - Too Many Attendees

### Scenario 5.1: Exceeding Room Capacity
```
Book a small room for too many people.

Employee: E001
Room: R006 (C-Suite Presidential Suite)
Start Time: 2026-01-17T14:00:00
End Time: 2026-01-17T16:00:00
Attendees: 8 people
Meeting: "Executive Team Meeting"

Room capacity is only 5 people.
```

**Expected Flow:**
1. ✓ Access verification: PASSES
2. ✓ Availability check: PASSES
3. ✓ Duration validation: PASSES
4. ✗ Capacity validation: FAILS
   - Requested attendees: 8
   - Room capacity: 5
   - Exceeded by: 3 people
   - Error: "Attendee count (8) exceeds room capacity (5)"
5. ✗ Workflow blocked
6. ✗ No confirmation shown
7. ✗ No database record

**Recommendation:**
- Use larger room (R001, R004, etc.)
- Or reduce attendee count to 5 maximum

---

### Scenario 5.2: Capacity at Exact Limit
```
Book a room at exact capacity.

Employee: E002
Room: R006 (C-Suite Presidential Suite)
Start Time: 2026-01-17T14:00:00
End Time: 2026-01-17T16:00:00
Attendees: 5 people (exact capacity)
Meeting: "Executive Discussion"

This should succeed as 5 = 5 (room capacity).
```

**Expected Result:**
- ✓ Capacity validation: PASSES
- Capacity check: 5 attendees ≤ 5 capacity = OK
- Workflow continues
- Confirmation presented
- Booking created after user confirms

---

### Scenario 5.3: Well Below Capacity
```
Small meeting in large room (good practice).

Employee: E003
Room: R004 (Training Center)
Start Time: 2026-01-18T10:00:00
End Time: 2026-01-18T12:00:00
Attendees: 8 people
Meeting: "Department Team Sync"

Room capacity: 30 (plenty of space).
```

**Expected Result:**
- ✓ All validations pass
- Capacity: 8 attendees ≤ 30 capacity ✓
- Room features displayed
- Confirmation requested
- Booking successfully created

---

## 6. HUMAN-IN-THE-LOOP - User Rejection

### Scenario 6.1: User Says NO to Booking
```
Complete a booking request but user rejects confirmation.

Employee: E002
Room: R002 (Board Room)
Start Time: 2026-01-15T14:00:00
End Time: 2026-01-15T16:00:00
Attendees: 8
Meeting: "Product Review"

All validations will pass, but respond NO when asked to confirm.
```

**Expected Flow:**
1. ✓ Access verification: PASSES
2. ✓ Availability check: PASSES (no conflicts)
3. ✓ Duration validation: PASSES (2 hours within PREMIUM limit)
4. ✓ Capacity validation: PASSES (8 ≤ 15)
5. ✓ Room details retrieved
6. **Confirmation Summary Presented:**
   ```
   Room: Board Room
   Capacity: 15
   Features: Video Conference, Speakerphone, 4K Display
   Start Time: 2026-01-15T14:00:00
   End Time: 2026-01-15T16:00:00
   Duration: 2 hours 0 minutes
   Attendees: 8
   Meeting: Product Review
   
   Do you want to confirm this booking? (YES/NO)
   ```
7. **User Response: NO**
8. ✗ Booking cancelled
9. ✗ No database record created
10. Confirmation message: "Booking cancelled by user"

**Database Result:**
- No record in Bookings table
- No changes to database
- User can retry or modify and re-submit

---

### Scenario 6.2: User Changes Mind (Multiple Rejections)
```
User requests multiple bookings but rejects all.

Request 1:
- Employee: E001
- Room: R001
- Time: 09:00-11:00
- Attendees: 5
- Response: NO

Request 2 (after modification):
- Same employee, room
- Time: 13:00-15:00
- Attendees: 5
- Response: NO (again)

Request 3 (finally accepts):
- Same employee, room
- Time: 15:00-17:00
- Attendees: 5
- Response: YES
```

**Expected Behavior:**
- First two requests: Rejected, no DB records
- Third request: Accepted, DB record created
- Only one booking created (for Request 3)
- No duplicate records despite multiple attempts

---

## 7. BACK-TO-BACK CONFLICTS - 15-Minute Buffer

### Scenario 7.1: Attempting to Book Within Buffer
```
Try to book a room during the buffer period after existing booking.

Employee: E001
Room: R001
Start Time: 2026-01-15T03:05:00 (5 minutes after B001 ends)
End Time: 2026-01-15T04:05:00
Attendees: 5
Meeting: "Quick Catch-up"

B001 ends at 03:00, buffer extends to 03:15.
This request starts at 03:05 (within buffer).
```

**Expected Flow:**
1. ✓ Access verification: PASSES
2. ✗ Availability check: FAILS
   - Existing booking B001: 02:00-03:00
   - Required buffer: 15 minutes
   - Buffer period: 02:45-03:15
   - Requested start: 03:05
   - Conflict: Start time within buffer
   - Error: "Room has 1 conflicting booking(s)"
3. ✗ Workflow blocked
4. ✗ No database record

**Solution:**
- Start at 03:15 or later (3:00 + 15 minutes)

---

### Scenario 7.2: Booking Exactly at Buffer Boundary
```
Book exactly at the end of the 15-minute buffer.

Employee: E001
Room: R001
Start Time: 2026-01-15T03:15:00 (exactly at buffer boundary)
End Time: 2026-01-15T04:15:00
Attendees: 5
Meeting: "Post-Meeting Debrief"

B001 ends at 03:00, buffer ends at 03:15.
This request starts at 03:15 (at boundary).
```

**Expected Result:**
- ✓ Availability check: PASSES
- Start time 03:15 = buffer end time = acceptable
- No conflicts detected
- Booking allowed to proceed
- Confirmation and creation

---

### Scenario 7.3: Booking Before Buffer
```
Book before the buffer period starts.

Employee: E001
Room: R001
Start Time: 2026-01-15T01:30:00
End Time: 2026-01-15T02:45:00
Attendees: 5
Meeting: "Pre-Meeting Prep"

This ends at 02:45, before B001 starts at 02:00 + 15-min pre-buffer = 01:45.

Actually: B001 starts at 02:00.
Check if existing booking has pre-buffer protection (system dependent).
```

**Expected Result:**
- Depends on system design
- If buffers are directional: ✓ Should PASS
- If buffers are bidirectional: ✓ Should PASS (ends before existing)

---

## 8. SEQUENTIAL vs PARALLEL EXECUTION DEMONSTRATION

### Scenario 8.1: Sequential Execution Trace
```
Process booking request with SEQUENTIAL execution tracking.

Employee: E001
Room: R002
Time: 2026-01-16T10:00:00 to 2026-01-16T12:00:00
Attendees: 8
Meeting: "Strategic Planning"

Execution trace requested to show sequential blocking.
```

**Expected Output:**
```
Sequential Execution Workflow:
├─ Step 1: Employee Access Verification
│  └─ ✓ PASSED (EXECUTIVE access allows access to STANDARD room)
│     └─ Blocking on: Awaiting verification result before proceeding
│
├─ Step 2: Room Availability Check
│  └─ ✓ PASSED (Room available 10:00-12:00, no conflicts)
│     └─ Blocking on: Awaiting availability check result
│
├─ Step 3: Meeting Duration Calculation
│  └─ ✓ PASSED (2 hours within EXECUTIVE limit of 24 hours)
│     └─ Blocking on: Awaiting duration calculation
│
├─ Step 4: Attendee Capacity Validation
│  └─ ✓ PASSED (8 attendees ≤ 15 room capacity)
│     └─ Blocking on: Awaiting capacity validation
│
├─ Step 5: Room Details Retrieval
│  └─ ✓ PASSED (Details fetched successfully)
│     └─ Features: Video Conference, Speakerphone, 4K Display
│
└─ Step 6: Human Confirmation
   └─ Awaiting user response (YES/NO)
```

**Key Point:** Each step waits for the previous step to complete. If any step fails, workflow terminates.

---

### Scenario 8.2: Parallel Execution Trace
```
Same booking with PARALLEL execution mode.

Employee: E001
Room: R002
Time: 2026-01-16T10:00:00 to 2026-01-16T12:00:00
Attendees: 8
Meeting: "Strategic Planning"

Request PARALLEL execution tracking.
```

**Expected Output:**
```
Parallel Execution Workflow:
├─ [Parallel Phase] Steps 1 & 2 running simultaneously:
│  │
│  ├─ Step 1: Employee Access Verification
│  │  └─ ✓ PASSED (EXECUTIVE)
│  │     Start: 00:00ms | End: 45ms
│  │
│  └─ Step 2: Room Availability Check
│     └─ ✓ PASSED (No conflicts)
│        Start: 00:00ms | End: 120ms
│
├─ [Merge Results] Combining parallel outputs
│  └─ ✓ Both checks successful, proceeding
│
├─ Step 3: Meeting Duration Calculation
│  └─ ✓ PASSED (2 hours)
│
├─ Step 4: Attendee Capacity Validation
│  └─ ✓ PASSED (8 ≤ 15)
│
├─ Step 5: Room Details Retrieval
│  └─ ✓ PASSED
│
└─ Step 6: Human Confirmation
   └─ Awaiting user response

Total Sequential Time: ~620ms
Time with Parallel Execution: ~520ms (saved ~100ms)
```

**Key Point:** Access and availability checks run concurrently, saving overall execution time.

---

## Testing Checklist

Use this checklist to verify all functionality:

### Access Control
- [ ] Executive can book all rooms
- [ ] Premium can access Basic/Standard/Premium rooms
- [ ] Standard can access Basic/Standard rooms
- [ ] Basic can access only Basic rooms
- [ ] Access denial shows clear error message

### Availability
- [ ] Booking prevented during existing booking time
- [ ] Booking prevented within 15-minute buffer (before)
- [ ] Booking prevented within 15-minute buffer (after)
- [ ] Booking allowed exactly at buffer boundary
- [ ] Multiple conflicts listed correctly

### Duration Validation
- [ ] Basic (2h), Standard (4h), Premium (8h), Executive (24h) limits enforced
- [ ] Duration calculation in hours:minutes accurate
- [ ] Exceeding limit shows clear error
- [ ] Within-limit bookings proceed

### Capacity
- [ ] Attendee count below capacity: PASS
- [ ] Attendee count equals capacity: PASS
- [ ] Attendee count above capacity: FAIL with error
- [ ] Large groups directed to appropriate rooms

### Human-in-the-Loop
- [ ] Summary presented before confirmation
- [ ] YES response creates database record
- [ ] NO response cancels without database write
- [ ] Multiple NO responses don't create duplicate records

### Database
- [ ] Booking created with CONFIRMED status
- [ ] BookingID is unique (UUID)
- [ ] Timestamps accurate
- [ ] No duplicate records on re-run
- [ ] Room availability slot marked BOOKED

### Sequential Execution
- [ ] Each step blocks on previous
- [ ] Any failure stops workflow
- [ ] Error step is clearly identified

### Parallel Execution
- [ ] Access and availability run together
- [ ] Results properly merged
- [ ] Subsequent steps wait for parallel phase
- [ ] Execution time is faster than sequential

---

## Running All Tests

```bash
# Execute all test scenarios
python test_all_scenarios.py

# Or run individual scenario groups
python test_happy_path.py
python test_access_control.py
python test_availability.py
python test_duration.py
python test_capacity.py
python test_confirmation.py
python test_sequential_parallel.py
```

---

## Expected Success Metrics

- **Happy Path Success Rate**: 100% (all valid bookings created)
- **Access Control**: 100% (all unauthorized attempts rejected)
- **Availability Detection**: 100% (all conflicts caught)
- **Duration Validation**: 100% (all limit violations caught)
- **Capacity Validation**: 100% (all capacity issues caught)
- **Human Confirmation**: 100% (respects YES/NO decisions)
- **Parallel Speedup**: 15-20% faster than sequential
- **Data Integrity**: 0 duplicate records, 0 orphaned records

---

**Document Version:** v1.0 — 2026