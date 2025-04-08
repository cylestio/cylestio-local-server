# LLM Metrics API Updates

This document provides information about the updated API endpoints for LLM metrics in the Cylestio Local Server.

## Overview of Changes

We've replaced several individual metrics endpoints with more comprehensive ones that provide richer data with flexible breakdowns. The new endpoints support advanced visualization features like histograms and trends.

## New API Endpoints

### 1. GET /v1/metrics/llm/analytics

Get comprehensive LLM usage analytics with optional breakdowns.

**Query Parameters:**
- `agent_id` (optional): Filter by agent ID
- `model_name` (optional): Filter by model name
- `from_time` (optional): Start time in ISO format
- `to_time` (optional): End time in ISO format
- `granularity` (optional, default: "day"): Time granularity (`minute`, `hour`, `day`)
- `breakdown_by` (optional, default: "none"): Dimension to break down by (`none`, `agent`, `model`, `time`)

**Response:**
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

### 2. GET /v1/metrics/llm/models

Get LLM model performance comparison.

**Query Parameters:**
- `agent_id` (optional): Filter by agent ID
- `from_time` (optional): Start time in ISO format
- `to_time` (optional): End time in ISO format

**Response:** Same format as `/v1/metrics/llm/analytics` with `breakdown_by=model`.

### 3. GET /v1/metrics/llm/usage_trends

Get LLM usage trends over time.

**Query Parameters:**
- `agent_id` (optional): Filter by agent ID
- `model_name` (optional): Filter by model name
- `from_time` (optional): Start time in ISO format
- `to_time` (optional): End time in ISO format
- `granularity` (optional): Time granularity (`minute`, `hour`, `day`)

**Response:** Same format as `/v1/metrics/llm/analytics` with `breakdown_by=time`.

### 4. GET /v1/metrics/llm/agent_usage

Get LLM usage by agent.

**Query Parameters:**
- `model_name` (optional): Filter by model name
- `from_time` (optional): Start time in ISO format
- `to_time` (optional): End time in ISO format

**Response:** Same format as `/v1/metrics/llm/analytics` with `breakdown_by=agent`.

### 5. GET /v1/metrics/llm/agent_model_relationships (NEW!)

Get comprehensive agent-model relationship analytics. This endpoint is designed specifically for analyzing which agents use which models, when they use them, and how much they use them.

**Query Parameters:**
- `agent_id` (optional): Filter by agent ID
- `model_name` (optional): Filter by model name
- `from_time` (optional): Start time in ISO format
- `to_time` (optional): End time in ISO format
- `granularity` (optional): Time granularity (`minute`, `hour`, `day`)
- `include_distributions` (optional): Whether to include time and token distributions for visualization (default: false)

**Response:**
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

## Deprecated Endpoints

The following endpoints are now deprecated and should be replaced with the new endpoints:

1. `GET /v1/metrics/llm/request_count` → Use `/v1/metrics/llm/analytics` instead
2. `GET /v1/metrics/llm/token_usage` → Use `/v1/metrics/llm/analytics` instead
3. `GET /v1/metrics/llm/response_time` → Use `/v1/metrics/llm/analytics` instead
4. `GET /v1/metrics/llms` → Use `/v1/metrics/llm/analytics` instead
5. `GET /v1/metrics/llms/requests` → Use `/v1/metrics/llm/analytics` instead
6. `GET /v1/metrics/usage` → Use `/v1/metrics/llm/usage_trends` instead

## Usage Examples

### Getting Agent-Model Relationship Data

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

// Example usage for rendering model usage per agent
function renderAgentModelUsage(data) {
  // For each breakdown item (agent:model combination)
  data.breakdown.forEach(item => {
    const [agentId, modelName] = item.key.split(':');
    
    console.log(`Agent: ${agentId}, Model: ${modelName}`);
    console.log(`Total requests: ${item.metrics.request_count}`);
    console.log(`Total tokens: ${item.metrics.token_count_total}`);
    console.log(`Relationship type: ${item.relation_type}`); // "primary" or "secondary"
    
    // If time distribution is included, render a timeline chart
    if (item.time_distribution) {
      renderTimelineChart(item.time_distribution, `${agentId} - ${modelName} Usage`);
    }
    
    // If token distribution is included, render a histogram
    if (item.token_distribution) {
      renderTokenHistogram(item.token_distribution, `${agentId} - ${modelName} Token Distribution`);
    }
  });
}

// Example function for rendering a timeline chart (using a chart library)
function renderTimelineChart(timeData, title) {
  // Format data for chart library
  const labels = timeData.map(point => new Date(point.timestamp).toLocaleDateString());
  const requestData = timeData.map(point => point.request_count);
  const tokenData = timeData.map(point => point.total_tokens);
  
  // Create and render the chart
  // Example using Chart.js or similar library
  const chart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [
        {
          label: 'Requests',
          data: requestData,
          borderColor: 'blue'
        },
        {
          label: 'Tokens',
          data: tokenData,
          borderColor: 'green'
        }
      ]
    },
    options: {
      title: {
        display: true,
        text: title
      }
    }
  });
}

// Example function for rendering a token histogram
function renderTokenHistogram(tokenData, title) {
  // Format data for chart library
  const labels = tokenData.map(bucket => bucket.bucket_range);
  const data = tokenData.map(bucket => bucket.request_count);
  
  // Create and render the chart
  // Example using Chart.js or similar library
  const chart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [
        {
          label: 'Request Count',
          data: data,
          backgroundColor: 'purple'
        }
      ]
    },
    options: {
      title: {
        display: true,
        text: title
      }
    }
  });
}
```

## Migration Guide

When migrating from the old endpoints to the new ones, follow these guidelines:

1. **For basic metrics retrieval:**
   - Replace `/v1/metrics/llm/request_count` with `/v1/metrics/llm/analytics`
   - The new endpoint includes all metrics in a single call

2. **For time series data:**
   - Replace `/v1/metrics/llm/token_usage` with `/v1/metrics/llm/usage_trends`
   - Set `granularity` parameter to control time resolution

3. **For model comparison:**
   - Replace `/v1/metrics/llms` with `/v1/metrics/llm/models`

4. **For agent-specific metrics:**
   - Use `/v1/metrics/llm/agent_usage` or filter other endpoints with `agent_id`

5. **For agent-model relationship analysis:**
   - Use the new `/v1/metrics/llm/agent_model_relationships` endpoint
   - Enable `include_distributions` for rich visualization data

## Additional Notes

- The new endpoints provide more comprehensive metrics in a single call
- All endpoints use consistent parameter naming and response structures
- Time-based data can be visualized as trends, histograms, and other chart types
- The agent-model relationship endpoint provides unique insights into which models are used by which agents

For any questions or issues, please contact the API development team. 