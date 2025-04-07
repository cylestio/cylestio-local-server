# Metrics Endpoints Guide

This guide provides detailed information about the Metrics API endpoints, which are used for retrieving aggregated metrics, analytics, and insights about AI agent operations.

## Metrics Format

All metrics responses follow a standard format:

```json
{
  "metric": "metric.name",
  "from_time": "2024-03-01T00:00:00.000Z",
  "to_time": "2024-03-31T23:59:59.999Z",
  "interval": "1d",
  "data": [
    {
      "timestamp": "2024-03-01T00:00:00.000Z",
      "value": 42,
      "dimensions": {
        "dimension1": "value1"
      }
    },
    {
      "timestamp": "2024-03-02T00:00:00.000Z",
      "value": 57,
      "dimensions": {
        "dimension1": "value1"
      }
    }
  ]
}
```

- `metric`: Name of the metric
- `from_time`: Start time of the data range in ISO 8601 format
- `to_time`: End time of the data range in ISO 8601 format
- `interval`: Aggregation interval (e.g., "1m", "1h", "1d", "7d")
- `data`: Array of data points, each containing:
  - `timestamp`: Timestamp of the data point
  - `value`: Numeric value of the metric
  - `dimensions`: Optional key-value pairs for multi-dimensional metrics

## Common Parameters

Most metrics endpoints support these common parameters:

- `agent_id`: Filter by agent ID
- `from_time`: Start time in ISO format (e.g., "2024-03-01T00:00:00Z")
- `to_time`: End time in ISO format
- `time_range`: Predefined time range ("1h", "1d", "7d", "30d")
- `interval`: Aggregation interval ("1m", "1h", "1d", "7d")
- `dimensions`: Comma-separated list of dimensions to group by

You typically use either (`from_time` AND `to_time`) OR `time_range`, but not both.

## Dashboard Metrics

Get key system-wide metrics for the dashboard with trend information.

**Endpoint**: `GET /v1/dashboard`

**Query Parameters**:
- `agent_id` (string, optional): Filter by agent ID
- `time_range` (string, default: "30d"): Time range for metrics ("1h", "1d", "7d", "30d")
- `metrics` (string, optional): Comma-separated list of metrics to include

**Response**:
```json
{
  "period": "30d",
  "time_range": "30d",
  "from_time": "2024-03-01T00:00:00.000Z",
  "to_time": "2024-03-31T23:59:59.999Z",
  "agent_id": null,
  "metrics": [
    {
      "metric": "llm.request_count",
      "value": 12500,
      "change": 15.2,
      "trend": "up"
    },
    {
      "metric": "llm.token_usage",
      "value": 1250000,
      "change": 10.5,
      "trend": "up"
    },
    {
      "metric": "tool.execution_count",
      "value": 8750,
      "change": -5.3,
      "trend": "down"
    },
    {
      "metric": "error.count",
      "value": 125,
      "change": -12.0,
      "trend": "down"
    },
    {
      "metric": "session.count",
      "value": 3500,
      "change": 8.7,
      "trend": "up"
    }
  ]
}
```

### Example: Fetching Dashboard Metrics

