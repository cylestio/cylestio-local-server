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

## LLM Analytics API

The LLM Analytics API provides comprehensive metrics about language model usage in your AI agents.

### LLM Analytics Endpoint

**Endpoint**: `GET /v1/metrics/llm/analytics`

**Query Parameters**:
- `agent_id` (string, optional): Filter by agent ID
- `model_name` (string, optional): Filter by model name
- `from_time` (datetime, optional): Start time (ISO format)
- `to_time` (datetime, optional): End time (ISO format)
- `granularity` (string, default: "day"): Time granularity ("minute", "hour", "day")
- `breakdown_by` (string, default: "none"): Dimension to break down by ("none", "agent", "model", "time")

**Response**:
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
      "key": "gpt-4",
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
      }
    }
  ],
  "from_time": "2023-04-01T00:00:00Z",
  "to_time": "2023-04-30T23:59:59Z",
  "filters": {
    "agent_id": null,
    "model_name": null,
    "from_time": "2023-04-01T00:00:00Z",
    "to_time": "2023-04-30T23:59:59Z",
    "granularity": "day"
  },
  "breakdown_by": "model"
}
```

### LLM Model Comparison Endpoint

**Endpoint**: `GET /v1/metrics/llm/models`

**Query Parameters**:
- `agent_id` (string, optional): Filter by agent ID
- `from_time` (datetime, optional): Start time (ISO format)
- `to_time` (datetime, optional): End time (ISO format)

**Response**: Same format as `/v1/metrics/llm/analytics` with `breakdown_by` set to "model".

### LLM Usage Trends Endpoint

**Endpoint**: `GET /v1/metrics/llm/usage_trends`

**Query Parameters**:
- `agent_id` (string, optional): Filter by agent ID
- `model_name` (string, optional): Filter by model name
- `from_time` (datetime, optional): Start time (ISO format)
- `to_time` (datetime, optional): End time (ISO format)
- `granularity` (string, default: "day"): Time granularity ("minute", "hour", "day")

**Response**: Same format as `/v1/metrics/llm/analytics` with `breakdown_by` set to "time".

### LLM Agent Usage Endpoint

**Endpoint**: `GET /v1/metrics/llm/agent_usage`

**Query Parameters**:
- `model_name` (string, optional): Filter by model name
- `from_time` (datetime, optional): Start time (ISO format)
- `to_time` (datetime, optional): End time (ISO format)

**Response**: Same format as `/v1/metrics/llm/analytics` with `breakdown_by` set to "agent".

### LLM Agent-Model Relationships Endpoint

**Endpoint**: `GET /v1/metrics/llm/agent_model_relationships`

This endpoint provides rich data about which agents used which models, when they were used, and usage statistics. Results can be visualized as histograms, trends, and other charts.

**Query Parameters**:
- `agent_id` (string, optional): Filter by agent ID
- `model_name` (string, optional): Filter by model name
- `from_time` (datetime, optional): Start time (ISO format)
- `to_time` (datetime, optional): End time (ISO format)
- `granularity` (string, default: "day"): Time granularity ("minute", "hour", "day")
- `include_distributions` (boolean, default: false): Whether to include time and token distributions for visualization

**Response**:
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

### Example: Getting Agent-Model Relationship Data

```typescript
// Get relationship between agents and models with time distribution
async function getAgentModelRelationships(agentId = null, includeDistributions = true) {
  const params = new URLSearchParams({
    include_distributions: includeDistributions.toString()
  });
  
  if (agentId) {
    params.append('agent_id', agentId);
  }

  const response = await fetch(`/v1/metrics/llm/agent_model_relationships?${params.toString()}`, {
    method: 'GET'
  });

  return await response.json();
}
```

### Example: Visualizing Agent-Model Relationships

```typescript
// Example usage for rendering model usage per agent
function renderAgentModelUsage(data) {
  // For each breakdown item (agent:model combination)
  data.breakdown.forEach(item => {
    const [agentId, modelName] = item.key.split(':');
    
    // Create a card or section for each agent-model combination
    const card = document.createElement('div');
    card.className = 'agent-model-card';
    
    // Add basic metrics
    card.innerHTML = `
      <h3>${agentId} - ${modelName}</h3>
      <p>Relationship: <strong>${item.relation_type}</strong></p>
      <p>Total requests: ${item.metrics.request_count}</p>
      <p>Total tokens: ${item.metrics.token_count_total}</p>
      <p>Estimated cost: $${item.metrics.estimated_cost_usd.toFixed(2)}</p>
    `;
    
    // If time distribution is included, render a timeline chart
    if (item.time_distribution) {
      const timeChartCanvas = document.createElement('canvas');
      timeChartCanvas.id = `time-chart-${agentId}-${modelName}`;
      card.appendChild(timeChartCanvas);
      
      renderTimelineChart(timeChartCanvas, item.time_distribution);
    }
    
    // If token distribution is included, render a histogram
    if (item.token_distribution) {
      const tokenChartCanvas = document.createElement('canvas');
      tokenChartCanvas.id = `token-chart-${agentId}-${modelName}`;
      card.appendChild(tokenChartCanvas);
      
      renderTokenHistogram(tokenChartCanvas, item.token_distribution);
    }
    
    // Add the card to the page
    document.getElementById('agent-model-container').appendChild(card);
  });
}
```

## Deprecated Endpoints

The following endpoints are now deprecated and have been replaced by the newer, more comprehensive endpoints described above:

### ~~Get LLM Request Count~~ (Deprecated)

**Endpoint**: `GET /v1/metrics/llm/request_count`

Use `/v1/metrics/llm/analytics` instead.

### ~~Get LLM Token Usage~~ (Deprecated)

**Endpoint**: `GET /v1/metrics/llm/token_usage`

Use `/v1/metrics/llm/analytics` instead.

### ~~Get LLM Response Time~~ (Deprecated)

**Endpoint**: `GET /v1/metrics/llm/response_time`

Use `/v1/metrics/llm/analytics` instead.

### ~~Get Aggregated LLM Metrics~~ (Deprecated)

**Endpoint**: `GET /v1/metrics/llms`

Use `/v1/metrics/llm/analytics` instead.

### ~~Get LLM Request Metrics~~ (Deprecated)

**Endpoint**: `GET /v1/metrics/llms/requests`

Use `/v1/metrics/llm/analytics` instead.

### ~~Get Overall Usage Patterns~~ (Deprecated)

**Endpoint**: `GET /v1/metrics/usage`

Use `/v1/metrics/llm/usage_trends` instead.

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