# Cylestio API Endpoint Structure Design

## 1. Overview

This document defines the API endpoint structure and organization for the Cylestio monitoring dashboard. The structure establishes consistent patterns for all API endpoints, including URL formatting, parameter naming, response formats, and versioning.

## 2. Base URL Structure

All API endpoints will use the following base URL pattern:

```
/api/v1/{resource_group}/{resource_name}
```

Where:
- `/api/v1` - API version prefix
- `{resource_group}` - Primary category of resources (agents, metrics, etc.)
- `{resource_name}` - Specific resource or operation

## 3. Core API Endpoint Groups

### 3.1 Agent Data (`/api/v1/agents`)

Endpoints for agent-specific data and operations:

- `GET /api/v1/agents` - List all agents
- `GET /api/v1/agents/{agent_id}` - Get agent details
- `GET /api/v1/agents/{agent_id}/metrics` - Get all metrics for an agent
- `GET /api/v1/agents/{agent_id}/sessions` - Get sessions for an agent
- `GET /api/v1/agents/{agent_id}/events` - Get events for an agent
- `GET /api/v1/agents/{agent_id}/tools` - Get tool usage for an agent
- `GET /api/v1/agents/{agent_id}/llms` - Get LLM usage for an agent
- `GET /api/v1/agents/{agent_id}/alerts` - Get alerts for an agent
- `GET /api/v1/agents/{agent_id}/dashboard` - Get dashboard data for an agent

### 3.2 Metrics Data (`/api/v1/metrics`)

Endpoints for aggregated metrics across the system:

- `GET /api/v1/metrics/llm/request_count` - Get LLM request count metrics
- `GET /api/v1/metrics/llm/token_usage` - Get LLM token usage metrics
- `GET /api/v1/metrics/llm/response_time` - Get LLM response time metrics
- `GET /api/v1/metrics/tool/execution_count` - Get tool execution count metrics
- `GET /api/v1/metrics/tool/success_rate` - Get tool success rate metrics
- `GET /api/v1/metrics/error/count` - Get error count metrics
- `GET /api/v1/metrics/session/count` - Get session count metrics
- `GET /api/v1/metrics/dashboard` - Get aggregated dashboard metrics

### 3.3 Alerts (`/api/v1/alerts`)

Endpoints for security alerts and suspicious activities:

- `GET /api/v1/alerts` - List all alerts
- `GET /api/v1/alerts/{alert_id}` - Get alert details
- `GET /api/v1/alerts/count` - Get alert count metrics
- `PUT /api/v1/alerts/{alert_id}/status` - Update alert status

### 3.4 Tools (`/api/v1/tools`)

Endpoints for tool usage analytics:

- `GET /api/v1/tools` - List all tools
- `GET /api/v1/tools/{tool_name}` - Get tool details
- `GET /api/v1/tools/{tool_name}/metrics` - Get metrics for a specific tool
- `GET /api/v1/tools/{tool_name}/usage` - Get usage patterns for a tool

### 3.5 LLMs (`/api/v1/llms`)

Endpoints for LLM interaction data and token usage:

- `GET /api/v1/llms` - List all LLM models used
- `GET /api/v1/llms/{model_name}` - Get model details
- `GET /api/v1/llms/{model_name}/metrics` - Get metrics for a specific model
- `GET /api/v1/llms/{model_name}/token_usage` - Get token usage for a model

### 3.6 Events (`/api/v1/events`)

Endpoints for raw telemetry event access:

- `GET /api/v1/events` - List events with filtering
- `GET /api/v1/events/{event_id}` - Get event details
- `GET /api/v1/events/traces/{trace_id}` - Get all events in a trace

### 3.7 Sessions (`/api/v1/sessions`)

Endpoints for session information and analytics:

- `GET /api/v1/sessions` - List all sessions
- `GET /api/v1/sessions/{session_id}` - Get session details
- `GET /api/v1/sessions/{session_id}/events` - Get events for a session
- `GET /api/v1/sessions/{session_id}/metrics` - Get metrics for a session

### 3.8 Telemetry Ingestion (`/api/v1/telemetry`)

Endpoints for ingesting telemetry data:

- `POST /api/v1/telemetry` - Submit a single telemetry event
- `POST /api/v1/telemetry/batch` - Submit multiple telemetry events

## 4. URL Structure Patterns

### 4.1 Collection Resources

Collections use plural nouns and return lists of resources:
```
GET /api/v1/agents
GET /api/v1/events
GET /api/v1/sessions
```

### 4.2 Individual Resources

Individual resources are accessed via IDs with the pattern:
```
GET /api/v1/agents/{agent_id}
GET /api/v1/events/{event_id}
GET /api/v1/sessions/{session_id}
```

### 4.3 Nested Resources

Nested resources follow a hierarchical pattern:
```
GET /api/v1/agents/{agent_id}/sessions
GET /api/v1/sessions/{session_id}/events
```

### 4.4 Actions

