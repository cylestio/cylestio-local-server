# Agent-Specific API Endpoints

This document describes the agent-specific API endpoints that provide detailed insights and metrics for individual AI agents, enabling users to drill down into specific agent performance, usage, and behavior.

## Base Agent Endpoints

### List Agents

```
GET /api/v1/agents
```

Lists all monitored agents with optional filtering and sorting.

**Query Parameters:**
- `status` (optional): Filter by agent status (active, inactive, paused)
- `agent_type` (optional): Filter by agent type (assistant, chatbot, autonomous, function, other)
- `created_after` (optional): Filter by creation date (ISO 8601 format)
- `page` (optional): Page number (default: 1)
- `page_size` (optional): Items per page (default: 50, max: 1000)
- `sort_by` (optional): Field to sort by (default: created_at)
- `sort_dir` (optional): Sort direction (asc, desc) (default: desc)

**Response:**
```json
{
  "items": [
    {
      "agent_id": "weather-agent",
      "name": "Weather Assistant",
      "type": "assistant",
      "status": "active",
      "created_at": "2023-01-01T00:00:00Z",
      "updated_at": "2023-02-15T12:30:45Z",
      "request_count": 1200,
      "token_usage": 45000,
      "error_count": 12
    },
    ...
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
    "timestamp": "2023-03-01T12:00:00Z"
  }
}
```

### Get Agent Details

```
GET /api/v1/agents/{agent_id}
```

Get detailed information about a specific agent.

**Path Parameters:**
- `agent_id`: Agent ID

**Response:**
```json
{
  "agent_id": "weather-agent",
  "name": "Weather Assistant",
  "type": "assistant",
  "status": "active",
  "description": "An AI assistant that provides weather information",
  "created_at": "2023-01-01T00:00:00Z",
  "updated_at": "2023-02-15T12:30:45Z",
  "configuration": {
    "model": "gpt-4",
    "temperature": 0.7
  },
  "metrics": {
    "request_count": 1200,
    "token_usage": 45000,
    "avg_response_time_ms": 850,
    "tool_usage": 350,
    "error_count": 12
  }
}
```

## Agent Dashboard Endpoint

### Get Agent Dashboard

```
GET /api/v1/agents/{agent_id}/dashboard
```

Get dashboard metrics for a specific agent over the specified time period.

**Path Parameters:**
- `agent_id`: Agent ID

**Query Parameters:**
- `time_range` (optional): Time range for metrics (1h, 1d, 7d, 30d) (default: 30d)
- `metrics` (optional): Comma-separated list of metrics to include

**Response:**
```json
{
  "agent_id": "weather-agent",
  "period": "Last 7d",
  "metrics": [
    {
      "metric": "llm_request_count",
      "value": 1200,
      "change": 15.5,
      "trend": "up"
    },
    {
      "metric": "token_usage",
      "value": 45000,
      "change": 7.2,
      "trend": "up"
    },
    {
      "metric": "avg_response_time",
      "value": 850,
      "change": -5.3,
      "trend": "down"
    },
    {
      "metric": "tool_execution_count",
      "value": 350,
      "change": 12.1,
      "trend": "up"
    },
    {
      "metric": "error_count",
      "value": 12,
      "change": -8.5,
      "trend": "down"
    }
  ]
}
```

## Agent LLM-Related Endpoints

### Get Agent LLM Usage

```
GET /api/v1/agents/{agent_id}/llms
```

Get LLM usage overview for a specific agent.

**Path Parameters:**
- `agent_id`: Agent ID

**Query Parameters:**
- `from_time` (optional): Start time (ISO 8601 format)
- `to_time` (optional): End time (ISO 8601 format)
- `time_range` (optional): Predefined time range (1h, 1d, 7d, 30d) (default: 30d)

