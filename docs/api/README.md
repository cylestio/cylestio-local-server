# API Reference

This document provides detailed information about all available API endpoints in the Cylestio Local Server.

## Base URL

All API endpoints are prefixed with `/v1/`.

## Authentication

For local development, authentication is not required. In production environments, API keys or other authentication methods should be implemented.

## API Endpoints

### Telemetry API

- [Submit Event](./telemetry-submit.md) - `POST /v1/telemetry`
- [Submit Batch](./telemetry-batch.md) - `POST /v1/telemetry/batch`
- [Retrieve Events](./telemetry-events.md) - `GET /v1/telemetry/events`
- [Get Event by ID](./telemetry-event-id.md) - `GET /v1/telemetry/events/{event_id}`
- [Get Events by Trace](./telemetry-trace.md) - `GET /v1/telemetry/traces/{trace_id}`

### Metrics API

- [Dashboard Metrics](./metrics-dashboard.md) - `GET /v1/metrics/dashboard`
- [Specific Metric](./metrics-specific.md) - `GET /v1/metrics`
- [Agent Metrics](./metrics-agents.md) - `GET /v1/metrics/agents`

### Health API

- [Health Check](./health.md) - `GET /v1/health`

## Response Formats

All API endpoints return responses in JSON format. The general structure for error responses is:

```json
{
  "error": "Error message",
  "detail": {
    "additional": "information"
  }
}
```

Successful responses vary by endpoint and are documented in the individual endpoint documentation.

## Status Codes

The API uses the following HTTP status codes:

- `200 OK` - The request was successful
- `201 Created` - A new resource was created successfully
- `400 Bad Request` - The request was invalid or malformed
- `401 Unauthorized` - Authentication is required or failed
- `404 Not Found` - The requested resource was not found
- `422 Unprocessable Entity` - Validation error
- `500 Internal Server Error` - An unexpected error occurred on the server

## Rate Limiting

By default, the API is limited to 100 requests per minute per client. This can be configured in the server settings. 