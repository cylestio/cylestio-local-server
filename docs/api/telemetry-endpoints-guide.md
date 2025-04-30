# Telemetry Endpoints Guide

This guide provides detailed information about the Telemetry API endpoints, which are used for submitting and retrieving telemetry events from AI agents.

## Event Format

All telemetry events follow this standard format:

```json
{
  "schema_version": "1.0",
  "timestamp": "2024-03-01T12:34:56.789Z",
  "trace_id": "trace-123456789",
  "span_id": "span-123456789",
  "parent_span_id": "parent-span-123456789",
  "name": "event.name",
  "level": "INFO",
  "agent_id": "agent-123456789",
  "attributes": {
    "key1": "value1",
    "key2": "value2"
  }
}
```

- `schema_version`: Version of the telemetry schema (e.g., "1.0")
- `timestamp`: Event timestamp in ISO 8601 format
- `trace_id`: Unique identifier for the trace
- `span_id`: Identifier for the event span (optional)
- `parent_span_id`: Identifier for the parent span (optional)
- `name`: Event name (see Event Types below)
- `level`: Log level (e.g., "INFO", "WARNING", "ERROR")
- `agent_id`: Identifier for the agent that generated the event
- `attributes`: Key-value pairs with event-specific data

## Event Types

Common event types include:

- **LLM Events**: `llm.request`, `llm.response`
- **Tool Events**: `tool.start`, `tool.end`
- **Security Events**: `security.alert`
- **Session Events**: `session.start`, `session.end`
- **Error Events**: `error.general`, `error.validation`

## Submit a Single Telemetry Event

Submit a single telemetry event for processing and storage.

**Endpoint**: `POST /v1/telemetry`

**Request Body**:
```json
{
  "schema_version": "1.0",
  "timestamp": "2024-03-01T12:34:56.789Z",
  "trace_id": "trace-123456789",
  "span_id": "span-123456789",
  "parent_span_id": "parent-span-123456789",
  "name": "llm.request",
  "level": "INFO",
  "agent_id": "agent-123456789",
  "attributes": {
    "llm.model": "claude-3-opus",
    "llm.prompt": "Explain quantum physics",
    "llm.max_tokens": 1000
  }
}
```

**Response**:
```json
{
  "success": true,
  "event_id": "evt-123456789"
}
```

**Error Response**:
```json
{
  "success": false,
  "error": "Invalid event format"
}
```

### Example: Submitting an LLM Request Event

```typescript
// Web App Dashboard code example
async function submitLLMRequestEvent(agentId, model, prompt) {
  const event = {
    schema_version: "1.0",
    timestamp: new Date().toISOString(),
    trace_id: generateUUID(), // Your UUID generation function
    span_id: generateUUID(),
    name: "llm.request",
    level: "INFO",
    agent_id: agentId,
    attributes: {
      "llm.model": model,
      "llm.prompt": prompt
    }
  };

  const response = await fetch('/v1/telemetry', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(event)
  });

  return await response.json();
}
```

## Submit Multiple Telemetry Events (Batch)

Submit multiple telemetry events for processing and storage.

**Endpoint**: `POST /v1/telemetry/batch`

**Request Body**:
```json
{
  "events": [
    {
      "schema_version": "1.0",
      "timestamp": "2024-03-01T12:34:56.789Z",
      "trace_id": "trace-123456789",
      "span_id": "span-123456789",
      "name": "llm.request",
      "level": "INFO",
      "agent_id": "agent-123456789",
      "attributes": {
        "llm.model": "claude-3-opus"
      }
    },
    {
      "schema_version": "1.0",
      "timestamp": "2024-03-01T12:35:00.123Z",
      "trace_id": "trace-123456789",
      "span_id": "span-987654321",
      "parent_span_id": "span-123456789",
      "name": "llm.response",
      "level": "INFO",
      "agent_id": "agent-123456789",
      "attributes": {
        "llm.model": "claude-3-opus",
        "llm.completion": "Quantum physics is..."
      }
    }
  ]
}
```

**Response**:
```json
{
  "success": true,
  "total": 2,
  "processed": 2,
  "failed": 0
}
```

**Partial Failure Response**:
```json
{
  "success": false,
  "total": 2,
  "processed": 1,
  "failed": 1,
  "details": [
    {
      "index": 1,
      "event_name": "llm.response",
      "error": "Invalid event format"
    }
  ]
}
```

## Retrieve Telemetry Events

Retrieve telemetry events with optional filtering.

**Endpoint**: `GET /v1/telemetry/events`