**Response:**
```json
{
  "items": [
    {
      "model": "gpt-4",
      "vendor": "openai",
      "request_count": 800,
      "input_tokens": 25000,
      "output_tokens": 15000,
      "total_tokens": 40000,
      "estimated_cost": 2.50
    },
    {
      "model": "gpt-3.5-turbo",
      "vendor": "openai",
      "request_count": 400,
      "input_tokens": 3000,
      "output_tokens": 2000,
      "total_tokens": 5000,
      "estimated_cost": 0.10
    }
  ],
  "total_requests": 1200,
  "total_tokens": 45000,
  "total_cost": 2.60,
  "meta": {
    "timestamp": "2023-03-01T12:00:00Z",
    "time_period": "Last 30d"
  }
}
```

### Get Agent LLM Requests

```
GET /api/v1/agents/{agent_id}/llms/requests
```

Get detailed LLM requests for a specific agent.

**Path Parameters:**
- `agent_id`: Agent ID

**Query Parameters:**
- `model` (optional): Filter by LLM model
- `status` (optional): Filter by request status
- `from_time` (optional): Start time (ISO 8601 format)
- `to_time` (optional): End time (ISO 8601 format)
- `time_range` (optional): Predefined time range (1h, 1d, 7d, 30d) (default: 1d)
- `page` (optional): Page number (default: 1)
- `page_size` (optional): Items per page (default: 50, max: 1000)

**Response:**
```json
{
  "items": [
    {
      "request_id": "req-00001",
      "timestamp": "2023-03-01T11:45:00Z",
      "model": "gpt-4",
      "status": "success",
      "input_tokens": 210,
      "output_tokens": 150,
      "duration_ms": 850,
      "prompt_summary": "What's the weather like in New York?",
      "response_summary": "The current weather in New York is sunny with a temperature of 72°F..."
    },
    ...
  ],
  "pagination": {
    "page": 1,
    "page_size": 50,
    "total": 45,
    "total_pages": 1,
    "has_next": false,
    "has_prev": false
  },
  "meta": {
    "timestamp": "2023-03-01T12:00:00Z",
    "time_period": "Last 1d",
    "filters_applied": {
      "model": "gpt-4"
    }
  }
}
```

### Get Agent Token Usage

```
GET /api/v1/agents/{agent_id}/tokens
```

Get token usage metrics for a specific agent.

**Path Parameters:**
- `agent_id`: Agent ID

**Query Parameters:**
- `from_time` (optional): Start time (ISO 8601 format)
- `to_time` (optional): End time (ISO 8601 format)
- `time_range` (optional): Predefined time range (1h, 1d, 7d, 30d) (default: 7d)
- `group_by` (optional): Group by field (model, time)
- `interval` (optional): Time interval for grouping (1h, 1d) (default: 1d)
- `page` (optional): Page number (default: 1)
- `page_size` (optional): Items per page (default: 50, max: 1000)

**Response (grouped by time):**
```json
{
  "items": [
    {
      "timestamp": "2023-03-01T00:00:00Z",
      "input_tokens": 2000,
      "output_tokens": 1500,
      "total_tokens": 3500
    },
    {
      "timestamp": "2023-02-28T00:00:00Z",
      "input_tokens": 2100,
      "output_tokens": 1550,
      "total_tokens": 3650
    },
    ...
  ],
  "total_input": 28000,
  "total_output": 17000,
  "total": 45000,
  "pagination": {
    "page": 1,
    "page_size": 50,
    "total": 7,
    "total_pages": 1,
    "has_next": false,
    "has_prev": false
  },
  "meta": {
    "timestamp": "2023-03-01T12:00:00Z",
    "time_period": "Last 7d",
    "group_by": "time"
  }
}
```

