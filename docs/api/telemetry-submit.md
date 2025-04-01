# Submit Telemetry Event

Submit a single telemetry event for processing and storage.

**URL**: `/v1/telemetry`  
**Method**: `POST`  
**Auth required**: No (in development), Yes (in production)

## Request Body

```json
{
  "schema_version": "1.0",
  "timestamp": "2023-06-01T12:00:00Z",
  "trace_id": "trace-123456",
  "span_id": "span-123456",
  "parent_span_id": null,
  "name": "llm.request",
  "level": "INFO",
  "agent_id": "my-agent",
  "attributes": {
    "llm.request.model": "gpt-4",
    "llm.request.tokens": 150,
    "status": "success"
  }
}
```

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | String | ISO 8601 formatted timestamp with timezone (e.g., `2023-06-01T12:00:00Z`) |
| `trace_id` | String | Unique identifier for the trace the event belongs to |
| `name` | String | Event name/type (e.g., `llm.request`, `tool.execution`) |
| `level` | String | Event severity level (one of: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`) |
| `agent_id` | String | Identifier for the agent that generated the event |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `schema_version` | String | Version of the event schema (defaults to `1.0`) |
| `span_id` | String | Unique identifier for the span within the trace |
| `parent_span_id` | String | Identifier for the parent span (if applicable) |
| `attributes` | Object | Custom key-value pairs with event-specific data |

### Common Attribute Fields

While attributes are flexible, these are commonly used for specific event types:

#### LLM Request Events

- `llm.request.model` - Model name/identifier
- `llm.request.tokens` - Input token count
- `llm.request.prompt` - Shortened/hashed prompt content

#### LLM Response Events

- `llm.response.time_ms` - Response time in milliseconds
- `llm.response.tokens` - Output token count
- `llm.response.completion` - Shortened/hashed completion content

#### Tool Events

- `tool.name` - Tool name/identifier
- `tool.input` - Shortened/hashed tool input
- `tool.output` - Shortened/hashed tool output
- `status` - Tool execution status (e.g., `success`, `error`)
- `error.message` - Error message if the tool execution failed

## Success Response

**Code**: `200 OK`

```json
{
  "id": "event-uuid",
  "status": "created"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | String | UUID of the created event |
| `status` | String | Status of the operation (`created`) |

## Error Responses

### Invalid Request

**Code**: `422 Unprocessable Entity`

```json
{
  "detail": [
    {
      "loc": ["body", "timestamp"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### Invalid Event Level

**Code**: `422 Unprocessable Entity`

```json
{
  "detail": [
    {
      "loc": ["body", "level"],
      "msg": "Level must be one of ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']",
      "type": "value_error"
    }
  ]
}
```

### Internal Server Error

**Code**: `500 Internal Server Error`

```json
{
  "error": "Internal server error",
  "detail": "An unexpected error occurred processing the event"
}
```

## Example

### Python

```python
import requests
from datetime import datetime, timezone

event = {
    "schema_version": "1.0",
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "trace_id": "trace-123456",
    "span_id": "span-123456",
    "name": "llm.request",
    "level": "INFO",
    "agent_id": "my-agent",
    "attributes": {
        "llm.request.model": "gpt-4",
        "llm.request.tokens": 150,
        "status": "success"
    }
}

response = requests.post("http://localhost:8000/v1/telemetry", json=event)
print(response.json())
```

### cURL

```bash
curl -X POST http://localhost:8000/v1/telemetry \
  -H "Content-Type: application/json" \
  -d '{
    "schema_version": "1.0",
    "timestamp": "2023-06-01T12:00:00Z",
    "trace_id": "trace-123456",
    "span_id": "span-123456",
    "name": "llm.request",
    "level": "INFO",
    "agent_id": "my-agent",
    "attributes": {
      "llm.request.model": "gpt-4",
      "llm.request.tokens": 150,
      "status": "success"
    }
  }'
```

## Notes

- All timestamps should be in ISO 8601 format with timezone information (preferably UTC)
- Trace IDs and span IDs should be consistent across related events
- For high-volume event ingestion, consider using the batch endpoint instead 