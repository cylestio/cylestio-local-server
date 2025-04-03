# Agent Endpoints Guide

This guide provides detailed information about the Agent API endpoints, which are used for retrieving and analyzing information about specific AI agents.

## Agent Data Model

Agents represent the AI assistants or tools being monitored. The agent data model includes:

```json
{
  "agent_id": "agent-123456789",
  "name": "Customer Support Assistant",
  "type": "assistant",
  "status": "active",
  "description": "AI assistant for handling customer support queries",
  "created_at": "2024-03-01T12:00:00.000Z",
  "updated_at": "2024-03-15T14:30:00.000Z",
  "configuration": {
    "model": "claude-3-opus",
    "temperature": 0.7,
    "max_tokens": 4000
  },
  "metrics": {
    "request_count": 12500,
    "token_usage": 1250000,
    "error_count": 125
  }
}
```

- `agent_id`: Unique identifier for the agent
- `name`: Display name of the agent
- `type`: Type of agent (assistant, chatbot, autonomous, function, or other)
- `status`: Current status (active, inactive, paused)
- `description`: Optional description of the agent's purpose
- `created_at`: Timestamp when the agent was created
- `updated_at`: Timestamp when the agent was last updated
- `configuration`: Optional object with agent-specific configuration
- `metrics`: Summary metrics about the agent's activity

## List All Agents

Retrieve a list of all agents with optional filtering and sorting.

**Endpoint**: `GET /v1/agents`

**Query Parameters**:
- `status` (string, optional): Filter by agent status (active, inactive, paused)
- `agent_type` (string, optional): Filter by agent type
- `created_after` (datetime, optional): Filter by creation date
- `page` (integer, default: 1): Page number
- `page_size` (integer, default: 50, max: 1000): Items per page
- `sort_by` (string, default: "created_at"): Field to sort by
- `sort_dir` (string, default: "desc"): Sort direction (asc, desc)

**Response**:
```json
{
  "items": [
    {
      "agent_id": "agent-123456789",
      "name": "Customer Support Assistant",
      "type": "assistant",
      "status": "active",
      "created_at": "2024-03-01T12:00:00.000Z",
      "updated_at": "2024-03-15T14:30:00.000Z",
      "request_count": 12500,
      "token_usage": 1250000,
      "error_count": 125
    },
    {
      "agent_id": "agent-987654321",
      "name": "Data Analysis Tool",
      "type": "function",
      "status": "active",
      "created_at": "2024-02-15T09:00:00.000Z",
      "updated_at": "2024-03-10T11:45:00.000Z",
      "request_count": 8750,
      "token_usage": 875000,
      "error_count": 87
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 50,
    "total_items": 2,
    "total_pages": 1
  },
  "meta": {
    "total_agents": 2,
    "active_agents": 2,
    "inactive_agents": 0
  }
}
```

### Example: Listing Active Agents