**Query Parameters**:
- `agent_id` (string, optional): Filter by agent ID
- `event_name` (string, optional): Filter by event name
- `level` (string, optional): Filter by log level
- `trace_id` (string, optional): Filter by trace ID
- `from_time` (datetime, optional): Start time
- `to_time` (datetime, optional): End time
- `limit` (integer, default: 100): Maximum number of events to return
- `offset` (integer, default: 0): Number of events to skip

**Response**:
```json
[
  {
    "id": "evt-123456789",
    "schema_version": "1.0",
    "timestamp": "2024-03-01T12:34:56.789Z",
    "trace_id": "trace-123456789",
    "span_id": "span-123456789",
    "parent_span_id": null,
    "name": "llm.request",
    "level": "INFO",
    "agent_id": "agent-123456789",
    "attributes": {
      "llm.model": "claude-3-opus",
      "llm.prompt": "Explain quantum physics"
    }
  },
  {
    "id": "evt-987654321",
    "schema_version": "1.0",
    "timestamp": "2024-03-01T12:35:00.123Z",
    "trace_id": "trace-123456789",
    "span_id": "span-987654321",
    "parent_span_id": "span-123456789",
    "name": "llm.response",
    "level": "INFO",
    "agent_id": "agent-123456789",
    "attributes": {
      "llm.model": "claude-3-opus",
      "llm.completion": "Quantum physics is..."
    }
  }
]
```

### Example: Retrieving Events for a Specific Agent

