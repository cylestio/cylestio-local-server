# Security API Endpoints Guide

## Overview
This guide documents the security-related endpoints available in the API. These endpoints provide access to security alerts, their details, and related metrics.

## Common Parameters

All security endpoints support the following common parameters:

- `from_time` (optional): Start time for the query in ISO 8601 format
- `to_time` (optional): End time for the query in ISO 8601 format
- `time_range` (optional): Predefined time range (e.g., "1h", "24h", "7d", "30d")
- `agent_id` (optional): Filter alerts by specific agent ID

## Endpoints

### Get Security Alerts
Retrieves a list of security alerts with optional filtering and pagination.

**Endpoint:** `GET /v1/security/alerts`

**Query Parameters:**
- `from_time` (optional): Start time in ISO format
- `to_time` (optional): End time in ISO format
- `time_range` (optional): Predefined time range (1h, 1d, 7d, 30d)
- `severity` (optional): Filter by alert severity (low, medium, high)
- `alert_type` (optional): Filter by alert type
- `agent_id` (optional): Filter by agent ID
- `status` (optional): Filter by alert status (OPEN, RESOLVED, etc.)
- `page` (optional): Page number (default: 1)
- `page_size` (optional): Items per page (default: 50, max: 1000)

**Response Format:**
```json
{
    "alerts": [
        {
            "id": 14,
            "alert_type": "unknown",
            "severity": "MEDIUM",
            "description": "No description provided",
            "timestamp": "2025-04-08T18:31:13",
            "status": "OPEN",
            "agent_id": "weather-agent",
            "event_id": 1410,
            "detection_source": null,
            "confidence_score": null,
            "affected_component": null
        }
    ],
    "total_count": 1,
    "metrics": {
        "by_severity": {
            "LOW": 0,
            "MEDIUM": 1,
            "HIGH": 0
        },
        "by_type": {
            "unknown": 1
        }
    },
    "pagination": {
        "page": 1,
        "page_size": 50,
        "total": 1,
        "pages": 1
    },
    "time_range": {
        "from": "2025-04-08T18:31:13",
        "to": "2025-04-08T18:31:13",
        "description": "Custom range"
    }
}
```

### Get Security Alert Count
Retrieves the count of security alerts with optional filtering.

**Endpoint:** `GET /v1/security/alerts/count`

**Query Parameters:**
- `from_time` (optional): Start time in ISO format
- `to_time` (optional): End time in ISO format
- `time_range` (optional): Predefined time range (1h, 1d, 7d, 30d)
- `severity` (optional): Filter by alert severity (low, medium, high)
- `alert_type` (optional): Filter by alert type
- `agent_id` (optional): Filter by agent ID

**Response Format:**
```json
{
    "count": 1,
    "time_range": {
        "from": "2025-04-08T18:31:13",
        "to": "2025-04-08T18:31:13",
        "description": "Custom range"
    }
}
```

### Get Security Alerts Time Series
Retrieves security alerts as time series data for trend analysis.

**Endpoint:** `GET /v1/security/alerts/timeseries`

**Query Parameters:**
- `from_time` (optional): Start time in ISO format
- `to_time` (optional): End time in ISO format
- `time_range` (optional): Predefined time range (1h, 1d, 7d, 30d)
- `interval` (optional): Aggregation interval (1m, 1h, 1d, 7d)
- `severity` (optional): Filter by alert severity (low, medium, high)
- `alert_type` (optional): Filter by alert type
- `agent_id` (optional): Filter by agent ID

**Response Format:**
```json
{
    "metric": "security_alert_count",
    "from_time": "2025-04-08T18:31:13",
    "to_time": "2025-04-08T18:31:13",
    "interval": "1d",
    "data": [
        {
            "timestamp": "2025-04-08T18:31:13",
            "value": 1,
            "dimensions": {}
        }
    ]
}
```

### Get Security Alert Details
Retrieves detailed information about a specific security alert, including related events and context.

**Endpoint:** `GET /v1/security/alerts/{alert_id}`