```typescript
// Web App Dashboard code example
async function listActiveAgents(page = 1, pageSize = 50) {
  const params = new URLSearchParams({
    status: 'active',
    page: page.toString(),
    page_size: pageSize.toString(),
    sort_by: 'request_count',
    sort_dir: 'desc'
  });

  const response = await fetch(`/v1/agents?${params.toString()}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json'
    }
  });

  return await response.json();
}
```

## Get Agent Details

Retrieve detailed information about a specific agent.

**Endpoint**: `GET /v1/agents/{agent_id}`

**Path Parameters**:
- `agent_id`: Agent ID

**Response**:
```json
{
  "agent_id": "agent-123456789",
  "name": "Customer Support Assistant",
  "type": "assistant",
  "status": "active",
  "description": "AI assistant for handling customer support queries",
  "created_at": "2024-03-01T12:00:00.000Z",
  "updated_at": "2024-03-15T14:30:00.000Z",
  "configuration": {
    "model": "claude-3-opus",
    "temperature": 0.7,
    "max_tokens": 4000
  },
  "metrics": {
    "request_count": 12500,
    "token_usage": 1250000,
    "error_count": 125,
    "avg_response_time": 2350,
    "success_rate": 0.98,
    "cost_estimate": 125.0,
    "session_count": 3500,
    "avg_session_duration": 300,
    "top_tools": [
      {"name": "database_query", "count": 4500},
      {"name": "knowledge_base", "count": 3200},
      {"name": "email_sender", "count": 950}
    ]
  }
}
```

## Get Agent Dashboard Data

Retrieve dashboard metrics for a specific agent over the specified time period.

**Endpoint**: `GET /v1/agents/{agent_id}/dashboard`

**Path Parameters**:
- `agent_id`: Agent ID

**Query Parameters**:
- `time_range` (string, default: "30d"): Time range for metrics ("1h", "1d", "7d", "30d")
- `metrics` (string, optional): Comma-separated list of metrics to include

**Response**:
```json
{
  "agent_id": "agent-123456789",
  "period": "30d",
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

### Example: Showing Agent Dashboard

```typescript
// Web App Dashboard code example
async function showAgentDashboard(agentId, timeRange = '7d') {
  const response = await fetch(`/v1/agents/${agentId}/dashboard?time_range=${timeRange}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json'
    }
  });

  const data = await response.json();
  
  // Render dashboard metrics cards
  const metricsContainer = document.getElementById('agent-metrics');
  metricsContainer.innerHTML = '';
  
  data.metrics.forEach(metric => {
    const card = document.createElement('div');
    card.className = 'metric-card';
    
    const trendClass = metric.trend === 'up' 
      ? (metric.metric.includes('error') ? 'negative' : 'positive')
      : (metric.metric.includes('error') ? 'positive' : 'negative');
    
    card.innerHTML = `
      <h3>${formatMetricName(metric.metric)}</h3>
      <div class="metric-value">${formatMetricValue(metric.metric, metric.value)}</div>
      <div class="metric-change ${trendClass}">
        ${metric.trend === 'up' ? '↑' : '↓'} ${Math.abs(metric.change).toFixed(1)}%
      </div>
    `;
    
    metricsContainer.appendChild(card);
  });
}

// Helper functions
function formatMetricName(metricKey) {
  const parts = metricKey.split('.');
  return parts.map(part => part.charAt(0).toUpperCase() + part.slice(1)).join(' ');
}

