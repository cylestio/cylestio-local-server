# Cylestio API Documentation

## Introduction

The Cylestio Local Server provides a comprehensive API for collecting, analyzing, and retrieving telemetry data from AI agents. This document provides a high-level overview of the API endpoints, while detailed documentation for each endpoint category is available in separate guides.

## API Versioning

All endpoints are prefixed with `/v1/` to indicate API version 1. Future API versions will use different prefixes (e.g., `/v2/`).

## Authentication

For local development, authentication is not required. In production environments, API keys or other authentication methods should be implemented.

## API Categories

The API is organized into the following categories:

### Telemetry API

Endpoints for submitting and retrieving raw telemetry events:

- `POST /v1/telemetry` - Submit a single telemetry event
- `POST /v1/telemetry/batch` - Submit multiple telemetry events
- `GET /v1/telemetry/events` - Retrieve events with filtering options
- `GET /v1/telemetry/events/{event_id}` - Get a specific event by ID
- `GET /v1/telemetry/traces/{trace_id}` - Get all events in a trace

See [Telemetry Endpoints Guide](./telemetry-endpoints-guide.md) for detailed documentation.

### Metrics API

Endpoints for retrieving aggregated metrics and analytics:

- `GET /v1/dashboard` - Get main dashboard metrics
- `GET /v1/metrics/llm/request_count` - Get LLM request count metrics
- `GET /v1/metrics/llm/token_usage` - Get LLM token usage metrics
- `GET /v1/metrics/llm/response_time` - Get LLM response time metrics
- `GET /v1/metrics/tool/execution_count` - Get tool execution count metrics
- `GET /v1/metrics/tool/success_rate` - Get tool success rate metrics
- `GET /v1/metrics/error/count` - Get error count metrics
- `GET /v1/metrics/session/count` - Get session count metrics
- And more...

See [Metrics Endpoints Guide](./metrics-endpoints-guide.md) for detailed documentation.

### Agent API

Endpoints for retrieving agent-specific information:

- `GET /v1/agents` - List all agents
- `GET /v1/agents/{agent_id}` - Get agent details
- `GET /v1/agents/{agent_id}/dashboard` - Get agent dashboard data
- `GET /v1/agents/{agent_id}/llms` - Get LLM usage for an agent
- `GET /v1/agents/{agent_id}/tools` - Get tool usage for an agent
- `GET /v1/agents/{agent_id}/sessions` - Get sessions for an agent
- `GET /v1/agents/{agent_id}/traces` - Get traces for an agent
- `GET /v1/agents/{agent_id}/alerts` - Get security alerts for an agent

See [Agent Endpoints Guide](./agent-endpoints-guide.md) for detailed documentation.

### Health API

Endpoints for checking API health:

- `GET /v1/health` - Check API health

## Common Parameters

Many endpoints support the following common parameters:

### Time Range Parameters

- `from_time`: Start time in ISO format (e.g., "2023-01-01T00:00:00Z")
- `to_time`: End time in ISO format
- `time_range`: Predefined time range (options: "1h", "1d", "7d", "30d")

### Pagination Parameters

- `page`: Page number (default: 1)
- `page_size`: Number of items per page (default varies by endpoint, typically 50)

### Filtering Parameters

- `agent_id`: Filter by specific agent
- Many endpoints have additional specific filtering parameters

## Response Formats

All API endpoints return responses in JSON format. The general structure for success responses varies by endpoint, but typically includes:

- The requested data
- Metadata about the request (e.g., pagination info)
- Status indicators

Error responses follow this structure:

```json
{
  "detail": {
    "success": false,
    "error": "Error message"
  }
}
```

## Status Codes

The API uses standard HTTP status codes:

- `200 OK` - The request was successful
- `201 Created` - A new resource was created successfully
- `400 Bad Request` - The request was invalid or malformed
- `404 Not Found` - The requested resource was not found
- `422 Unprocessable Entity` - Validation error
- `500 Internal Server Error` - An unexpected error occurred on the server

## Rate Limiting

The API implements rate limiting to prevent abuse. The default limit is 100 requests per minute per client, but this can be configured in the server settings.

## Further Documentation

For more detailed information about specific endpoints, please refer to the following guides:

- [Telemetry Endpoints Guide](./telemetry-endpoints-guide.md)
- [Metrics Endpoints Guide](./metrics-endpoints-guide.md)
- [Agent Endpoints Guide](./agent-endpoints-guide.md)
- [OpenAPI Documentation](http://localhost:8000/docs) (when server is running) 