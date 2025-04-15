# Task: Remove Madrid Time Adjustments

## Background
Our monitor client now sends all telemetry in UTC timezone (with "Z" suffix). Currently, the server has hardcoded timezone adjustments for Madrid time (UTC+2) in various places. We need to remove these adjustments to properly support UTC throughout the system.

## Task Description
Remove all instances of hardcoded +2 hour time adjustments (Madrid time) in the codebase. These are typically found in patterns like:
- `datetime.utcnow() + timedelta(hours=2)`
- Comments mentioning "Add 2 hours offset to match Madrid time (UTC+2)"

## Implementation Steps
1. Identify all files containing Madrid time adjustments
   - Look for `timedelta(hours=2)` patterns
   - Check utility functions, API routes, and analysis modules
   
2. Replace each occurrence by removing the time adjustment:
   - Change `datetime.utcnow() + timedelta(hours=2)` to `datetime.utcnow()`
   - Remove related comments about Madrid time
   
3. Update any code that depends on these adjusted timestamps

## Key Files to Check
- `src/analysis/utils.py`
- `src/analysis/interface.py`
- `src/analysis/security_analysis.py`
- `src/api/routes/security.py`
- `src/api/routes/agents.py`
- `src/api/routes/metrics.py`

## Testing
- Verify that timestamps in responses are now in UTC without the +2 hours adjustment
- Check that time range calculations work correctly with the UTC times
- Ensure that no frontend-facing data is affected in a way that would break existing functionality

## Acceptance Criteria
- All hardcoded +2 hour adjustments have been removed from the codebase
- Server code consistently uses UTC time for all operations
- No regressions in functionality related to time-based queries 