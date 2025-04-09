# Security API Endpoints Guide

This guide provides detailed documentation for the Security API endpoints in the Cylestio API.

## Common Parameters

All security endpoints support the following common parameters:

- `from_time` (optional): Start time for the query in ISO 8601 format
- `to_time` (optional): End time for the query in ISO 8601 format
- `time_range` (optional): Predefined time range (e.g., "1h", "24h", "7d", "30d")
- `agent_id` (optional): Filter alerts by specific agent ID

## Endpoints

### Get Security Alerts

```
GET /v1/security/alerts
```

Retrieves security alerts with filtering options.

#### Query Parameters

- All common parameters
- `severity` (optional): Filter by alert severity (e.g., "high", "medium", "low")
- `type` (optional): Filter by alert type
- `limit` (optional): Maximum number of alerts to return (default: 100)
- `offset` (optional): Number of alerts to skip (default: 0)

#### Response Format

```json
{
  "alerts": [
    {
      "id": "string",
      "timestamp": "string",
      "severity": "string",
      "type": "string",
      "agent_id": "string",
      "description": "string",
      "details": {}
    }
  ],
  "total": 0,
  "time_range": {
    "from": "string",
    "to": "string"
  }
}
```

### Get Security Alerts Count

```
GET /v1/security/alerts/count
```

Retrieves aggregated security alert counts.

#### Response Format

```json
{
  "total": 0,
  "by_severity": {
    "high": 0,
    "medium": 0,
    "low": 0
  },
  "by_type": {
    "type1": 0,
    "type2": 0
  },
  "time_range": {
    "from": "string",
    "to": "string"
  }
}
```

### Get Security Alerts Time Series

```
GET /v1/security/alerts/timeseries
```

Retrieves security alert counts over time.

#### Query Parameters

- All common parameters
- `interval` (optional): Time interval for aggregation (e.g., "1h", "1d")

#### Response Format

```json
{
  "data": [
    {
      "timestamp": "string",
      "count": 0,
      "by_severity": {
        "high": 0,
        "medium": 0,
        "low": 0
      }
    }
  ],
  "time_range": {
    "from": "string",
    "to": "string"
  }
}
```

## Error Handling

All endpoints may return the following error responses:

- `400 Bad Request`: Invalid parameters or time range
- `500 Internal Server Error`: Server-side error

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