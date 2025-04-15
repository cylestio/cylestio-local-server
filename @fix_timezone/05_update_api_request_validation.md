# Task: Update API Request Validation for UTC Timestamps

## Background
Our system now consistently uses UTC for all timestamps. We need to ensure that incoming API requests with timestamps are properly validated and parsed to maintain this consistency.

## Task Description
Update API request validation to ensure all incoming timestamp parameters are properly validated as UTC format (with 'Z' suffix) and correctly converted to datetime objects.

## Implementation Steps

1. Identify all API endpoints that accept timestamp parameters:
   - Look for parameters of type `datetime` in FastAPI route definitions
   - Check for any custom validation for timestamp fields in request models

2. Update Pydantic models for request validation:
   - Use a validator to ensure timestamps are in UTC format
   - Utilize the new timestamp parsing utility

3. Example implementation:
   ```python
   # src/api/schemas/common.py
   from datetime import datetime
   from pydantic import BaseModel, validator
   from src.utils.time_utils import parse_iso_timestamp
   
   class TimeRangeRequest(BaseModel):
       from_time: Optional[datetime] = None
       to_time: Optional[datetime] = None
       
       @validator('from_time', 'to_time', pre=True)
       def validate_timestamps(cls, value):
           """Validate that timestamps are in ISO format with UTC ('Z') timezone."""
           if isinstance(value, str):
               # Check if it ends with Z (UTC)
               if not value.endswith('Z'):
                   raise ValueError("Timestamp must be in UTC format with 'Z' suffix")
               return parse_iso_timestamp(value)
           return value
   ```

4. Use the updated models in API routes:
   ```python
   from src.api.schemas.common import TimeRangeRequest
   
   @router.post("/events/query")
   async def query_events(time_range: TimeRangeRequest):
       # Access validated timestamps
       from_time = time_range.from_time
       to_time = time_range.to_time
       # ... implementation ...
   ```

5. For direct Query parameters, add validation:
   ```python
   from fastapi import Query
   from src.utils.time_utils import parse_iso_timestamp
   
   def validate_timestamp(value: str):
       if value and not value.endswith('Z'):
           raise ValueError("Timestamp must be in UTC format with 'Z' suffix")
       return parse_iso_timestamp(value)
   
   @router.get("/events")
   async def get_events(
       from_time: Optional[str] = Query(
           None, 
           description="Start time in UTC (ISO format with 'Z' suffix)"
       ),
       to_time: Optional[str] = Query(
           None, 
           description="End time in UTC (ISO format with 'Z' suffix)"
       )
   ):
       # Validate and parse timestamps
       from_time_dt = validate_timestamp(from_time) if from_time else None
       to_time_dt = validate_timestamp(to_time) if to_time else None
       # ... implementation ...
   ```

## Key Files to Check
- `src/api/schemas/` (all request schema files)
- `src/api/routes/` (all route files with timestamp parameters)

## Testing
- Test API endpoints with various timestamp formats:
  - Valid UTC timestamps (with 'Z' suffix)
  - Invalid timestamps (without 'Z' suffix)
  - Non-UTC timestamps with explicit offsets
- Verify that only valid UTC timestamps are accepted

## Acceptance Criteria
- All API endpoints that accept timestamp parameters validate them correctly
- Only UTC timestamps with 'Z' suffix are accepted
- Invalid timestamps result in appropriate error responses
- API documentation clearly indicates the required UTC format 