```typescript
// Web App Dashboard code example
async function getDashboardMetrics(timeRange = '30d', agentId = null) {
  const params = new URLSearchParams({
    time_range: timeRange
  });
  
  if (agentId) {
    params.append('agent_id', agentId);
  }

  const response = await fetch(`/v1/dashboard?${params.toString()}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json'
    }
  });

  return await response.json();
}
```

## LLM Metrics

### Get LLM Request Count

Get LLM request count metrics with optional filtering and grouping.

**Endpoint**: `GET /v1/metrics/llm/request_count`

**Query Parameters**:
- `agent_id` (string, optional): Filter by agent ID
- `from_time` (datetime, optional): Start time (ISO format)
- `to_time` (datetime, optional): End time (ISO format)
- `time_range` (string, default: "30d"): Predefined time range ("1h", "1d", "7d", "30d")
- `interval` (string, optional): Aggregation interval ("1m", "1h", "1d", "7d")
- `dimensions` (string, optional): Comma-separated list of dimensions to group by

**Response**:
```json
{
  "metric": "llm.request_count",
  "from_time": "2024-03-01T00:00:00.000Z",
  "to_time": "2024-03-31T23:59:59.999Z",
  "interval": "1d",
  "data": [
    {
      "timestamp": "2024-03-01T00:00:00.000Z",
      "value": 425
    },
    {
      "timestamp": "2024-03-02T00:00:00.000Z",
      "value": 387
    }
  ]
}
```

### Example: Grouped LLM Request Count by Model

```typescript
// Web App Dashboard code example
async function getLLMRequestCountByModel(timeRange = '7d') {
  const params = new URLSearchParams({
    time_range: timeRange,
    interval: '1d',
    dimensions: 'llm.model'
  });

  const response = await fetch(`/v1/metrics/llm/request_count?${params.toString()}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json'
    }
  });

  const data = await response.json();
  
  // Restructure data for chart visualization
  const models = [...new Set(data.data.map(d => d.dimensions['llm.model']))];
  const timestamps = [...new Set(data.data.map(d => d.timestamp))];
  
  const chartData = {
    labels: timestamps.map(ts => new Date(ts).toLocaleDateString()),
    datasets: models.map(model => ({
      label: model,
      data: timestamps.map(ts => {
        const point = data.data.find(d => 
          d.timestamp === ts && 
          d.dimensions['llm.model'] === model
        );
        return point ? point.value : 0;
      })
    }))
  };
  
  return chartData;
}
```

### Get LLM Token Usage

Get LLM token usage metrics with optional filtering and grouping.

**Endpoint**: `GET /v1/metrics/llm/token_usage`

**Query Parameters**:
Similar to request_count endpoint (see above)

**Response**:
```json
{
  "metric": "llm.token_usage",
  "from_time": "2024-03-01T00:00:00.000Z",
  "to_time": "2024-03-31T23:59:59.999Z",
  "interval": "1d",
  "data": [
    {
      "timestamp": "2024-03-01T00:00:00.000Z",
      "value": 42500
    },
    {
      "timestamp": "2024-03-02T00:00:00.000Z",
      "value": 38700
    }
  ]
}
```

### Get LLM Response Time

Get LLM response time metrics with optional filtering and grouping.

**Endpoint**: `GET /v1/metrics/llm/response_time`

**Query Parameters**:
Similar to request_count endpoint (see above)

**Response**:
```json
{
  "metric": "llm.response_time",
  "from_time": "2024-03-01T00:00:00.000Z",
  "to_time": "2024-03-31T23:59:59.999Z",
  "interval": "1d",
  "data": [
    {
      "timestamp": "2024-03-01T00:00:00.000Z",
      "value": 2350  // milliseconds
    },
    {
      "timestamp": "2024-03-02T00:00:00.000Z",
      "value": 2480  // milliseconds
    }
  ]
}
```

## Tool Metrics

### Get Comprehensive Tool Interaction Data

Get detailed information about tool interactions with rich filtering, sorting and pagination.

**Endpoint**: `GET /v1/metrics/tool_interactions`

**Query Parameters**:
- `agent_id` (string, optional): Filter by agent ID
- `from_time` (datetime, optional): Start time (ISO format)
- `to_time` (datetime, optional): End time (ISO format)
- `time_range` (string, default: "30d"): Predefined time range (1h, 1d, 7d, 30d)
- `tool_name` (string, optional): Filter by specific tool name
- `tool_status` (string, optional): Filter by execution status (success, error, pending)
- `framework_name` (string, optional): Filter by framework name
- `interaction_type` (string, optional): Filter by interaction type (execution, result)
- `sort_by` (string, default: "request_timestamp"): Field to sort by
- `sort_dir` (string, default: "desc"): Sort direction (asc, desc)
- `page` (integer, default: 1): Page number
- `page_size` (integer, default: 20, max: 100): Page size

**Response**:
```json
{
  "total": 145,
  "page": 1,
  "page_size": 20,
  "from_time": "2024-03-01T00:00:00.000Z",
  "to_time": "2024-03-31T23:59:59.999Z",
  "interactions": [
    {
      "id": 123,
      "event_id": 456,
      "tool_name": "web_search",
      "interaction_type": "execution",
      "status": "success",
      "status_code": 200,
      "parameters": {
        "query": "weather in San Francisco",
        "limit": 5
      },
      "result": {
        "temperature": "72°F",
        "conditions": "Sunny"
      },
      "error": null,
      "request_timestamp": "2024-03-15T14:30:00.000Z",
      "response_timestamp": "2024-03-15T14:30:01.250Z",
      "duration_ms": 1250,
      "framework_name": "langchain",
      "tool_version": "1.2.3",
      "authorization_level": "user",
      "execution_time_ms": 1150,
      "cache_hit": false,
      "api_version": "v2",
      "raw_attributes": {
        "tool.name": "web_search",
        "tool.params": {"query": "weather in San Francisco", "limit": 5},
        "framework.name": "langchain"
      },
      "span_id": "span123",
      "trace_id": "trace456",
      "agent_id": "agent789"
    },
    // More interactions...
  ]
}
```

## Error Metrics

### Get Error Count

Get error count metrics with optional filtering and grouping.

**Endpoint**: `GET /v1/metrics/error/count`

**Query Parameters**:
Similar to LLM metrics endpoints (see above)

**Response**:
```json
{
  "metric": "error.count",
  "from_time": "2024-03-01T00:00:00.000Z",
  "to_time": "2024-03-31T23:59:59.999Z",
  "interval": "1d",
  "data": [
    {
      "timestamp": "2024-03-01T00:00:00.000Z",
      "value": 15
    },
    {
      "timestamp": "2024-03-02T00:00:00.000Z",
      "value": 9
    }
  ]
}
```

## Session Metrics

### Get Session Count

Get session count metrics with optional filtering and grouping.

**Endpoint**: `GET /v1/metrics/session/count`

**Query Parameters**:
Similar to LLM metrics endpoints (see above)

**Response**:
```json
{
  "metric": "session.count",
  "from_time": "2024-03-01T00:00:00.000Z",
  "to_time": "2024-03-31T23:59:59.999Z",
  "interval": "1d",
  "data": [
    {
      "timestamp": "2024-03-01T00:00:00.000Z",
      "value": 127
    },
    {
      "timestamp": "2024-03-02T00:00:00.000Z",
      "value": 135
    }
  ]
}
```

## Agent-Specific Metrics

### Get All Metrics for a Specific Agent

Get all metrics for a specific agent.

**Endpoint**: `GET /v1/metrics/agent/{agent_id}`

**Path Parameters**:
- `agent_id`: Agent ID to get metrics for

**Query Parameters**:
- `time_range` (string, default: "30d"): Time range for the metrics

**Response**:
```json
{
  "agent_id": "agent-123456789",
  "time_range": "30d",
  "llm": {
    "request_count": 3250,
    "token_usage": 325000,
    "response_time_avg": 2150,
    "models": [
      {"name": "claude-3-opus", "requests": 1500, "tokens": 180000},
      {"name": "claude-3-sonnet", "requests": 1750, "tokens": 145000}
    ]
  },
  "tools": {
    "execution_count": 2750,
    "success_rate": 0.96,
    "top_tools": [
      {"name": "database_query", "count": 1200, "success_rate": 0.98},
      {"name": "web_search", "count": 950, "success_rate": 0.95},
      {"name": "file_operation", "count": 600, "success_rate": 0.94}
    ]
  },
  "errors": {
    "count": 87,
    "by_type": [
      {"type": "api_error", "count": 45},
      {"type": "validation_error", "count": 27},
      {"type": "timeout", "count": 15}
    ]
  },
  "sessions": {
    "count": 875,
    "avg_duration": 320,  // seconds
    "avg_events": 12.5
  }
}
```

## System-Wide Aggregated Metrics

### Get Aggregated LLM Usage Metrics

Get aggregated LLM usage metrics across all agents, with breakdown by model.

**Endpoint**: `GET /v1/metrics/llms`

**Query Parameters**:
- `from_time` (datetime, optional): Start time (ISO format)
- `to_time` (datetime, optional): End time (ISO format)
- `time_range` (string, default: "30d"): Predefined time range ("1h", "1d", "7d", "30d")
- `interval` (string, optional): Aggregation interval ("1m", "1h", "1d", "7d")
- `dimensions` (string, default: "llm.model"): Comma-separated list of dimensions to group by

**Response**:
```json
{
  "metric": "llm.usage",
  "from_time": "2024-03-01T00:00:00.000Z",
  "to_time": "2024-03-31T23:59:59.999Z",
  "interval": null,
  "data": [
    {
      "dimensions": {
        "llm.model": "claude-3-opus"
      },
      "requests": 5250,
      "input_tokens": 525000,
      "output_tokens": 1050000,
      "total_tokens": 1575000,
      "avg_response_time": 2450,
      "estimated_cost": 126.0
    },
    {
      "dimensions": {
        "llm.model": "claude-3-sonnet"
      },
      "requests": 7250,
      "input_tokens": 580000,
      "output_tokens": 870000,
      "total_tokens": 1450000,
      "avg_response_time": 1850,
      "estimated_cost": 87.0
    }
  ],
  "totals": {
    "requests": 12500,
    "total_tokens": 3025000,
    "estimated_cost": 213.0
  }
}
```

### Example: Creating a Token Usage Dashboard

```typescript
// Web App Dashboard code example
async function createTokenUsageDashboard() {
  // Get aggregated usage by model
  const modelData = await fetch('/v1/metrics/llms', {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' }
  }).then(res => res.json());
  
  // Get usage over time
  const timeData = await fetch('/v1/metrics/tokens?group_by=time&interval=1d', {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' }
  }).then(res => res.json());
  
  // Render model breakdown pie chart
  renderPieChart({
    labels: modelData.data.map(d => d.dimensions['llm.model']),
    data: modelData.data.map(d => d.total_tokens)
  });
  
  // Render time series chart
  renderLineChart({
    labels: timeData.data.map(d => new Date(d.timestamp).toLocaleDateString()),
    datasets: [{
      label: 'Input Tokens',
      data: timeData.data.map(d => d.input_tokens)
    }, {
      label: 'Output Tokens',
      data: timeData.data.map(d => d.output_tokens)
    }]
  });
  
  // Render cost summary card
  renderCostCard({
    total: modelData.totals.estimated_cost,
    breakdown: modelData.data.map(d => ({
      model: d.dimensions['llm.model'],
      cost: d.estimated_cost
    }))
  });
}
```

## Common Use Cases

### 1. Creating a System Dashboard

```typescript
async function createSystemDashboard() {
  // Get main dashboard metrics
  const dashboard = await fetch('/v1/dashboard', {
    method: 'GET'
  }).then(res => res.json());
  
  // Get LLM request trend over time
  const llmRequests = await fetch('/v1/metrics/llm/request_count?interval=1d', {
    method: 'GET'
  }).then(res => res.json());
  
  // Get token usage by model
  const tokenUsage = await fetch('/v1/metrics/llms', {
    method: 'GET'
  }).then(res => res.json());
  
  // Get tool success rates
  const toolRates = await fetch('/v1/metrics/tools', {
    method: 'GET'
  }).then(res => res.json());
  
  // Render components
  renderMetricCards(dashboard.metrics);
  renderTimeSeriesChart('llm-requests', llmRequests);
  renderModelBreakdownChart('token-usage', tokenUsage);
  renderToolSuccessChart('tool-success', toolRates);
}
```

### 2. Monitoring Agent Performance

```typescript
async function monitorAgentPerformance(agentId) {
  // Get agent dashboard
  const dashboard = await fetch(`/v1/agents/${agentId}/dashboard`, {
    method: 'GET'
  }).then(res => res.json());
  
  // Get LLM usage
  const llmUsage = await fetch(`