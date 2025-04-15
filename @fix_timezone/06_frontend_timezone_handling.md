# Frontend Task: Implement Consistent UTC to Local Time Conversion

## Background
Our backend system now consistently uses UTC timezone for all timestamps (with 'Z' suffix). The frontend needs to properly handle these UTC timestamps by converting them to the user's local timezone for display, while still sending UTC timestamps in requests.

## Task Description
Implement consistent timezone handling in the frontend to:
1. Convert UTC timestamps from API responses to local time for display
2. Convert local time to UTC when sending timestamps in API requests
3. Clearly indicate timezone to users when displaying timestamps

## Implementation Guide

### 1. Add a Date/Time Utility Library
Choose a date/time utility library that handles timezone conversion well. We recommend:
- [Day.js](https://day.js.org/) with the UTC and timezone plugins
- [date-fns](https://date-fns.org/) with the timezone functions

Example with Day.js:
```javascript
import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';
import timezone from 'dayjs/plugin/timezone';

// Extend dayjs with plugins
dayjs.extend(utc);
dayjs.extend(timezone);

// Add to package.json:
// "dayjs": "^1.11.7"
```

### 2. Create Utility Functions for Time Conversion

```javascript
// src/utils/timeUtils.js

/**
 * Converts a UTC ISO timestamp to local time for display
 * 
 * @param {string} utcTimestamp - ISO timestamp with Z suffix
 * @param {string} format - Display format (optional)
 * @returns {string} Formatted local time
 */
export function utcToLocalDisplay(utcTimestamp, format = 'YYYY-MM-DD HH:mm:ss') {
  if (!utcTimestamp) return '';
  return dayjs(utcTimestamp).local().format(format);
}

/**
 * Converts a local datetime to UTC ISO timestamp for API requests
 * 
 * @param {Date|string} localDateTime - Local date/time
 * @returns {string} ISO timestamp with Z suffix
 */
export function localToUtc(localDateTime) {
  if (!localDateTime) return null;
  return dayjs(localDateTime).utc().format('YYYY-MM-DDTHH:mm:ss') + 'Z';
}

/**
 * Formats a timestamp with timezone indication
 * 
 * @param {string} utcTimestamp - ISO timestamp with Z suffix
 * @returns {string} Formatted time with timezone
 */
export function formatWithTimezone(utcTimestamp) {
  if (!utcTimestamp) return '';
  const local = dayjs(utcTimestamp).local();
  return `${local.format('YYYY-MM-DD HH:mm:ss')} (${local.format('Z')})`;
}
```

### 3. Update Components that Display Timestamps

Find all components that display timestamps and update them to use the conversion utilities:

```jsx
import { utcToLocalDisplay, formatWithTimezone } from '../utils/timeUtils';

function EventItem({ event }) {
  return (
    <div className="event-item">
      <div className="event-title">{event.title}</div>
      <div className="event-time">
        {utcToLocalDisplay(event.timestamp, 'MMMM D, YYYY h:mm A')}
      </div>
      <div className="event-details">
        Occurred at: {formatWithTimezone(event.timestamp)}
      </div>
    </div>
  );
}
```

### 4. Update Form Components that Send Timestamps

For date pickers and forms that send timestamp data to the API:

```jsx
import { useState } from 'react';
import { localToUtc } from '../utils/timeUtils';

function EventFilterForm({ onSubmit }) {
  const [startDate, setStartDate] = useState(new Date());
  const [endDate, setEndDate] = useState(new Date());
  
  const handleSubmit = (e) => {
    e.preventDefault();
    
    // Convert local dates to UTC for API request
    onSubmit({
      from_time: localToUtc(startDate),
      to_time: localToUtc(endDate)
    });
  };
  
  return (
    <form onSubmit={handleSubmit}>
      <label>
        Start Date:
        <input 
          type="datetime-local" 
          onChange={(e) => setStartDate(e.target.value)}
        />
      </label>
      <label>
        End Date:
        <input 
          type="datetime-local" 
          onChange={(e) => setEndDate(e.target.value)}
        />
      </label>
      <button type="submit">Filter</button>
    </form>
  );
}
```

### 5. Update Data Fetching Logic

For API calls that require or receive timestamps:

```javascript
import { localToUtc } from '../utils/timeUtils';

async function fetchEvents(startDate, endDate) {
  // Convert to UTC for API request
  const params = new URLSearchParams({
    from_time: localToUtc(startDate),
    to_time: localToUtc(endDate)
  });
  
  const response = await fetch(`/api/events?${params}`);
  return response.json();
}
```

### 6. Add Timezone Indicator in the UI (Optional)

Consider adding a small indicator showing the user's current timezone:

```jsx
function TimezoneIndicator() {
  const [timezone, setTimezone] = useState('');
  
  useEffect(() => {
    setTimezone(dayjs.tz.guess());
  }, []);
  
  return (
    <div className="timezone-indicator">
      <small>Times displayed in {timezone}</small>
    </div>
  );
}
```

## Key Components to Update
- Date/time displays in all listings and detail views
- Date pickers and filter forms
- Charts and visualizations with time axes
- Data fetching logic that involves timestamps

## Testing
- Test with browsers set to different timezones
- Verify timestamps display correctly in the user's local time
- Ensure API requests contain properly formatted UTC timestamps
- Test date range filters to confirm they work as expected

## Acceptance Criteria
- All displayed timestamps are converted from UTC to local time
- All timestamps sent to the API are in UTC format with 'Z' suffix
- Date/time pickers and filters work correctly with timezone conversion
- Users can understand what timezone is being used for display 