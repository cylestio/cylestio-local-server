# Task: Update API Documentation for UTC Timezone Standardization

## Background
Our system now consistently uses UTC for all timestamps. We need to update our API documentation to clearly state this and provide guidance on how clients should handle timestamps.

## Task Description
Update all API documentation to clearly specify that:
1. All timestamps in API requests and responses use UTC timezone (with 'Z' suffix)
2. Clients are responsible for converting UTC to local time for display purposes

## Implementation Steps

1. Identify all API documentation files:
   - API schema definitions
   - OpenAPI documentation
   - Markdown documentation
   - Code comments in API route files

2. Update FastAPI route documentation:
   - Add clear notes in the docstrings about timezone requirements
   - Make sure all timestamp parameter descriptions mention UTC

3. Update any written documentation:
   - Emphasize that all timestamps are in UTC
   - Provide guidance on timezone handling for clients

4. Add a general note about timezone handling to the API overview documentation

## Key Files to Check
- `src/api/routes/*.py` (all route files)
- `tasks/events_endpoints/ui_context/*.md` (API documentation for UI developers)
- Any OpenAPI documentation files or schema definitions

## Examples of Documentation Updates

### In API Route Docstrings
```python
@router.get("/events")
async def get_events(
    from_time: Optional[datetime] = Query(
        None, 
        description="Start time in UTC (ISO format with 'Z' suffix)"
    ),
    to_time: Optional[datetime] = Query(
        None, 
        description="End time in UTC (ISO format with 'Z' suffix)"
    )
):
    """
    Get events within a time range.
    
    All timestamps in requests and responses use UTC timezone (indicated by 'Z' suffix).
    Clients are responsible for converting to local time for display purposes.
    """
    # ... implementation ...
```

### In Markdown Documentation
```markdown
## Timezone Handling

- All timestamps in API requests and responses use UTC timezone (indicated by 'Z' suffix in ISO format strings)
- Example: `"2023-04-15T10:30:00Z"` represents 10:30 AM UTC time
- Clients should convert UTC timestamps to local time for display purposes
- When sending timestamps to the API, clients should convert local time to UTC
```

## Testing
- Review updated documentation for clarity and correctness
- Verify that the documentation accurately reflects the actual API behavior

## Acceptance Criteria
- All API documentation clearly states that timestamps use UTC timezone
- Parameter descriptions for timestamp fields specify UTC format
- Documentation provides guidance on how clients should handle timezone conversion
- API documentation is consistent with the actual implementation 