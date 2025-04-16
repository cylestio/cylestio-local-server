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
- `GET /v1/metrics/llm/analytics` - Get comprehensive LLM usage analytics with flexible breakdowns
- `GET /v1/metrics/llm/models` - Get LLM model performance comparison
- `GET /v1/metrics/llm/usage_trends` - Get LLM usage trends over time
- `GET /v1/metrics/llm/agent_usage` - Get LLM usage by agent
- `GET /v1/metrics/tool/execution_count` - Get tool execution count metrics
- `GET /v1/metrics/tool/success_rate` - Get tool success rate metrics
- `GET /v1/metrics/error/count` - Get error count metrics
- `GET /v1/metrics/session/count` - Get session count metrics
- `GET /v1/metrics/tool_interactions` - Get tool interactions metrics

See [Metrics Endpoints Guide](./metrics-endpoints-guide.md) for detailed documentation.

### Security API

Endpoints for retrieving security-related information:

- `GET /v1/security/alerts` - Get security alerts with filtering options
- `GET /v1/security/alerts/count` - Get security alerts count
- `GET /v1/security/alerts/timeseries` - Get security alerts time series data
- `GET /v1/security/alerts/{alert_id}` - Get detailed information about a specific security alert
- `GET /v1/security/alerts/{alert_id}/triggers` - Get triggered event IDs for a specific security alert

These endpoints provide comprehensive security monitoring capabilities, including:
- Alert filtering by severity, type, and agent
- Time-based alert analysis
- Alert count and trend analysis
- Detailed alert information
- Traceability between alerts and triggering events

See [Security Endpoints Guide](./security-endpoints-guide.md) for detailed documentation.

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

### LLM Analytics

The following endpoints provide comprehensive analytics for LLM usage:

- `GET /v1/metrics/llm/analytics` - Get comprehensive LLM usage analytics with flexible breakdowns
- `GET /v1/metrics/llm/models` - Get LLM model performance comparison
- `GET /v1/metrics/llm/usage_trends` - Get LLM usage trends over time
- `GET /v1/metrics/llm/agent_usage` - Get LLM usage by agent

These new endpoints replace several deprecated endpoints:

- ~~`GET /v1/metrics/llm/request_count`~~ - (Deprecated) Get LLM request count metrics
- ~~`GET /v1/metrics/llm/token_usage`~~ - (Deprecated) Get LLM token usage metrics
- ~~`GET /v1/metrics/llm/response_time`~~ - (Deprecated) Get LLM response time metrics
- ~~`GET /v1/metrics/llms`~~ - (Deprecated) Get aggregated LLM usage metrics
- ~~`GET /v1/metrics/llms/requests`~~ - (Deprecated) Get LLM request metrics
- ~~`GET /v1/metrics/usage`~~ - (Deprecated) Get overall usage patterns

#### LLM Analytics Endpoint

`GET /v1/metrics/llm/analytics`

This endpoint provides comprehensive LLM usage analytics with flexible filtering and breakdowns.

**Parameters:**
- `agent_id` (optional) - Filter by agent ID
- `model_name` (optional) - Filter by model name
- `from_time` (optional) - Start time in ISO format
- `to_time` (optional) - End time in ISO format
- `granularity` (optional, default: "day") - Time granularity: "minute", "hour", or "day"
- `breakdown_by` (optional, default: "none") - Dimension to break down by: "none", "agent", "model", or "time"

**Response:**
```json
{
  "total": {
    "request_count": 1250,
    "response_time_avg": 1842.5,
    "response_time_p95": 3625.3,
    "success_rate": 0.98,
    "error_rate": 0.02,
    "token_count_input": 124500,
    "token_count_output": 67890,
    "token_count_total": 192390,
    "estimated_cost_usd": 3.86,
    "first_seen": "2023-09-01T00:00:00Z",
    "last_seen": "2023-09-30T23:59:59Z"
  },
  "breakdown": [
    {
      "key": "gpt-4",
      "metrics": {
        "request_count": 850,
        "response_time_avg": 2140.2,
        "response_time_p95": 4125.7,
        "success_rate": 0.99,
        "error_rate": 0.01,
        "token_count_input": 84500,
        "token_count_output": 47890,
        "token_count_total": 132390,
        "estimated_cost_usd": 3.31,
        "first_seen": "2023-09-01T00:00:00Z",
        "last_seen": "2023-09-30T23:59:59Z"
      }
    },
    {
      "key": "gpt-3.5-turbo",
      "metrics": {
        "request_count": 400,
        "response_time_avg": 1210.3,
        "response_time_p95": 2380.5,
        "success_rate": 0.96,
        "error_rate": 0.04,
        "token_count_input": 40000,
        "token_count_output": 20000,
        "token_count_total": 60000,
        "estimated_cost_usd": 0.55,
        "first_seen": "2023-09-01T12:30:45Z",
        "last_seen": "2023-09-29T18:45:12Z"
      }
    }
  ],
  "from_time": "2023-09-01T00:00:00Z",
  "to_time": "2023-09-30T23:59:59Z",
  "filters": {
    "agent_id": null,
    "model_name": null,
    "from_time": "2023-09-01T00:00:00Z",
    "to_time": "2023-09-30T23:59:59Z",
    "granularity": "day"
  },
  "breakdown_by": "model"
}
```