function formatMetricValue(metricKey, value) {
  if (metricKey.includes('token')) {
    return value.toLocaleString() + ' tokens';
  } else if (metricKey.includes('count')) {
    return value.toLocaleString();
  } else if (metricKey.includes('rate')) {
    return (value * 100).toFixed(1) + '%';
  }
  return value.toLocaleString();
}
```

## Get LLM Usage for an Agent

Retrieve LLM usage overview for a specific agent.

**Endpoint**: `GET /v1/agents/{agent_id}/llms`

**Path Parameters**:
- `agent_id`: Agent ID

**Query Parameters**:
- `from_time` (datetime, optional): Start time (ISO format)
- `to_time` (datetime, optional): End time (ISO format)
- `time_range` (string, default: "30d"): Predefined time range ("1h", "1d", "7d", "30d")

**Response**:
```json
{
  "items": [
    {
      "model": "claude-3-opus",
      "vendor": "anthropic",
      "request_count": 5000,
      "input_tokens": 500000,
      "output_tokens": 750000,
      "total_tokens": 1250000,
      "estimated_cost": 100.0
    },
    {
      "model": "claude-3-sonnet",
      "vendor": "anthropic",
      "request_count": 7500,
      "input_tokens": 450000,
      "output_tokens": 550000,
      "total_tokens": 1000000,
      "estimated_cost": 60.0
    }
  ],
  "total_requests": 12500,
  "total_tokens": 2250000,
  "total_cost": 160.0,
  "meta": {
    "time_period": "30d",
    "from_time": "2024-03-01T00:00:00.000Z",
    "to_time": "2024-03-31T23:59:59.999Z"
  }
}
```

## Get LLM Requests for an Agent

Retrieve detailed LLM requests for a specific agent.

**Endpoint**: `GET /v1/agents/{agent_id}/llms/requests`

**Path Parameters**:
- `agent_id`: Agent ID

**Query Parameters**:
- `model` (string, optional): Filter by LLM model
- `status` (string, optional): Filter by request status
- `from_time` (datetime, optional): Start time (ISO format)
- `to_time` (datetime, optional): End time (ISO format)
- `time_range` (string, default: "1d"): Predefined time range ("1h", "1d", "7d", "30d")
- `page` (integer, default: 1): Page number
- `page_size` (integer, default: 50): Items per page

**Response**:
```json
{
  "items": [
    {
      "request_id": "req-123456789",
      "timestamp": "2024-03-31T14:30:25.123Z",
      "model": "claude-3-opus",
      "status": "success",
      "input_tokens": 350,
      "output_tokens": 520,
      "duration_ms": 2150,
      "prompt_summary": "Explain the difference between REST and GraphQL",
      "response_summary": "REST is an architectural style for APIs that..."
    },
    {
      "request_id": "req-987654321",
      "timestamp": "2024-03-31T14:15:10.456Z",
      "model": "claude-3-opus",
      "status": "success",
      "input_tokens": 275,
      "output_tokens": 480,
      "duration_ms": 1950,
      "prompt_summary": "Generate sample code to connect to a database",
      "response_summary": "Here's Python code using SQLAlchemy to connect..."
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 50,
    "total_items": 125,
    "total_pages": 3
  },
  "meta": {
    "time_period": "1d",
    "from_time": "2024-03-31T00:00:00.000Z",
    "to_time": "2024-03-31T23:59:59.999Z",
    "filters": {
      "model": null,
      "status": null
    }
  }
}
```

### Example: Viewing Recent LLM Requests

```typescript
// Web App Dashboard code example
async function viewRecentLLMRequests(agentId, timeRange = '1d', page = 1) {
  const params = new URLSearchParams({
    time_range: timeRange,
    page: page.toString(),
    page_size: '50'
  });

  const response = await fetch(`/v1/agents/${agentId}/llms/requests?${params.toString()}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json'
    }
  });

  const data = await response.json();
  
  // Render the requests table
  const table = document.getElementById('llm-requests-table');
  table.innerHTML = `
    <thead>
      <tr>
        <th>Time</th>
        <th>Model</th>
        <th>Status</th>
        <th>Input Tokens</th>
        <th>Output Tokens</th>
        <th>Duration</th>
        <th>Prompt</th>
        <th>Response</th>
      </tr>
    </thead>
    <tbody>
      ${data.items.map(req => `
        <tr>
          <td>${formatDateTime(req.timestamp)}</td>
          <td>${req.model}</td>
          <td class="${req.status === 'success' ? 'success' : 'error'}">${req.status}</td>
          <td>${req.input_tokens.toLocaleString()}</td>
          <td>${req.output_tokens.toLocaleString()}</td>
          <td>${req.duration_ms}ms</td>
          <td title="${escapeHtml(req.prompt_summary)}">${truncate(req.prompt_summary, 50)}</td>
          <td title="${escapeHtml(req.response_summary)}">${truncate(req.response_summary, 50)}</td>
        </tr>
      `).join('')}
    </tbody>
  `;
  
  // Render pagination
  renderPagination(data.pagination, page, pageNum => {
    viewRecentLLMRequests(agentId, timeRange, pageNum);
  });
}

// Helper functions
function formatDateTime(isoString) {
  const date = new Date(isoString);
  return date.toLocaleString();
}

function truncate(str, maxLength) {
  if (!str) return '';
  if (str.length <= maxLength) return str;
  return str.substring(0, maxLength) + '...';
}

function escapeHtml(str) {
  if (!str) return '';
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
```

## Get Token Usage for an Agent

Retrieve token usage metrics for a specific agent.

**Endpoint**: `GET /v1/agents/{agent_id}/tokens`

**Path Parameters**:
- `agent_id`: Agent ID

**Query Parameters**:
- `from_time` (datetime, optional): Start time (ISO format)
- `to_time` (datetime, optional): End time (ISO format)
- `time_range` (string, default: "7d"): Predefined time range ("1h", "1d", "7d", "30d")
- `group_by` (string, optional): Group by field (model, time)
- `interval` (string, default: "1d"): Time interval for grouping ("1h", "1d")
- `page` (integer, default: 1): Page number
- `page_size` (integer, default: 50): Items per page

**Response**:
```json
{
  "items": [
    {
      "timestamp": "2024-03-31T00:00:00.000Z",
      "input_tokens": 35000,
      "output_tokens": 52500,
      "total_tokens": 87500,
      "model": null
    },
    {
      "timestamp": "2024-03-30T00:00:00.000Z",
      "input_tokens": 32500,
      "output_tokens": 48750,
      "total_tokens": 81250,
      "model": null
    }
  ],
  "total_input": 235000,
  "total_output": 352500,
  "total": 587500,
  "pagination": {
    "page": 1,
    "page_size": 50,
    "total_items": 7,
    "total_pages": 1
  },
  "meta": {
    "time_period": "7d",
    "from_time": "2024-03-25T00:00:00.000Z",
    "to_time": "2024-03-31T23:59:59.999Z",
    "group_by": "time",
    "interval": "1d"
  }
}
```

## Get Tool Usage for an Agent

Retrieve tool usage overview for a specific agent.

**Endpoint**: `GET /v1/agents/{agent_id}/tools`

**Path Parameters**:
- `agent_id`: Agent ID

**Query Parameters**:
- `from_time` (datetime, optional): Start time (ISO format)
- `to_time` (datetime, optional): End time (ISO format)
- `time_range` (string, default: "30d"): Predefined time range ("1h", "1d", "7d", "30d")

**Response**:
```json
{
  "items": [
    {
      "tool_name": "database_query",
      "category": "data_access",
      "execution_count": 4500,
      "success_count": 4410,
      "error_count": 90,
      "success_rate": 0.98,
      "avg_duration_ms": 125
    },
    {
      "tool_name": "knowledge_base",
      "category": "data_access",
      "execution_count": 3200,
      "success_count": 3120,
      "error_count": 80,
      "success_rate": 0.975,
      "avg_duration_ms": 350
    },
    {
      "tool_name": "email_sender",
      "category": "communication",
      "execution_count": 950,
      "success_count": 925,
      "error_count": 25,
      "success_rate": 0.974,
      "avg_duration_ms": 275
    }
  ],
  "total_executions": 8650,
  "overall_success_rate": 0.977,
  "meta": {
    "time_period": "30d",
    "from_time": "2024-03-01T00:00:00.000Z",
    "to_time": "2024-03-31T23:59:59.999Z"
  }
}
```

## Get Tool Executions for an Agent

Retrieve detailed tool executions for a specific agent.

**Endpoint**: `GET /v1/agents/{agent_id}/tools/executions`

**Path Parameters**:
- `agent_id`: Agent ID

**Query Parameters**:
- `tool_name` (string, optional): Filter by tool name
- `status` (string, optional): Filter by execution status
- `from_time` (datetime, optional): Start time (ISO format)
- `to_time` (datetime, optional): End time (ISO format)
- `time_range` (string, default: "1d"): Predefined time range ("1h", "1d", "7d", "30d")
- `page` (integer, default: 1): Page number
- `page_size` (integer, default: 50): Items per page

**Response**:
```json
{
  "items": [
    {
      "execution_id": "exec-123456789",
      "timestamp": "2024-03-31T14:35:12.345Z",
      "tool_name": "database_query",
      "status": "success",
      "duration_ms": 135,
      "parameters": {
        "query": "SELECT * FROM users WHERE email = ?",
        "params": ["example@example.com"]
      },
      "result_summary": "Found 1 user matching the email"
    },
    {
      "execution_id": "exec-987654321",
      "timestamp": "2024-03-31T14:32:45.678Z",
      "tool_name": "knowledge_base",
      "status": "success",
      "duration_ms": 325,
      "parameters": {
        "query": "How to reset password",
        "max_results": 3
      },
      "result_summary": "Retrieved 3 knowledge base articles about password reset"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 50,
    "total_items": 285,
    "total_pages": 6
  },
  "meta": {
    "time_period": "1d",
    "from_time": "2024-03-31T00:00:00.000Z",
    "to_time": "2024-03-31T23:59:59.999Z",
    "filters": {
      "tool_name": null,
      "status": null
    }
  }
}
```

## Get Sessions for an Agent

Retrieve sessions for a specific agent.

**Endpoint**: `GET /v1/agents/{agent_id}/sessions`

**Path Parameters**:
- `agent_id`: Agent ID

**Query Parameters**:
- `status` (string, optional): Filter by session status
- `min_duration` (integer, optional): Minimum duration in seconds
- `max_duration` (integer, optional): Maximum duration in seconds
- `from_time` (datetime, optional): Start time (ISO format)
- `to_time` (datetime, optional): End time (ISO format)
- `time_range` (string, default: "7d"): Predefined time range ("1h", "1d", "7d", "30d")
- `page` (integer, default: 1): Page number
- `page_size` (integer, default: 50): Items per page

**Response**:
```json
{
  "items": [
    {
      "session_id": "sess-123456789",
      "start_time": "2024-03-31T14:00:00.000Z",
      "end_time": "2024-03-31T14:15:30.000Z",
      "duration_seconds": 930,
      "event_count": 25,
      "llm_request_count": 8,
      "tool_execution_count": 12,
      "error_count": 0,
      "status": "completed"
    },
    {
      "session_id": "sess-987654321",
      "start_time": "2024-03-31T13:30:00.000Z",
      "end_time": "2024-03-31T13:45:15.000Z",
      "duration_seconds": 915,
      "event_count": 22,
      "llm_request_count": 7,
      "tool_execution_count": 10,
      "error_count": 1,
      "status": "completed"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 50,
    "total_items": 120,
    "total_pages": 3
  },
  "meta": {
    "time_period": "7d",
    "from_time": "2024-03-25T00:00:00.000Z",
    "to_time": "2024-03-31T23:59:59.999Z"
  }
}
```

## Get Traces for an Agent

Retrieve traces for a specific agent.

**Endpoint**: `GET /v1/agents/{agent_id}/traces`

**Path Parameters**:
- `agent_id`: Agent ID

**Query Parameters**:
- `status` (string, optional): Filter by trace status
- `event_type` (string, optional): Filter by initial event type
- `min_duration` (integer, optional): Minimum duration in milliseconds
- `max_duration` (integer, optional): Maximum duration in milliseconds
- `from_time` (datetime, optional): Start time (ISO format)
- `to_time` (datetime, optional): End time (ISO format)
- `time_range` (string, default: "7d"): Predefined time range ("1h", "1d", "7d", "30d")
- `page` (integer, default: 1): Page number
- `page_size` (integer, default: 50): Items per page

**Response**:
```json
{
  "items": [
    {
      "trace_id": "trace-123456789",
      "start_time": "2024-03-31T14:05:12.345Z",
      "end_time": "2024-03-31T14:05:18.765Z",
      "duration_ms": 6420,
      "event_count": 12,
      "status": "completed",
      "initial_event_type": "llm.request"
    },
    {
      "trace_id": "trace-987654321",
      "start_time": "2024-03-31T14:02:34.567Z",
      "end_time": "2024-03-31T14:02:39.876Z",
      "duration_ms": 5309,
      "event_count": 9,
      "status": "completed",
      "initial_event_type": "tool.start"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 50,
    "total_items": 350,
    "total_pages": 7
  },
  "meta": {
    "time_period": "7d",
    "from_time": "2024-03-25T00:00:00.000Z",
    "to_time": "2024-03-31T23:59:59.999Z"
  }
}
```

## Get Security Alerts for an Agent

Retrieve security alerts for a specific agent.

**Endpoint**: `GET /v1/agents/{agent_id}/alerts`

**Path Parameters**:
- `agent_id`: Agent ID

**Query Parameters**:
- `severity` (string, optional): Filter by alert severity
- `type` (string, optional): Filter by alert type
- `status` (string, optional): Filter by alert status
- `from_time` (datetime, optional): Start time (ISO format)
- `to_time` (datetime, optional): End time (ISO format)
- `time_range` (string, default: "7d"): Predefined time range ("1h", "1d", "7d", "30d")
- `page` (integer, default: 1): Page number
- `page_size` (integer, default: 50): Items per page

**Response**:
```json
{
  "items": [
    {
      "alert_id": "alert-123456789",
      "timestamp": "2024-03-31T14:10:22.345Z",
      "type": "prompt_injection",
      "severity": "medium",
      "description": "Potential prompt injection attempt detected",
      "status": "resolved",
      "related_event_id": "evt-123456789"
    },
    {
      "alert_id": "alert-987654321",
      "timestamp": "2024-03-30T15:20:33.456Z",
      "type": "sensitive_data",
      "severity": "high",
      "description": "Potential PII detected in user input",
      "status": "active",
      "related_event_id": "evt-987654321"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 50,
    "total_items": 15,
    "total_pages": 1
  },
  "meta": {
    "time_period": "7d",
    "from_time": "2024-03-25T00:00:00.000Z",
    "to_time": "2024-03-31T23:59:59.999Z"
  }
}
```

## Common Use Cases

### 1. Agent Overview Dashboard

```typescript
// Web App Dashboard code example
async function loadAgentOverview(agentId) {
  // Get agent details
  const agentDetails = await fetch(`/v1/agents/${agentId}`, {
    method: 'GET'
  }).then(res => res.json());
  
  // Get dashboard metrics
  const dashboard = await fetch(`/v1/agents/${agentId}/dashboard?time_range=30d`, {
    method: 'GET'
  }).then(res => res.json());
  
  // Get LLM usage
  const llmUsage = await fetch(`/v1/agents/${agentId}/llms?time_range=30d`, {
    method: 'GET'
  }).then(res => res.json());
  
  // Get tool usage
  const toolUsage = await fetch(`/v1/agents/${agentId}/tools?time_range=30d`, {
    method: 'GET'
  }).then(res => res.json());
  
  // Render agent header
  document.getElementById('agent-name').textContent = agentDetails.name;
  document.getElementById('agent-type').textContent = agentDetails.type;
  document.getElementById('agent-status').textContent = agentDetails.status;
  document.getElementById('agent-created').textContent = 
    new Date(agentDetails.created_at).toLocaleDateString();
  
  // Render metrics cards
  renderMetricCards(dashboard.metrics);
  
  // Render LLM usage chart
  renderLLMUsageChart(llmUsage);
  
  // Render tool usage chart
  renderToolUsageChart(toolUsage);
}
```

### 2. Session Analysis

```typescript
// Web App Dashboard code example
async function analyzeAgentSessions(agentId, timeRange = '7d') {
  // Get all sessions
  const sessions = await fetch(`/v1/agents/${agentId}/sessions?time_range=${timeRange}&page_size=1000`, {
    method: 'GET'
  }).then(res => res.json());
  
  // Calculate statistics
  const sessionCount = sessions.items.length;
  const completedSessions = sessions.items.filter(s => s.status === 'completed').length;
  const completionRate = completedSessions / sessionCount;
  
  const avgDuration = sessions.items.reduce((sum, s) => sum + (s.duration_seconds || 0), 0) / sessionCount;
  const avgLLMRequests = sessions.items.reduce((sum, s) => sum + s.llm_request_count, 0) / sessionCount;
  const avgToolExecutions = sessions.items.reduce((sum, s) => sum + s.tool_execution_count, 0) / sessionCount;
  
  // Group by day
  const sessionsByDay = {};
  sessions.items.forEach(session => {
    const day = new Date(session.start_time).toLocaleDateString();
    sessionsByDay[day] = (sessionsByDay[day] || 0) + 1;
  });
  
  // Render statistics
  renderSessionStats({
    sessionCount,
    completionRate,
    avgDuration,
    avgLLMRequests,
    avgToolExecutions
  });
  
  // Render sessions by day chart
  renderSessionsByDayChart(sessionsByDay);
  
  // Render session list
  renderSessionList(sessions.items.slice(0, 10));
}
```

### 3. Security Monitoring

```typescript
// Web App Dashboard code example
async function monitorAgentSecurity(agentId, timeRange = '30d') {
  // Get security alerts
  const alerts = await fetch(`/v1/agents/${agentId}/alerts?time_range=${timeRange}&page_size=1000`, {
    method: 'GET'
  }).then(res => res.json());
  
  // Group by severity
  const alertsBySeverity = {
    low: alerts.items.filter(a => a.severity === 'low').length,
    medium: alerts.items.filter(a => a.severity === 'medium').length,
    high: alerts.items.filter(a => a.severity === 'high').length
  };
  
  // Group by type
  const alertsByType = {};
  alerts.items.forEach(alert => {
    alertsByType[alert.type] = (alertsByType[alert.type] || 0) + 1;
  });
  
  // Group by status
  const alertsByStatus = {
    active: alerts.items.filter(a => a.status === 'active').length,
    resolved: alerts.items.filter(a => a.status === 'resolved').length
  };
  
  // Get active high-severity alerts
  const highSeverityActiveAlerts = alerts.items.filter(
    a => a.severity === 'high' && a.status === 'active'
  );
  
  // Render alert summary
  renderAlertSummary({
    total: alerts.items.length,
    alertsBySeverity,
    alertsByType,
    alertsByStatus
  });
  
  // Render high-severity active alerts
  renderHighSeverityAlerts(highSeverityActiveAlerts);
}
```

## Best Practices

1. **Cache agent details**: Basic agent information changes infrequently, so cache it to reduce API calls.

2. **Use pagination carefully**: For endpoints that support pagination, ensure you handle pagination properly in your UI. For analytics dashboards, you may need to increase page_size to get all data at once.

3. **Implement proper error handling**: Handle API errors gracefully, especially for user-facing dashboards.

4. **Use filtered queries**: Use the filtering parameters to reduce the amount of data transferred and processed.

5. **Optimize time ranges**: Choose appropriate time ranges based on user needs. For real-time monitoring, use shorter ranges.

6. **Combine related API calls**: Make multiple API calls in parallel when building dashboards that need data from multiple endpoints.

7. **Progressive loading**: Implement progressive loading for dashboards to improve user experience.

## Common Errors and Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| "Agent not found" | Invalid agent_id parameter | Check that the agent ID exists and is correctly formatted |
| "Invalid time range" | Incorrectly formatted time_range parameter | Use one of the supported time ranges: "1h", "1d", "7d", "30d" |
| "Too many items requested" | Requesting too many items per page | Reduce the page_size parameter or implement pagination |
| "Invalid parameter" | Parameter has invalid format or value | Check the parameter format and constraints |

## Schema Reference

For a complete reference of the agent API schemas, including all available fields and their types, see the [API Schema Documentation](../api-schema.md). 