```typescript
// Web App Dashboard code example
async function getAgentEvents(agentId, timeRange = '1d', limit = 50) {
  const params = new URLSearchParams({
    agent_id: agentId,
    time_range: timeRange,
    limit: limit.toString()
  });

  const response = await fetch(`/v1/telemetry/events?${params.toString()}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json'
    }
  });

  return await response.json();
}
```

## Get Multiple Telemetry Events by IDs

Retrieve multiple specific telemetry events by providing a list of event IDs.

**Endpoint**: `POST /v1/telemetry/events/by-ids`

**Request Body**:
```json
{
  "event_ids": [
    "evt-123456789",
    "evt-987654321"
  ]
}
```

**Response**:
```json
[
  {
    "id": "evt-123456789",
    "schema_version": "1.0",
    "timestamp": "2024-03-01T12:34:56.789Z",
    "trace_id": "trace-123456789",
    "span_id": "span-123456789",
    "parent_span_id": null,
    "name": "llm.request",
    "level": "INFO",
    "agent_id": "agent-123456789",
    "attributes": {
      "llm.model": "claude-3-opus",
      "llm.prompt": "Explain quantum physics"
    }
  },
  {
    "id": "evt-987654321",
    "schema_version": "1.0",
    "timestamp": "2024-03-01T12:35:00.123Z",
    "trace_id": "trace-123456789",
    "span_id": "span-987654321",
    "parent_span_id": "span-123456789",
    "name": "llm.response",
    "level": "INFO",
    "agent_id": "agent-123456789",
    "attributes": {
      "llm.model": "claude-3-opus",
      "llm.completion": "Quantum physics is..."
    }
  }
]
```

### Example: Retrieving Multiple Events by IDs

```typescript
// Web App Dashboard code example
async function getEventsByIds(eventIds) {
  const response = await fetch('/v1/telemetry/events/by-ids', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ event_ids: eventIds })
  });

  return await response.json();
}
```

## Get a Specific Telemetry Event by ID

Retrieve a specific telemetry event by its ID.

**Endpoint**: `GET /v1/telemetry/events/{event_id}`

**Path Parameters**:
- `event_id`: ID of the event to retrieve

**Response**:
```json
{
  "id": "evt-123456789",
  "schema_version": "1.0",
  "timestamp": "2024-03-01T12:34:56.789Z",
  "trace_id": "trace-123456789",
  "span_id": "span-123456789",
  "parent_span_id": null,
  "name": "llm.request",
  "level": "INFO",
  "agent_id": "agent-123456789",
  "attributes": {
    "llm.model": "claude-3-opus",
    "llm.prompt": "Explain quantum physics"
  }
}
```

## Get Events by Trace ID

Retrieve all events associated with a specific trace.

**Endpoint**: `GET /v1/telemetry/traces/{trace_id}`

**Path Parameters**:
- `trace_id`: ID of the trace

**Response**:
```json
[
  {
    "id": "evt-123456789",
    "schema_version": "1.0",
    "timestamp": "2024-03-01T12:34:56.789Z",
    "trace_id": "trace-123456789",
    "span_id": "span-123456789",
    "parent_span_id": null,
    "name": "llm.request",
    "level": "INFO",
    "agent_id": "agent-123456789",
    "attributes": {
      "llm.model": "claude-3-opus",
      "llm.prompt": "Explain quantum physics"
    }
  },
  {
    "id": "evt-987654321",
    "schema_version": "1.0",
    "timestamp": "2024-03-01T12:35:00.123Z",
    "trace_id": "trace-123456789",
    "span_id": "span-987654321",
    "parent_span_id": "span-123456789",
    "name": "llm.response",
    "level": "INFO",
    "agent_id": "agent-123456789",
    "attributes": {
      "llm.model": "claude-3-opus",
      "llm.completion": "Quantum physics is..."
    }
  }
]
```

### Example: Visualizing a Complete Trace in the Dashboard

```typescript
// Web App Dashboard code example
async function visualizeTrace(traceId) {
  const events = await fetch(`/v1/telemetry/traces/${traceId}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json'
    }
  }).then(res => res.json());

  // Sort events by timestamp
  events.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));

  // Create timeline visualization
  const timeline = events.map(event => ({
    id: event.id,
    name: event.name,
    time: new Date(event.timestamp),
    duration: event.attributes.duration_ms || 0,
    level: event.level,
    parentId: event.parent_span_id
  }));

  renderTimeline(timeline); // Your rendering function
}
```

## Common Use Cases

### 1. Capturing a Complete LLM Interaction

```typescript
// 1. Send llm.request event
await submitEvent({
  name: "llm.request",
  // ... other event fields
  attributes: {
    "llm.model": "claude-3-opus",
    "llm.prompt": "Generate a summary of the following text...",
    "llm.max_tokens": 2000
  }
});

// 2. Send llm.response event
await submitEvent({
  name: "llm.response",
  // ... other event fields
  attributes: {
    "llm.model": "claude-3-opus",
    "llm.completion": "The summary of the text is...",
    "llm.tokens.prompt": 250,
    "llm.tokens.completion": 150,
    "llm.duration_ms": 3200
  }
});
```

### 2. Recording Tool Usage

```typescript
// 1. Send tool.start event
await submitEvent({
  name: "tool.start",
  // ... other event fields
  attributes: {
    "tool.name": "database_query",
    "tool.parameters": JSON.stringify({
      "query": "SELECT * FROM users WHERE id = ?",
      "params": [123]
    })
  }
});

// 2. Send tool.end event
await submitEvent({
  name: "tool.end",
  // ... other event fields
  attributes: {
    "tool.name": "database_query",
    "tool.result": JSON.stringify({ "id": 123, "name": "John Doe" }),
    "tool.duration_ms": 150,
    "tool.status": "success"
  }
});
```

### 3. Reporting Security Alerts

```typescript
await submitEvent({
  name: "security.alert",
  level: "WARNING",
  // ... other event fields
  attributes: {
    "security.type": "prompt_injection",
    "security.severity": "medium",
    "security.description": "Potential prompt injection detected",
    "security.context": "User asked to 'ignore all previous instructions'",
    "security.mitigation": "Inserted warning message to agent"
  }
});
```

## Best Practices

1. **Always include trace_id**: Use a consistent trace ID to link related events.

2. **Use span_id and parent_span_id**: Create a proper hierarchy of spans to track the relationship between events.

3. **Be consistent with event naming**: Follow the `category.action` pattern for event names.

4. **Set appropriate log levels**:
   - `DEBUG`: Detailed debugging information
   - `INFO`: Normal operations
   - `WARNING`: Unexpected issues that don't disrupt operation
   - `ERROR`: Errors that disrupt normal operation
   - `CRITICAL`: Critical failures requiring immediate attention

5. **Include relevant attributes**: Add all relevant information in the attributes, but avoid including sensitive data.

6. **Batch when possible**: Use batch submission for multiple related events to reduce API calls.

7. **Use ISO timestamp format**: Always use ISO 8601 format for timestamps (e.g., "2024-03-01T12:34:56.789Z").

## Common Errors and Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| "Invalid timestamp format" | Timestamp not in ISO 8601 format | Use proper ISO format: "YYYY-MM-DDTHH:MM:SS.sssZ" |
| "Missing required field" | A required field is missing | Check that all required fields are included in the event |
| "Event processing failed" | Server error while processing | Check server logs for details, retry submission |
| "Rate limit exceeded" | Too many requests | Implement backoff strategy, batch requests |

## Schema Reference

For a complete reference of the telemetry event schema, including all required and optional fields, see the [Telemetry Schema Documentation](../telemetry-schema.md). 