**Response (grouped by model):**
```json
{
  "items": [
    {
      "timestamp": "2023-03-01T12:00:00Z",
      "input_tokens": 25000,
      "output_tokens": 15000,
      "total_tokens": 40000,
      "model": "gpt-4"
    },
    {
      "timestamp": "2023-03-01T12:00:00Z",
      "input_tokens": 3000,
      "output_tokens": 2000,
      "total_tokens": 5000,
      "model": "gpt-3.5-turbo"
    }
  ],
  "total_input": 28000,
  "total_output": 17000,
  "total": 45000,
  "pagination": {
    "page": 1,
    "page_size": 50,
    "total": 2,
    "total_pages": 1,
    "has_next": false,
    "has_prev": false
  },
  "meta": {
    "timestamp": "2023-03-01T12:00:00Z",
    "time_period": "Last 7d",
    "group_by": "model"
  }
}
```

## Agent Tool Usage Endpoints

### Get Agent Tool Usage

```
GET /api/v1/agents/{agent_id}/tools
```

Get tool usage overview for a specific agent.

**Path Parameters:**
- `agent_id`: Agent ID

**Query Parameters:**
- `from_time` (optional): Start time (ISO 8601 format)
- `to_time` (optional): End time (ISO 8601 format)
- `time_range` (optional): Predefined time range (1h, 1d, 7d, 30d) (default: 30d)
- `category` (optional): Filter by tool category

**Response:**
```json
{
  "items": [
    {
      "tool_name": "web_search",
      "category": "external_api",
      "execution_count": 150,
      "success_count": 145,
      "error_count": 5,
      "success_rate": 0.97,
      "avg_duration_ms": 750
    },
    {
      "tool_name": "document_retrieval",
      "category": "internal_function",
      "execution_count": 100,
      "success_count": 98,
      "error_count": 2,
      "success_rate": 0.98,
      "avg_duration_ms": 250
    },
    ...
  ],
  "total_executions": 350,
  "overall_success_rate": 0.97,
  "meta": {
    "timestamp": "2023-03-01T12:00:00Z",
    "time_period": "Last 30d"
  }
}
```

### Get Agent Tool Executions

```
GET /api/v1/agents/{agent_id}/tools/executions
```

Get detailed tool executions for a specific agent.

**Path Parameters:**
- `agent_id`: Agent ID

**Query Parameters:**
- `tool_name` (optional): Filter by tool name
- `status` (optional): Filter by execution status
- `from_time` (optional): Start time (ISO 8601 format)
- `to_time` (optional): End time (ISO 8601 format)
- `time_range` (optional): Predefined time range (1h, 1d, 7d, 30d) (default: 1d)
- `page` (optional): Page number (default: 1)
- `page_size` (optional): Items per page (default: 50, max: 1000)

**Response:**
```json
{
  "items": [
    {
      "execution_id": "exec-00001",
      "timestamp": "2023-03-01T11:50:00Z",
      "tool_name": "web_search",
      "status": "success",
      "duration_ms": 350,
      "parameters": {
        "query": "weather New York"
      },
      "result_summary": "Retrieved weather information for New York"
    },
    ...
  ],
  "pagination": {
    "page": 1,
    "page_size": 50,
    "total": 65,
    "total_pages": 2,
    "has_next": true,
    "has_prev": false
  },
  "meta": {
    "timestamp": "2023-03-01T12:00:00Z",
    "time_period": "Last 1d",
    "filters_applied": {
      "tool_name": "web_search"
    }
  }
}
```

## Agent Session and Trace Endpoints

### Get Agent Sessions

```
GET /api/v1/agents/{agent_id}/sessions
```

Get sessions for a specific agent. This endpoint connects to the analysis layer to retrieve real session data from the database.

**Path Parameters:**
- `agent_id`: Agent ID

**Query Parameters:**
- `status` (optional): Filter by session status
- `from_time` (optional): Start time (ISO 8601 format)
- `to_time` (optional): End time (ISO 8601 format)
- `time_range` (optional): Predefined time range (1h, 1d, 7d, 30d) (default: 7d)
- `min_duration` (optional): Minimum session duration in seconds
- `max_duration` (optional): Maximum session duration in seconds
- `page` (optional): Page number (default: 1)
- `page_size` (optional): Items per page (default: 50, max: 1000)