#### LLM Model Comparison Endpoint

`GET /v1/metrics/llm/models`

This endpoint provides a comparison of different LLM models' performance metrics.

**Parameters:**
- `agent_id` (optional) - Filter by agent ID
- `from_time` (optional) - Start time in ISO format
- `to_time` (optional) - End time in ISO format

**Response:** Same format as `/v1/metrics/llm/analytics` with `breakdown_by` set to "model".

#### LLM Usage Trends Endpoint

`GET /v1/metrics/llm/usage_trends`

This endpoint provides LLM usage trends over time with flexible time granularity.

**Parameters:**
- `agent_id` (optional) - Filter by agent ID
- `model_name` (optional) - Filter by model name
- `from_time` (optional) - Start time in ISO format
- `to_time` (optional) - End time in ISO format
- `granularity` (optional, default: "day") - Time granularity: "minute", "hour", or "day"

**Response:** Same format as `/v1/metrics/llm/analytics` with `breakdown_by` set to "time".

#### LLM Agent Usage Endpoint

`GET /v1/metrics/llm/agent_usage`

This endpoint provides LLM usage broken down by agent.

**Parameters:**
- `model_name` (optional) - Filter by model name
- `from_time` (optional) - Start time in ISO format
- `to_time` (optional) - End time in ISO format

**Response:** Same format as `/v1/metrics/llm/analytics` with `breakdown_by` set to "agent".

### GET /v1/metrics/llm/agent_model_relationships

Get comprehensive agent-model relationship analytics.

This endpoint provides rich data about which agents used which models, when they were used, and usage statistics. Results can be visualized as histograms, trends, and other charts.

**Query Parameters:**
- `agent_id` (optional): Filter by agent ID
- `model_name` (optional): Filter by model name
- `from_time` (optional): Start time in ISO format
- `to_time` (optional): End time in ISO format
- `granularity` (optional): Time granularity (`minute`, `hour`, `day`)
- `include_distributions` (optional): Whether to include time and token distributions for visualization (default: false)

**Response:**
```json
{
  "total": {
    "request_count": 325,
    "response_time_avg": 824.56,
    "response_time_p95": 1450.32,
    "success_rate": 0.97,
    "error_rate": 0.03,
    "token_count_input": 15240,
    "token_count_output": 8732,
    "token_count_total": 23972,
    "estimated_cost_usd": 0.47,
    "first_seen": "2023-04-01T00:00:00Z",
    "last_seen": "2023-04-30T23:59:59Z"
  },
  "breakdown": [
    {
      "key": "support-agent:gpt-4",
      "metrics": {
        "request_count": 125,
        "response_time_avg": 1200.34,
        "response_time_p95": 1820.45,
        "success_rate": 0.99,
        "error_rate": 0.01,
        "token_count_input": 8240,
        "token_count_output": 5500,
        "token_count_total": 13740,
        "estimated_cost_usd": 0.412,
        "first_seen": "2023-04-01T00:00:00Z",
        "last_seen": "2023-04-30T23:59:59Z"
      },
      "relation_type": "primary",
      "time_distribution": [
        {
          "timestamp": "2023-04-01T00:00:00Z",
          "request_count": 42,
          "input_tokens": 2800,
          "output_tokens": 1850,
          "total_tokens": 4650,
          "avg_duration": 1150.25
        },
        {
          "timestamp": "2023-04-02T00:00:00Z",
          "request_count": 38,
          "input_tokens": 2500,
          "output_tokens": 1700,
          "total_tokens": 4200,
          "avg_duration": 1220.75
        }
      ],
      "token_distribution": [
        {
          "bucket_range": "0-100",
          "lower_bound": 0,
          "upper_bound": 100,
          "request_count": 12,
          "input_tokens": 480,
          "output_tokens": 320,
          "total_tokens": 800,
          "avg_duration": 850.45
        },
        {
          "bucket_range": "100-500",
          "lower_bound": 100,
          "upper_bound": 500,
          "request_count": 85,
          "input_tokens": 5460,
          "output_tokens": 3680,
          "total_tokens": 9140,
          "avg_duration": 1100.32
        }
      ]
    },
    {
      "key": "support-agent:claude-3-sonnet",
      "metrics": {
        "request_count": 75,
        "response_time_avg": 605.77,
        "response_time_p95": 980.21,
        "success_rate": 0.95,
        "error_rate": 0.05,
        "token_count_input": 3500,
        "output_tokens": 1500,
        "token_count_total": 5000,
        "estimated_cost_usd": 0.028,
        "first_seen": "2023-04-01T00:00:00Z",
        "last_seen": "2023-04-30T23:59:59Z"
      },
      "relation_type": "secondary"
    }
  ],
  "from_time": "2023-04-01T00:00:00Z",
  "to_time": "2023-04-30T23:59:59Z",
  "filters": {
    "agent_id": "support-agent",
    "model_name": null,
    "from_time": "2023-04-01T00:00:00Z",
    "to_time": "2023-04-30T23:59:59Z",
    "granularity": "day"
  },
  "breakdown_by": "agent"
}
``` 