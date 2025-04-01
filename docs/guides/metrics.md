# Metrics Guide

This guide explains the metrics available in the Cylestio Local Server and how to use them effectively.

## Available Metrics

The Cylestio Local Server provides several built-in metrics that are automatically calculated from telemetry events:

### LLM Metrics

| Metric | Description | Event Types Used |
|--------|-------------|------------------|
| `llm_request_count` | Number of LLM requests | `llm.request` |
| `llm_token_usage` | Total tokens used in LLM requests | `llm.request` (using `llm.request.tokens` attribute) |
| `llm_response_time` | Average response time for LLM requests in milliseconds | `llm.response` (using `llm.response.time_ms` attribute) |

### Tool Metrics

| Metric | Description | Event Types Used |
|--------|-------------|------------------|
| `tool_execution_count` | Number of tool executions | `tool.execution`, `tool.success`, `tool.error` |
| `tool_success_rate` | Percentage of successful tool executions | `tool.success` vs `tool.error` |

### General Metrics

| Metric | Description | Event Types Used |
|--------|-------------|------------------|
| `error_count` | Number of error events | Any event with level `ERROR` or `CRITICAL` |
| `session_count` | Number of unique sessions | Events with `session.id` attribute |

## Time Ranges

When querying metrics, you can specify different time ranges:

| Time Range | Description |
|------------|-------------|
| `1h` | Last hour |
| `6h` | Last 6 hours |
| `12h` | Last 12 hours |
| `1d` | Last day (24 hours) |
| `7d` | Last 7 days |
| `30d` | Last 30 days |

## Intervals

When retrieving time series data, you can specify the interval (bucket size):

| Interval | Description |
|----------|-------------|
| `1m` | 1 minute buckets |
| `5m` | 5 minute buckets |
| `15m` | 15 minute buckets |
| `1h` | 1 hour buckets |
| `6h` | 6 hour buckets |
| `1d` | 1 day buckets |

## Accessing Metrics

### Dashboard Metrics

The dashboard endpoint provides a summary of key metrics:

```
GET /v1/metrics/dashboard?time_range=1d
```

This returns metrics in a format suitable for displaying on a dashboard:

```json
{
  "period": {
    "from": "2023-06-01T00:00:00Z",
    "to": "2023-06-02T00:00:00Z"
  },
  "metrics": [
    {
      "metric": "llm_request_count",
      "value": 150
    },
    {
      "metric": "llm_token_usage",
      "value": 25000
    },
    {
      "metric": "llm_avg_response_time",
      "value": 1200
    },
    {
      "metric": "tool_execution_count",
      "value": 75
    },
    {
      "metric": "error_count",
      "value": 12
    },
    {
      "metric": "session_count",
      "value": 8
    }
  ]
}
```

### Specific Metric

To retrieve time series data for a specific metric:

```
GET /v1/metrics?metric=llm_request_count&time_range=1d&interval=1h
```

This returns the metric data with timestamps:

```json
{
  "metric": "llm_request_count",
  "from_time": "2023-06-01T00:00:00Z",
  "to_time": "2023-06-02T00:00:00Z",
  "interval": "1h",
  "data": [
    {
      "timestamp": "2023-06-01T00:00:00Z",
      "value": 10
    },
    {
      "timestamp": "2023-06-01T01:00:00Z",
      "value": 15
    },
    {
      "timestamp": "2023-06-01T02:00:00Z",
      "value": 8
    },
    ...
  ]
}
```

### Agent Metrics

To retrieve metrics broken down by agent:

```
GET /v1/metrics/agents?time_range=1d
```

This returns metrics for each agent:

```json
[
  {
    "agent_id": "agent1",
    "llm_requests": 50,
    "tool_executions": 25,
    "errors": 5,
    "timestamp": "2023-06-01T00:00:00Z"
  },
  {
    "agent_id": "agent2",
    "llm_requests": 30,
    "tool_executions": 15,
    "errors": 2,
    "timestamp": "2023-06-01T00:00:00Z"
  }
]
```

## Best Practices for Metrics

### 1. Consistent Event Naming