**Response:**
```json
{
  "items": [
    {
      "session_id": "sess-00001",
      "start_time": "2023-03-01T10:00:00Z",
      "end_time": "2023-03-01T10:15:00Z",
      "duration_seconds": 900,
      "event_count": 120,
      "llm_request_count": 18,
      "tool_execution_count": 25,
      "error_count": 0,
      "status": "completed"
    },
    ...
  ],
  "pagination": {
    "page": 1,
    "page_size": 50,
    "total": 85,
    "total_pages": 2,
    "has_next": true,
    "has_prev": false
  },
  "meta": {
    "timestamp": "2023-03-01T12:00:00Z",
    "time_period": "Last 7d",
    "filters_applied": {
      "status": "completed"
    }
  }
}
```

### Get Agent Traces

```
GET /api/v1/agents/{agent_id}/traces
```

Get execution traces for a specific agent. This endpoint connects to the analysis layer to retrieve real trace data from the database.

**Path Parameters:**
- `agent_id`: Agent ID

**Query Parameters:**
- `status` (optional): Filter by trace status
- `from_time` (optional): Start time (ISO 8601 format)
- `to_time` (optional): End time (ISO 8601 format)
- `time_range` (optional): Predefined time range (1h, 1d, 7d, 30d) (default: 1d)
- `min_duration` (optional): Minimum trace duration in milliseconds
- `max_duration` (optional): Maximum trace duration in milliseconds
- `page` (optional): Page number (default: 1)
- `page_size` (optional): Items per page (default: 50, max: 1000)

**Response:**
```json
{
  "items": [
    {
      "trace_id": "trace-00001",
      "start_time": "2023-03-01T11:55:00Z",
      "end_time": "2023-03-01T11:55:03Z",
      "duration_ms": 3000,
      "event_count": 8,
      "status": "completed",
      "initial_event_type": "user_input"
    },
    ...
  ],
  "pagination": {
    "page": 1,
    "page_size": 50,
    "total": 120,
    "total_pages": 3,
    "has_next": true,
    "has_prev": false
  },
  "meta": {
    "timestamp": "2023-03-01T12:00:00Z",
    "time_period": "Last 1d",
    "filters_applied": {
      "status": "completed"
    }
  }
}
```

## Agent Security and Alert Endpoints

### Get Agent Alerts

```
GET /api/v1/agents/{agent_id}/alerts
```

Get security alerts for a specific agent. This endpoint connects to the analysis layer to retrieve real security alert data from the database.

**Path Parameters:**
- `agent_id`: Agent ID

**Query Parameters:**
- `from_time` (optional): Start time (ISO 8601 format)
- `to_time` (optional): End time (ISO 8601 format)
- `time_range` (optional): Predefined time range (1h, 1d, 7d, 30d) (default: 7d)
- `type` (optional): Filter by alert type
- `severity` (optional): Filter by alert severity
- `status` (optional): Filter by alert status
- `page` (optional): Page number (default: 1)
- `page_size` (optional): Items per page (default: 50, max: 1000)

**Response:**
```json
{
  "items": [
    {
      "alert_id": "alert-00001",
      "timestamp": "2023-03-01T09:30:00Z",
      "type": "prompt_injection",
      "severity": "high",
      "description": "Possible prompt injection attempt detected",
      "status": "open",
      "related_event_id": "event-000123"
    },
    ...
  ],
  "pagination": {
    "page": 1,
    "page_size": 50,
    "total": 35,
    "total_pages": 1,
    "has_next": false,
    "has_prev": false
  },
  "meta": {
    "timestamp": "2023-03-01T12:00:00Z",
    "time_period": "Last 7d",
    "filters_applied": {
      "severity": "high"
    }
  }
}
``` 