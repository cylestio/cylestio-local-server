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

### Get Tool Execution Count

Get tool execution count metrics with optional filtering and grouping.

**Endpoint**: `GET /v1/metrics/tool/execution_count`

**Query Parameters**:
Similar to LLM metrics endpoints (see above)

**Response**:
```json
{
  "metric": "tool.execution_count",
  "from_time": "2024-03-01T00:00:00.000Z",
  "to_time": "2024-03-31T23:59:59.999Z",
  "interval": "1d",
  "data": [
    {
      "timestamp": "2024-03-01T00:00:00.000Z",
      "value": 287
    },
    {
      "timestamp": "2024-03-02T00:00:00.000Z",
      "value": 312
    }
  ]
}
```

### Get Tool Success Rate

Get tool success rate metrics with optional filtering and grouping.

**Endpoint**: `GET /v1/metrics/tool/success_rate`

**Query Parameters**:
Similar to LLM metrics endpoints (see above)

**Response**:
```json
{
  "metric": "tool.success_rate",
  "from_time": "2024-03-01T00:00:00.000Z",
  "to_time": "2024-03-31T23:59:59.999Z",
  "interval": "1d",
  "data": [
    {
      "timestamp": "2024-03-01T00:00:00.000Z",
      "value": 0.95  // 95% success rate
    },
    {
      "timestamp": "2024-03-02T00:00:00.000Z",
      "value": 0.97  // 97% success rate
    }
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

### Get Tool Usage Analytics

Get aggregated tool usage analytics across all agents.

**Endpoint**: `GET /v1/metrics/tools`

**Query Parameters**:
- `from_time` (datetime, optional): Start time (ISO format)
- `to_time` (datetime, optional): End time (ISO format)
- `time_range` (string, default: "30d"): Predefined time range ("1h", "1d", "7d", "30d")
- `interval` (string, optional): Aggregation interval ("1m", "1h", "1d", "7d")
- `group_by` (string, default: "tool.name"): Dimension to group by

**Response**:
```json
{
  "metric": "tool.usage",
  "from_time": "2024-03-01T00:00:00.000Z",
  "to_time": "2024-03-31T23:59:59.999Z",
  "interval": null,
  "data": [
    {
      "dimensions": {
        "tool.name": "database_query"
      },
      "executions": 3750,
      "success_count": 3675,
      "error_count": 75,
      "success_rate": 0.98,
      "avg_duration_ms": 120
    },
    {
      "dimensions": {
        "tool.name": "web_search"
      },
      "executions": 2500,
      "success_count": 2375,
      "error_count": 125,
      "success_rate": 0.95,
      "avg_duration_ms": 850
    },
    {
      "dimensions": {
        "tool.name": "file_operation"
      },
      "executions": 2000,
      "success_count": 1940,
      "error_count": 60,
      "success_rate": 0.97,
      "avg_duration_ms": 75
    }
  ],
  "totals": {
    "executions": 8250,
    "success_rate": 0.97
  }
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
  const llmUsage = await fetch(`/v1/agents/${agentId}/llms`, {
    method: 'GET'
  }).then(res => res.json());
  
  // Get tool executions
  const toolUsage = await fetch(`/v1/agents/${agentId}/tools`, {
    method: 'GET'
  }).then(res => res.json());
  
  // Get error trend
  const errors = await fetch(`/v1/metrics/error/count?agent_id=${agentId}&interval=1d`, {
    method: 'GET'
  }).then(res => res.json());
  
  // Render agent performance dashboard
  renderAgentDashboard({
    metrics: dashboard.metrics,
    llmUsage,
    toolUsage,
    errors
  });
}
```

### 3. Cost Analysis

```typescript
async function analyzeCosts(timeRange = '30d') {
  // Get LLM usage by model
  const modelUsage = await fetch(`/v1/metrics/llms?time_range=${timeRange}`, {
    method: 'GET'
  }).then(res => res.json());
  
  // Get cost trend over time
  const costTrend = await fetch(`/v1/metrics/tokens?interval=1d&time_range=${timeRange}`, {
    method: 'GET'
  }).then(res => res.json());
  
  // Get top agents by cost
  const agentCosts = await fetch(`/v1/metrics/llms?dimensions=agent_id&time_range=${timeRange}`, {
    method: 'GET'
  }).then(res => res.json());
  
  // Calculate cost metrics
  const totalCost = modelUsage.totals.estimated_cost;
  const avgDailyCost = totalCost / (timeRange === '30d' ? 30 : timeRange === '7d' ? 7 : 1);
  const costPerAgent = agentCosts.data.map(d => ({
    agent: d.dimensions.agent_id,
    cost: d.estimated_cost
  })).sort((a, b) => b.cost - a.cost);
  
  // Render cost analysis dashboard
  renderCostAnalysis({
    totalCost,
    avgDailyCost,
    costByModel: modelUsage.data,
    costPerAgent,
    costTrend: costTrend.data
  });
}
```

## Best Practices

1. **Use the right time range**: For real-time monitoring, use shorter time ranges. For trend analysis, use longer time ranges.

2. **Choose appropriate intervals**: Match the interval to the time range for meaningful aggregations:
   - 1h → 1m intervals
   - 1d → 1h intervals
   - 7d → 6h or 1d intervals
   - 30d → 1d intervals

3. **Use dimensions effectively**: Group by dimensions that provide meaningful insights:
   - `llm.model` for model performance comparison
   - `agent_id` for agent performance comparison
   - `tool.name` for tool usage analysis

4. **Cache expensive queries**: Some aggregated metrics can be expensive to compute. Cache results for frequently accessed dashboards.

5. **Implement progressive loading**: Load summary metrics first, then detailed charts to improve dashboard responsiveness.

6. **Use relative time ranges**: Instead of hard-coding timestamps, use relative time ranges ("1h", "1d", "7d", "30d") for reusable components.

7. **Combine metrics appropriately**: Use multiple endpoints to build comprehensive dashboards.

## Common Errors and Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| "Invalid time range format" | Incorrectly formatted time range | Use one of the supported time ranges: "1h", "1d", "7d", "30d" |
| "Invalid interval" | Unsupported aggregation interval | Use one of the supported intervals: "1m", "1h", "1d", "7d" |
| "Too many dimensions" | Too many grouping dimensions | Limit dimensions to 1-3 for best performance |
| "Date range too large" | Requesting too much data | Use a smaller time range or larger interval |

## Schema Reference

For a complete reference of the metrics API schemas, including all available metrics and dimensions, see the [API Schema Documentation](../api-schema.md). 