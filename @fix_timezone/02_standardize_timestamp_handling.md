# Task: Standardize Timestamp Handling

## Background
Our monitor client now sends all telemetry in UTC timezone (with "Z" suffix). The server currently handles this inconsistently, with various approaches to parsing and formatting timestamps. We need to standardize how we handle timestamps throughout the codebase.

## Task Description
Create a consistent approach for handling ISO format timestamps with 'Z' suffix (UTC) and ensure all timestamps in the system are properly handled.

## Implementation Steps

1. Review the current timestamp handling code:
   - Look for patterns like `timestamp.replace('Z', '+00:00')`
   - Check how timestamps are serialized to JSON

2. Create a standardized utility module for timestamp handling:
   ```python
   # src/utils/time_utils.py
   from datetime import datetime
   
   def parse_iso_timestamp(timestamp_str):
       """
       Parse an ISO format timestamp string, handling UTC 'Z' suffix correctly.
       
       Args:
           timestamp_str (str): ISO format timestamp string
           
       Returns:
           datetime: Parsed datetime object (timezone-naive, but in UTC)
       """
       if not timestamp_str:
           return None
       
       # Handle 'Z' suffix for UTC time
       if isinstance(timestamp_str, str) and timestamp_str.endswith('Z'):
           timestamp_str = timestamp_str.replace('Z', '+00:00')
       
       return datetime.fromisoformat(timestamp_str).replace(tzinfo=None)
   
   def format_iso_timestamp(dt):
       """
       Format a datetime object as ISO format string with 'Z' suffix for UTC.
       
       Args:
           dt (datetime): Datetime object to format
           
       Returns:
           str: ISO format timestamp string with 'Z' suffix
       """
       if not dt:
           return None
       
       # Ensure the datetime is timezone-naive
       if dt.tzinfo:
           dt = dt.replace(tzinfo=None)
       
       return dt.isoformat() + 'Z'
   ```

3. Replace existing timestamp parsing/formatting code to use the new utilities:
   - Find all instances of `.replace('Z', '+00:00')` and replace with `parse_iso_timestamp()`
   - Update JSON serialization to use the new utilities

## Key Files to Check
- `src/models/event.py`
- `src/models/security_alert.py`
- `src/models/llm_interaction.py`
- `src/analysis/utils.py`
- `src/api/schemas/telemetry.py`
- `src/processing/simple_processor.py`
- `src/utils/json_serializer.py`

## Testing
- Verify that timestamps are correctly parsed from telemetry events
- Ensure timestamps in API responses have 'Z' suffix
- Check that time-based queries still work correctly

## Acceptance Criteria
- New utility functions for standardized timestamp handling are implemented
- All timestamp parsing and formatting uses the standardized approach
- API responses consistently use ISO format with 'Z' suffix
- Existing functionalities that rely on timestamp parsing continue to work correctly 