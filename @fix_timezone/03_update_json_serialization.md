# Task: Update JSON Serialization for UTC Timestamps

## Background
Our system now uses UTC timestamps with 'Z' suffix for all telemetry data. Currently, our JSON serialization for API responses doesn't consistently format timestamps in this way. We need to update the JSON serialization to ensure consistent UTC timestamp formatting in all API responses.

## Task Description
Update the JSON serialization code to ensure all datetime objects are serialized as ISO format strings with 'Z' suffix (indicating UTC) in API responses.

## Implementation Steps

1. Locate the current JSON serialization code:
   - `src/utils/json_serializer.py` contains the custom JSON encoder

2. Update the JSON encoder to use the new timestamp utility:
   ```python
   # src/utils/json_serializer.py
   import json
   from datetime import datetime, date
   from src.utils.time_utils import format_iso_timestamp
   
   class CustomJSONEncoder(json.JSONEncoder):
       """
       Custom JSON encoder that handles datetime and date objects by converting them
       to ISO format strings with 'Z' suffix.
       """
       def default(self, obj):
           if isinstance(obj, datetime):
               # Use the standardized utility function to format with 'Z' suffix
               return format_iso_timestamp(obj)
           elif isinstance(obj, date):
               # For date objects (without time), use ISO format without 'Z'
               return obj.isoformat()
           # Let the base class handle other types or raise TypeError
           return super().default(obj)
   ```

3. Ensure all API routes use this encoder for responses:
   - Check FastAPI configuration for default JSON encoder
   - Review any custom response formatting in API routes

4. Update any direct JSON serialization in code:
   - Find places where `datetime.isoformat()` is called directly
   - Replace with calls to `format_iso_timestamp` from the new utility module

## Key Files to Check
- `src/utils/json_serializer.py`
- `src/api/main.py` (FastAPI app configuration)
- `src/api/routes/` (all route files)

## Testing
- Test API responses to ensure timestamps have 'Z' suffix
- Verify that date-only fields are serialized correctly
- Check that the frontend can correctly parse and display the timestamps

## Acceptance Criteria
- JSON serialization consistently adds 'Z' suffix to all datetime values in API responses
- All API endpoints return ISO format timestamps with 'Z' suffix
- Date-only fields (without time component) are serialized correctly
- No regressions in functionality related to timestamp serialization 