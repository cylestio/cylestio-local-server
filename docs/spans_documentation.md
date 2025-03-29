# Spans in Cylestio Telemetry

## Overview

Spans represent discrete operations or units of work within a trace. They are a critical component of Cylestio's tracing system, allowing related events to be grouped together for better correlation and analysis. Spans form the foundation of the correlation system, enabling observability of complex AI interactions.

## Purpose of Spans

- **Event Correlation**: Group related events (like an LLM request and its response)
- **Duration Tracking**: Measure and analyze the time taken for operations
- **Hierarchical Relationships**: Model parent-child relationships between operations
- **Context Propagation**: Pass context through a chain of operations

## Span Data Model

The `Span` model includes the following key fields:

- `span_id`: A unique identifier for the span
- `trace_id`: The ID of the trace this span belongs to
- `parent_span_id`: The ID of the parent span, if any
- `root_span_id`: The ID of the root span in the hierarchy
- `name`: A descriptive name for the span (e.g., "llm_interaction")
- `start_timestamp`: When the span began
- `end_timestamp`: When the span completed

## Span Hierarchy and Relationships

Spans form a hierarchical tree structure within a trace:

- A **root span** has no parent and represents a top-level operation
- **Child spans** have a parent and represent sub-operations
- All spans in a hierarchy share the same `trace_id`
- The `root_span_id` field allows quick access to the root of a span tree

Example hierarchy:
```
Root Span: "User Interaction"
  ├── Child Span: "LLM Query"
  │     ├── Grandchild Span: "Token Processing"
  │     └── Grandchild Span: "Response Generation"
  └── Child Span: "Tool Execution"
```

## Span Lifecycle

1. **Creation**: A span is created when an event with a span_id is received
2. **Update**: The span is updated as more events with the same span_id arrive
3. **Completion**: The span is completed when an event with a matching `*.finish` or `*.end` name is received

## Best Practices for Using Spans

### When to Create Spans

Create new spans for:
- Meaningful operations that have a start and end
- Operations that might contain sub-operations
- Operations that you want to measure the duration of
- Groups of events that logically belong together

### Naming Conventions

Span names should:
- Be descriptive of the operation being performed
- Follow a consistent pattern (e.g., `category_action`)
- Avoid using sensitive information

### Span Hierarchies

- Create a new child span for significant sub-operations
- Avoid deeply nested hierarchies (>5 levels) as they become hard to analyze
- Ensure child spans have shorter durations than their parents

### Tracing Context Propagation

- Always pass the `trace_id` between components
- Pass `parent_span_id` when creating child spans
- Set `span_id` on all events within a span

## Implementation Details

### Automatic Span Name Derivation

The system automatically derives span names from event names:
- "llm.call.start" → "llm_interaction"
- "tool.call.start" → "tool_interaction"
- "framework.initialization" → "framework_initialization"

### Timestamp Management

Span timestamps are set based on:
- The timestamps of events associated with the span
- The naming patterns of the events:
  - Events ending with `.start` or `.begin` set the `start_timestamp`
  - Events ending with `.finish`, `.end`, or `.stop` set the `end_timestamp`

### Span Relations to Other Entities

- **Events**: Many events can belong to a single span
- **Trace**: A span belongs to exactly one trace
- **Parent Span**: A span can have one parent span
- **Child Spans**: A span can have multiple child spans

## Examples

### Creating a Span Hierarchy

```python
# Create a root span for processing a user query
root_span_id = "span-123"
event1 = {
    "name": "query.start",
    "span_id": root_span_id,
    "trace_id": "trace-456",
    "timestamp": "2023-06-01T12:00:00Z"
}

# Create a child span for the LLM call
child_span_id = "span-789"
event2 = {
    "name": "llm.call.start", 
    "span_id": child_span_id,
    "parent_span_id": root_span_id,
    "trace_id": "trace-456",
    "timestamp": "2023-06-01T12:00:05Z"
}
```

### Analyzing Span Data

```python
# Get all events in a span
events = db_session.query(Event).filter(Event.span_id == "span-123").all()

# Calculate span duration
span = db_session.query(Span).filter(Span.span_id == "span-123").first()
duration_seconds = span.get_duration_seconds()

# Get the entire span hierarchy
span_tree = span.get_span_tree(db_session)
```

## Debugging Spans

If spans aren't working as expected, check:

1. Are `span_id` values being correctly set on events?
2. Do events have the correct `parent_span_id` values?
3. Are timestamps being properly set on events?
4. Are span names being derived correctly?
5. Is the span hierarchy being correctly established?

## Conclusion

Spans are a powerful concept for tracking and analyzing operations in a distributed system. By using spans effectively, you can gain deep insights into the performance, behavior, and relationships of operations in your AI system. 