Use consistent event names to ensure accurate metrics. For example:

- `llm.request` for LLM request events
- `llm.response` for LLM response events
- `tool.execution` for tool execution events
- `tool.success` for successful tool executions
- `tool.error` for failed tool executions

### 2. Include Required Attributes

To ensure accurate metrics, include the required attributes in your events:

- For LLM token usage: include `llm.request.tokens` in `llm.request` events
- For LLM response time: include `llm.response.time_ms` in `llm.response` events
- For tool metrics: use proper event names (`tool.success`, `tool.error`)
- For session counting: include `session.id` attribute

### 3. Setting the Right Time Range

Choose the right time range for your use case:

- For real-time monitoring: use shorter ranges (`1h`, `6h`)
- For daily reports: use `1d`
- For trend analysis: use longer ranges (`7d`, `30d`)

### 4. Using Intervals Effectively

When retrieving time series data, choose an appropriate interval:

- For detailed short-term data: use small intervals (`1m`, `5m`)
- For longer periods: use larger intervals (`1h`, `1d`) to reduce data points

## Custom Metrics

While the Cylestio Local Server provides built-in metrics, you can create custom metrics by:

1. Using consistent event naming and attributes
2. Filtering events using the events API and calculating metrics client-side
3. Using the trace API to analyze sequences of events

## Example: Creating a Custom Metric

Here's an example of how to create a custom metric for "average tokens per session":

```python
import requests
from collections import defaultdict

# Get all llm.request events with session.id attribute
response = requests.get(
    "http://localhost:8000/v1/telemetry/events",
    params={
        "event_name": "llm.request",
        "limit": 1000,
        "from_time": "2023-06-01T00:00:00Z"
    }
)

events = response.json()

# Calculate tokens per session
session_tokens = defaultdict(int)
session_counts = defaultdict(int)

for event in events:
    if "attributes" in event and "session.id" in event["attributes"]:
        session_id = event["attributes"]["session.id"]
        token_count = event["attributes"].get("llm.request.tokens", 0)
        session_tokens[session_id] += token_count
        session_counts[session_id] += 1

# Calculate average tokens per session
session_avg_tokens = {
    session_id: tokens / session_counts[session_id]
    for session_id, tokens in session_tokens.items()
}

# Calculate overall average
if session_tokens:
    avg_tokens_per_session = sum(session_tokens.values()) / sum(session_counts.values())
    print(f"Average tokens per session: {avg_tokens_per_session}")
else:
    print("No session data found")
```

## Visualizing Metrics

The Cylestio Local Server API is designed to work well with various visualization tools:

- **Dashboards**: Use the dashboard endpoint with tools like Grafana, Kibana, or custom dashboards
- **Charts**: Use the metrics endpoint to create time series charts
- **Agent Monitoring**: Use the agents endpoint to create agent comparison views

### Example: Creating a Simple Dashboard with Matplotlib

```python
import requests
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime

# Get LLM request count time series
response = requests.get(
    "http://localhost:8000/v1/metrics",
    params={"metric": "llm_request_count", "time_range": "1d", "interval": "1h"}
)
data = response.json()

# Extract timestamps and values
timestamps = [datetime.fromisoformat(point["timestamp"].replace("Z", "+00:00")) 
              for point in data["data"]]
values = [point["value"] for point in data["data"]]

# Create plot
plt.figure(figsize=(12, 6))
plt.plot(timestamps, values, marker='o')
plt.title("LLM Requests Over Time")
plt.xlabel("Time")
plt.ylabel("Request Count")
plt.grid(True)

# Format x-axis dates
plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
plt.gcf().autofmt_xdate()

# Save or show the plot
plt.savefig("llm_requests.png")
plt.show()
```

## Advanced Metric Analysis

For more advanced metric analysis, consider:

1. **Correlation Analysis**: Compare multiple metrics to find relationships
2. **Anomaly Detection**: Identify unusual patterns in metrics
3. **Trend Analysis**: Analyze long-term trends in metrics

These can be implemented by retrieving metrics data and performing analysis in your application. 