Actions on resources use verbs or descriptive nouns:
```
GET /api/v1/agents/{agent_id}/dashboard
PUT /api/v1/alerts/{alert_id}/status
```

## 5. Query Parameter Standards

### 5.1 Time Filtering

All time-based endpoints use these parameters:
- `from_time`: ISO 8601 timestamp for start time
- `to_time`: ISO 8601 timestamp for end time
- `time_range`: Shorthand time range (accepted values: "1h", "1d", "7d", "30d")

Example:
```
GET /api/v1/metrics/llm/request_count?time_range=7d
GET /api/v1/metrics/llm/request_count?from_time=2023-01-01T00:00:00Z&to_time=2023-01-31T23:59:59Z
```

### 5.2 Pagination

All list endpoints use these parameters:
- `page`: Page number (1-indexed, default: 1)
- `page_size`: Number of items per page (default: 50, max: 1000)

Example:
```
GET /api/v1/events?page=2&page_size=100
```

### 5.3 Sorting

All list endpoints use these parameters:
- `sort_by`: Field to sort by
- `sort_dir`: Sort direction (accepted values: "asc", "desc", default: "desc")

Example:
```
GET /api/v1/events?sort_by=timestamp&sort_dir=asc
```

### 5.4 Filtering

Common filters across endpoints:
- `agent_id`: Filter by agent ID
- `level`: Filter by log level
- `event_name`: Filter by event name
- `trace_id`: Filter by trace ID

Example:
```
GET /api/v1/events?agent_id=weather-agent&level=ERROR
```

### 5.5 Aggregation

Time-series data endpoints use:
- `interval`: Time-based grouping (accepted values: "1m", "1h", "1d", "7d")
- `dimensions`: Comma-separated list of dimensions to group by

Example:
```
GET /api/v1/metrics/llm/token_usage?interval=1d&dimensions=model,vendor
```

## 6. Response Format Standards

### 6.1 List Response Format

```json
{
  "items": [
    { ... resource object ... },
    { ... resource object ... }
  ],
  "pagination": {
    "page": 1,
    "page_size": 50,
    "total": 125,
    "total_pages": 3,
    "has_next": true,
    "has_prev": false
  },
  "meta": {
    "timestamp": "2023-01-01T12:00:00Z"
  }
}
```

### 6.2 Individual Resource Response Format

```json
{
  "data": {
    ... resource properties ...
  },
  "meta": {
    "timestamp": "2023-01-01T12:00:00Z"
  }
}
```

### 6.3 Time Series Data Response Format

```json
{
  "metric": "llm_token_usage",
  "from_time": "2023-01-01T00:00:00Z",
  "to_time": "2023-01-07T23:59:59Z",
  "interval": "1d",
  "data": [
    {
      "timestamp": "2023-01-01T00:00:00Z",
      "value": 12345,
      "dimensions": {
        "model": "gpt-4",
        "agent_id": "weather-agent"
      }
    },
    ...
  ],
  "meta": {
    "timestamp": "2023-01-08T12:00:00Z"
  }
}
```

### 6.4 Error Response Format

```json
{
  "success": false,
  "error": {
    "code": "validation_error",
    "message": "Invalid time range parameter",
    "details": [
      {
        "field": "time_range",
        "error": "Must be one of: 1h, 1d, 7d, 30d"
      }
    ]
  },
  "meta": {
    "timestamp": "2023-01-01T12:00:00Z"
  }
}
```

## 7. Versioning Strategy

### 7.1 URL-Based Versioning

- All endpoints include the version in the URL path: `/api/v1/...`
- Major version changes will increment the version number: `/api/v2/...`

### 7.2 Version Lifecycle

- Each API version will be supported for a minimum of 12 months after a new version is released
- Deprecation notices will be provided at least 6 months before end-of-life
- Multiple versions may be active simultaneously during transition periods

### 7.3 Backward Compatibility

- New fields may be added to existing resources without version changes
- Existing fields will not be removed or have their meaning changed within a version
- New optional parameters may be added to existing endpoints

## 8. HTTP Method Mapping

### 8.1 GET

Used for all read-only operations:
- Retrieving resources or collections
- Querying metrics and analytics
- Filtering data

### 8.2 POST

Used for creating new resources:
- Submitting telemetry events
- Creating new configuration items (future)

### 8.3 PUT

Used for full resource updates:
- Updating configuration settings (future)
- Replacing resources with new versions

### 8.4 PATCH

Used for partial resource updates:
- Updating specific fields of a resource
- Modifying configuration parameters

### 8.5 DELETE

Used for resource removal:
- Deleting configuration items (future)
- Removing user-defined settings (future)

## 9. Content Types

- All request and response bodies use JSON: `Content-Type: application/json`
- Files and binary data use appropriate MIME types

## 10. Authentication and Authorization

Authentication and authorization mechanisms will be defined in a separate security document, but all endpoints will follow these principles:

- All API endpoints will require authentication (future)
- Authorization will be based on role-based access control (future)
- API keys or OAuth 2.0 will be the primary authentication methods (future) 