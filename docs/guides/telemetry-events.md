# Telemetry Events Guide

This guide explains the structure, semantics, and best practices for telemetry events in the Cylestio Local Server.

## Event Structure

Telemetry events in Cylestio have a standardized structure:

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

### Core Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `schema_version` | String | No | Version of the event schema (defaults to "1.0") |
| `timestamp` | String | Yes | ISO 8601 formatted timestamp with timezone |
| `trace_id` | String | Yes | Unique identifier for the trace the event belongs to |
| `span_id` | String | No | Unique identifier for the span within the trace |
| `parent_span_id` | String | No | Identifier for the parent span (if applicable) |
| `name` | String | Yes | Event name/type (e.g., `llm.request`, `tool.execution`) |
| `level` | String | Yes | Event severity level (one of: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`) |
| `agent_id` | String | Yes | Identifier for the agent that generated the event |
| `attributes` | Object | No | Custom key-value pairs with event-specific data |

## Common Event Types

### LLM Events

- `llm.request` - An LLM request with attributes like `llm.request.model` and `llm.request.tokens`
- `llm.response` - An LLM response with attributes like `llm.response.time_ms` and `llm.response.tokens`

### Tool Events

- `tool.execution` - Start of a tool execution with attributes like `tool.name` and `tool.input`
- `tool.success` - Successful tool execution with attributes like `tool.output` and `tool.execution_time_ms`
- `tool.error` - Failed tool execution with attributes like `error.message` and `error.type`

### Session Events

- `session.start` - Start of a user session with attributes like `session.id` and `client.type`
- `session.end` - End of a user session with attributes like `session.duration_ms`

## Event Levels

| Level | Description |
|-------|-------------|
| `DEBUG` | Detailed information for debugging purposes |
| `INFO` | Normal operational information |
| `WARNING` | Something unexpected but not necessarily an error |
| `ERROR` | An error that prevented an operation from completing |
| `CRITICAL` | A severe error that requires immediate attention |

## Traces and Spans

Traces and spans allow you to track related events across distributed systems:

- A **trace** represents a complete flow of operations (e.g., a user request)
- A **span** represents a unit of work within a trace (e.g., an LLM call)

By setting `trace_id`, `span_id`, and `parent_span_id` appropriately, you can create hierarchical relationships between events.

## Best Practices

1. **Consistent Event Naming**: Use the format `category.action` (e.g., `llm.request`)
2. **Proper Timestamps**: Use ISO 8601 format with timezone (preferably UTC)
3. **Structured Attributes**: Use namespaced attributes (e.g., `llm.request.model` not just `model`)
4. **Include Trace Context**: Always include `trace_id` and `span_id`
5. **Use Appropriate Levels**: Choose the right level for the event importance
6. **Avoid Sensitive Information**: Never include full prompts, API keys, or user PII
7. **Keep Events Lightweight**: Include only relevant information

## Example: LLM Request and Response

```json
// LLM Request Event
{
  "timestamp": "2023-06-01T12:00:00Z",
  "trace_id": "trace-123456",
  "span_id": "span-request",
  "name": "llm.request",
  "level": "INFO",
  "agent_id": "my-agent",
  "attributes": {
    "llm.request.model": "gpt-4",
    "llm.request.tokens": 150,
    "session.id": "session-123"
  }
}

// LLM Response Event
{
  "timestamp": "2023-06-01T12:00:05Z",
  "trace_id": "trace-123456",
  "span_id": "span-response",
  "parent_span_id": "span-request",
  "name": "llm.response",
  "level": "INFO",
  "agent_id": "my-agent",
  "attributes": {
    "llm.response.time_ms": 1200,
    "llm.response.tokens": 80,
    "session.id": "session-123",
    "status": "success"
  }
}
```

## Example: Error Handling

```json
{
  "timestamp": "2023-06-01T12:01:05Z",
  "trace_id": "trace-123456",
  "span_id": "span-error",
  "name": "llm.error",
  "level": "ERROR",
  "agent_id": "my-agent",
  "attributes": {
    "error.message": "Failed to connect to LLM service",
    "error.type": "ConnectionError",
    "session.id": "session-123"
  }
}
```

For more detailed information about specific event types and attributes, refer to the [API Reference](../api/README.md). 