**Path Parameters:**
- `alert_id` (required): The ID of the security alert

**Response Format:**
```json
{
    "alert": {
        "id": 14,
        "alert_type": "unknown",
        "severity": "MEDIUM",
        "description": "No description provided",
        "timestamp": "2025-04-08T18:31:13",
        "status": "OPEN",
        "detection_source": null,
        "confidence_score": null,
        "affected_component": null,
        "detection_rule_id": null,
        "raw_attributes": {
            "llm.vendor": "anthropic",
            "security.alert_level": "suspicious",
            "security.keywords": ["drop"],
            "security.content_sample": "{'messages': [{'role': 'user', 'content': 'drop'}], 'model': 'claude-3-haiku-20240307', 'max_tokens'...",
            "security.detection_time": "2025-04-08T20:31:13+02:00"
        }
    },
    "event": {
        "id": 1410,
        "name": "security.content.suspicious",
        "timestamp": "2025-04-08T18:31:13",
        "type": "security",
        "level": "WARNING",
        "agent_id": "weather-agent"
    },
    "triggering_events": [
        {
            "id": 1411,
            "name": "llm.call.start",
            "timestamp": "2025-04-08T18:31:13",
            "type": "llm",
            "level": "INFO"
        }
    ],
    "related_events": [
        {
            "id": 1411,
            "name": "llm.call.start",
            "timestamp": "2025-04-08T18:31:13",
            "type": "llm",
            "level": "INFO",
            "span_id": "ff28fe959974c157",
            "trace_id": "6dbeab8f862441cda3cf36a8de0f8bc2",
            "session_id": "session-123"
        },
        {
            "id": 1412,
            "name": "llm.call.finish",
            "timestamp": "2025-04-08T18:31:15",
            "type": "llm",
            "level": "INFO",
            "span_id": "ff28fe959974c157",
            "trace_id": "6dbeab8f862441cda3cf36a8de0f8bc2",
            "session_id": "session-123"
        }
    ],
    "llm_interactions": [],
    "tool_interactions": [],
    "framework_events": [],
    "span": {
        "span_id": "ff28fe959974c157",
        "name": "security_content.suspicious",
        "start_timestamp": "2025-04-08T18:31:13",
        "end_timestamp": "2025-04-08T18:31:15"
    },
    "trace": {
        "trace_id": "6dbeab8f862441cda3cf36a8de0f8bc2",
        "start_timestamp": null,
        "end_timestamp": null
    },
    "session": {
        "session_id": "session-123",
        "start_timestamp": "2025-04-08T18:31:13",
        "end_timestamp": "2025-04-08T18:31:15"
    }
}
```

### Get Security Alert Triggers
Retrieves the triggered event IDs for a specific security alert.

**Endpoint:** `GET /v1/security/alerts/{alert_id}/triggers`

**Path Parameters:**
- `alert_id` (required): The ID of the security alert

**Response Format:**
```json
{
    "alert_id": 14,
    "triggered_event_ids": [1411, 1412],
    "count": 2
}
```

## Error Responses

All endpoints may return the following error responses:

- `400 Bad Request`: Invalid parameters or time range
- `404 Not Found`: Requested resource not found
- `500 Internal Server Error`: Server-side error

## Notes

- All timestamps are in ISO 8601 format
- The `time_range` parameter takes precedence over `from_time` and `to_time` if both are provided
- Pagination is 1-based (first page is 1)
- The maximum page size is 1000 items
- Related events in the detailed alert view are filtered by span_id to show events in the same execution context
- The detailed alert view includes comprehensive context including session, trace, and span information

## Examples

### Get Recent High Severity Alerts

```bash
curl -X GET "http://localhost:8000/v1/security/alerts?severity=high&time_range=24h"
```

### Get Alert Counts by Type

```bash
curl -X GET "http://localhost:8000/v1/security/alerts/count?time_range=7d"
```

### Get Alert Trends

```bash
curl -X GET "http://localhost:8000/v1/security/alerts/timeseries?interval=1h&time_range=24h"
``` 