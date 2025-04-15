# LLM Metrics Endpoints Guide

This guide provides detailed documentation for all LLM-related API endpoints in the Cylestio Local Server, designed for UI developers to implement monitoring, analytics, and debugging screens.

## Table of Contents

- [Overview](#overview)
- [Common Parameters](#common-parameters)
- [Response Formats](#response-formats)
- [LLM Analytics API](#llm-analytics-api)
  - [LLM Analytics Overview](#llm-analytics-overview)
  - [LLM Usage Trends](#llm-usage-trends)
  - [LLM Agent Usage](#llm-agent-usage)
  - [LLM Model Comparison](#llm-model-comparison)
  - [Agent-Model Relationships](#agent-model-relationships)
- [LLM Conversation Explorer API](#llm-conversation-explorer-api)
  - [List Conversations](#list-conversations)
  - [Conversation Details](#conversation-details)
  - [List LLM Requests](#list-llm-requests)
  - [LLM Request Details](#llm-request-details)
- [Basic LLM Metrics API](#basic-llm-metrics-api)
  - [LLM Request Metrics](#llm-request-metrics)
  - [LLM Token Usage Metrics](#llm-token-usage-metrics)
- [Deprecated Endpoints](#deprecated-endpoints)
- [UI Implementation Examples](#ui-implementation-examples)
  - [Analytics Dashboard](#analytics-dashboard)
  - [Conversation Explorer](#conversation-explorer)
  - [Model Comparison View](#model-comparison-view)

## Overview

The LLM Metrics API provides comprehensive data about language model operations across your AI agents. These endpoints enable you to:

- Monitor LLM usage, performance, and costs over time
- Compare different models and agents
- Explore detailed conversation history
- Debug individual LLM requests
- Analyze usage patterns and trends

## Common Parameters

Most LLM metrics endpoints support these common parameters:

| Parameter | Type | Description |
|-----------|------|-------------|
| `agent_id` | string | Filter by agent ID |
| `from_time` | datetime | Start time in ISO format (e.g., "2023-09-01T00:00:00Z") |
| `to_time` | datetime | End time in ISO format |
| `time_range` | string | Predefined time range ("1h", "1d", "7d", "30d") |
| `interval` | string | Aggregation interval ("1m", "1h", "1d", "7d") |
| `granularity` | string | Time granularity ("minute", "hour", "day") |

You typically use either (`from_time` AND `to_time`) OR `time_range`, but not both.

## Response Formats

### LLM Metrics Response Format

The standard metrics response format includes aggregated stats and optional breakdowns:

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

### Pagination Format

List endpoints use this pagination format:

```json
{
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 60,
    "total_pages": 3,
    "has_next": true,
    "has_prev": false
  }
}
```

## LLM Analytics API

### LLM Analytics Overview

**Endpoint**: `GET /v1/metrics/llm/analytics`

**Description**: Comprehensive analytics for LLM usage with flexible breakdowns.

**Query Parameters**:
- `agent_id` (string, optional): Filter by agent ID
- `model_name` (string, optional): Filter by model name
- `from_time` (datetime, optional): Start time (ISO format)
- `to_time` (datetime, optional): End time (ISO format)
- `granularity` (string, default: "day"): Time granularity ("minute", "hour", "day")
- `breakdown_by` (string, default: "none"): Dimension to break down by ("none", "agent", "model", "time")

**Response**: See [LLM Metrics Response Format](#llm-metrics-response-format)

### LLM Usage Trends

**Endpoint**: `GET /v1/metrics/llm/usage_trends`

**Description**: Shows LLM usage trends over time with flexible time granularity.

**Query Parameters**:
- `agent_id` (string, optional): Filter by agent ID
- `model_name` (string, optional): Filter by model name
- `from_time` (datetime, optional): Start time (ISO format)
- `to_time` (datetime, optional): End time (ISO format)
- `granularity` (string, default: "day"): Time granularity ("minute", "hour", "day")

**Response**: Same format as LLM Analytics with `breakdown_by` set to "time".

**Example Response**:
```json
{
  "total": {
    "request_count": 53,
    "response_time_avg": 1433.11,
    "response_time_p95": 2796.0,
    "success_rate": 0.66,
    "error_rate": 0.26,
    "token_count_input": 30017,
    "token_count_output": 3773,
    "token_count_total": 33790,
    "estimated_cost_usd": 0.036,
    "first_seen": "2023-04-09T18:37:07.099123",
    "last_seen": "2023-04-12T13:30:06.956871"
  },
  "breakdown": [
    {
      "key": "2023-04-09",
      "metrics": {
        "request_count": 42,
        "response_time_avg": 1432.48,
        "response_time_p95": 2864.95,
        "success_rate": 0.67,
        "error_rate": 0.24,
        "token_count_input": 21334,
        "token_count_output": 2960,
        "token_count_total": 24294,
        "estimated_cost_usd": 0.024,
        "first_seen": null,
        "last_seen": null
      }
    },
    {
      "key": "2023-04-10",
      "metrics": {
        "request_count": 6,
        "response_time_avg": 1512.33,
        "response_time_p95": 3024.67,
        "success_rate": 0.67,
        "error_rate": 0.33,
        "token_count_input": 3796,
        "token_count_output": 378,
        "token_count_total": 4174,
        "estimated_cost_usd": 0.004,
        "first_seen": null,
        "last_seen": null
      }
    }
  ],
  "from_time": "2023-03-16T13:09:10.352454",
  "to_time": "2023-04-15T13:09:10.352483",
  "filters": {
    "agent_id": "weather-agent",
    "model_name": null,
    "from_time": "2023-03-16T13:09:10.352454",
    "to_time": "2023-04-15T13:09:10.352483",
    "granularity": "day"
  },
  "breakdown_by": "time"
}
```

### LLM Agent Usage

**Endpoint**: `GET /v1/metrics/llm/agent_usage`

**Description**: Get LLM usage broken down by agent, showing which agents are using LLMs the most.

**Query Parameters**:
- `model_name` (string, optional): Filter by model name
- `from_time` (datetime, optional): Start time (ISO format)
- `to_time` (datetime, optional): End time (ISO format)

**Response**: Same format as LLM Analytics with `breakdown_by` set to "agent".

### LLM Model Comparison

**Endpoint**: `GET /v1/metrics/llm/models`

**Description**: Compare different LLM models' performance metrics.

**Query Parameters**:
- `agent_id` (string, optional): Filter by agent ID
- `from_time` (datetime, optional): Start time (ISO format)
- `to_time` (datetime, optional): End time (ISO format)

**Response**: Same format as LLM Analytics with `breakdown_by` set to "model".

### Agent-Model Relationships

**Endpoint**: `GET /v1/metrics/llm/agent_model_relationships`

**Description**: Rich data about which agents used which models, when they were used, and usage statistics.

**Query Parameters**:
- `agent_id` (string, optional): Filter by agent ID
- `model_name` (string, optional): Filter by model name
- `from_time` (datetime, optional): Start time (ISO format)
- `to_time` (datetime, optional): End time (ISO format)
- `granularity` (string, default: "day"): Time granularity ("minute", "hour", "day")
- `include_distributions` (boolean, default: false): Whether to include time and token distributions for visualization

**Response**: Extended LLM Metrics response with additional distribution data.

**Example Response**:
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

## LLM Conversation Explorer API

The LLM Conversation Explorer API provides access to the conversations and individual LLM requests across your AI agents, enabling you to explore conversation history, analyze interactions, and debug issues.

### List Conversations

**Endpoint**: `GET /v1/metrics/llm/conversations`

**Description**: Lists all LLM conversations, with optional filtering by agent or model.

**Query Parameters**:
- `agent_id` (string, optional): Filter conversations by agent ID
- `model` (string, optional): Filter conversations by model name
- `from_time` (datetime, optional): Start time (ISO format)
- `to_time` (datetime, optional): End time (ISO format)
- `page` (integer, default: 1): Page number for pagination
- `page_size` (integer, default: 20): Number of items per page

**Response**:
```json
{
  "items": [
    {
      "trace_id": "44f5da24d41e94565ed61ca72eae0f6b",
      "agent_id": "weather-agent",
      "agent_name": "Weather Agent",
      "first_timestamp": "2023-04-09T19:46:39.397602",
      "last_timestamp": "2023-04-09T19:47:04.156019",
      "request_count": 7,
      "total_tokens": 1120,
      "user_messages": 3,
      "assistant_messages": 4,
      "summary": "hi"
    },
    {
      "trace_id": "c9b30c3c7570430e96689ef917269e46",
      "agent_id": "weather-agent",
      "agent_name": "Weather Agent",
      "first_timestamp": "2023-04-12T13:29:44.703782",
      "last_timestamp": "2023-04-12T13:30:06.956871",
      "request_count": 5,
      "total_tokens": 4750,
      "user_messages": 2,
      "assistant_messages": 3,
      "summary": "any alerts in nyc?"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 2,
    "total_pages": 1,
    "has_next": false,
    "has_prev": false
  }
}
```

### Conversation Details

**Endpoint**: `GET /v1/metrics/llm/conversations/{trace_id}`

**Description**: Retrieves detailed information about a specific conversation, including all messages exchanged.

**Path Parameters**:
- `trace_id`: The unique trace ID of the conversation to retrieve

**Query Parameters**:
- `page` (integer, default: 1): Page number for pagination
- `page_size` (integer, default: 50): Number of messages per page

**Response**:
```json
{
  "items": [
    {
      "id": "211_73",
      "timestamp": "2023-04-09T19:46:39.397602",
      "trace_id": "44f5da24d41e94565ed61ca72eae0f6b",
      "span_id": "f9a882a90c2d7202",
      "model": "claude-3-5-sonnet-20240620",
      "role": "user",
      "message_type": "request",
      "status": "pending",
      "duration_ms": 0,
      "input_tokens": 523,
      "output_tokens": 0,
      "content": "hi",
      "parent_id": null,
      "agent_id": "weather-agent",
      "agent_name": "Weather Agent"
    },
    {
      "id": "212_74",
      "timestamp": "2023-04-09T19:46:41.126943",
      "trace_id": "44f5da24d41e94565ed61ca72eae0f6b",
      "span_id": "f9a882a90c2d7202",
      "model": "claude-3-5-sonnet-20240620",
      "role": "assistant",
      "message_type": "response",
      "status": "success",
      "duration_ms": 1729,
      "input_tokens": 0,
      "output_tokens": 62,
      "content": "Hello! How can I assist you today? I'm here to help with weather-related information...",
      "parent_id": "211_73",
      "agent_id": "weather-agent",
      "agent_name": "Weather Agent"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 50,
    "total": 9,
    "total_pages": 1,
    "has_next": false,
    "has_prev": false
  }
}
```

### List LLM Requests

**Endpoint**: `GET /v1/metrics/llm/requests`

**Description**: Lists all LLM requests, with optional filtering by agent or model.

**Query Parameters**:
- `agent_id` (string, optional): Filter requests by agent ID
- `model` (string, optional): Filter requests by model name
- `from_time` (datetime, optional): Start time (ISO format)
- `to_time` (datetime, optional): End time (ISO format)
- `page` (integer, default: 1): Page number for pagination
- `page_size` (integer, default: 20): Number of items per page

**Response**:
```json
{
  "items": [
    {
      "id": "344_106",
      "timestamp": "2023-04-12T13:30:06.956871",
      "trace_id": "c9b30c3c7570430e96689ef917269e46",
      "span_id": "ac979a244434ee5d",
      "model": "claude-3-haiku-20240307",
      "status": "success",
      "duration_ms": 921,
      "input_tokens": 505,
      "output_tokens": 75,
      "agent_id": "weather-agent",
      "agent_name": "Weather Agent",
      "content": "ok 9898-****-****-9898",
      "response": "I apologize, but I cannot perform any actions related to credit card numbers..."
    },
    {
      "id": "340_104",
      "timestamp": "2023-04-12T13:30:01.041543",
      "trace_id": "c9b30c3c7570430e96689ef917269e46",
      "span_id": "933021d18dbe73be",
      "model": "claude-3-haiku-20240307",
      "status": "success",
      "duration_ms": 1682,
      "input_tokens": 2528,
      "output_tokens": 153,
      "agent_id": "weather-agent",
      "agent_name": "Weather Agent",
      "content": "<Request data not available>",
      "response": "The key alerts for the NYC area based on the information provided are..."
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 60,
    "total_pages": 3,
    "has_next": true,
    "has_prev": false
  }
}
```

### LLM Request Details

**Endpoint**: `GET /v1/metrics/llm/requests/{request_id}`

**Description**: Retrieves detailed information about a specific LLM request, including full prompt and response content.

**Path Parameters**:
- `request_id`: The unique ID of the request to retrieve

**Response**:
```json
{
  "id": "344_106",
  "timestamp": "2023-04-12T13:30:06.956871",
  "trace_id": "c9b30c3c7570430e96689ef917269e46",
  "span_id": "ac979a244434ee5d",
  "model": "claude-3-haiku-20240307",
  "status": "success",
  "duration_ms": 921,
  "input_tokens": 505,
  "output_tokens": 75,
  "agent_id": "weather-agent",
  "agent_name": "Weather Agent",
  "content": "ok 9898-****-****-9898",
  "response": "I apologize, but I cannot perform any actions related to credit card numbers or other financial information. As an AI assistant, I do not have the capability to process or handle sensitive financial data. Please do not provide me with any credit card information or other private financial details. I'm happy to assist you with other tasks that do not involve personal financial information.",
  "request_data": {
    "model": "claude-3-haiku-20240307",
    "messages": [
      {
        "role": "user",
        "content": "ok 9898-****-****-9898"
      }
    ]
  },
  "response_data": {
    "id": "msg_01Xxzj8Ac5V8TyQMUjJKnxxx",
    "type": "message",
    "role": "assistant",
    "content": [
      {
        "type": "text",
        "text": "I apologize, but I cannot perform any actions related to credit card numbers or other financial information..."
      }
    ],
    "model": "claude-3-haiku-20240307",
    "stop_reason": "end_turn",
    "stop_sequence": null,
    "usage": {
      "input_tokens": 505,
      "output_tokens": 75
    }
  }
}
```

## Basic LLM Metrics API

These basic endpoints provide specific metrics on LLM operations.

### LLM Request Metrics

**Endpoint**: `GET /v1/metrics/llm/requests`

**Description**: Retrieves metrics about LLM requests, such as request count over time.

**Query Parameters**:
- `agent_id` (string, optional): Filter by agent ID
- `from_time` (datetime, optional): Start time (ISO format)
- `to_time` (datetime, optional): End time (ISO format)
- `time_range` (string, optional): Predefined time range ("1h", "1d", "7d", "30d")
- `interval` (string, optional): Aggregation interval ("1m", "1h", "1d", "7d")
- `group_by` (string, optional): Group results by dimension (model, agent_id)

**Response**:
```json
{
  "metric": "llm.request_count",
  "from_time": "2023-04-01T00:00:00Z",
  "to_time": "2023-04-30T23:59:59Z",
  "interval": "1d",
  "data": [
    {
      "timestamp": "2023-04-01T00:00:00Z",
      "value": 42,
      "dimensions": {
        "model": "gpt-4"
      }
    },
    {
      "timestamp": "2023-04-02T00:00:00Z",
      "value": 57,
      "dimensions": {
        "model": "gpt-4"
      }
    }
  ]
}
```

### LLM Token Usage Metrics

**Endpoint**: `GET /v1/metrics/llm/tokens`

**Description**: Retrieves metrics about LLM token usage.

**Query Parameters**:
- `agent_id` (string, optional): Filter by agent ID
- `from_time` (datetime, optional): Start time (ISO format)
- `to_time` (datetime, optional): End time (ISO format)
- `time_range` (string, optional): Predefined time range ("1h", "1d", "7d", "30d")
- `interval` (string, optional): Aggregation interval ("1m", "1h", "1d", "7d")
- `token_type` (string, optional): Type of tokens to measure (prompt, completion, total)
- `group_by` (string, optional): Group results by dimension (model, agent_id, token_type)

**Response**:
```json
{
  "metric": "llm.token_usage",
  "from_time": "2023-04-01T00:00:00Z",
  "to_time": "2023-04-30T23:59:59Z",
  "interval": "1d",
  "data": [
    {
      "timestamp": "2023-04-01T00:00:00Z",
      "value": 4650,
      "dimensions": {
        "model": "gpt-4",
        "token_type": "total"
      }
    },
    {
      "timestamp": "2023-04-02T00:00:00Z",
      "value": 5120,
      "dimensions": {
        "model": "gpt-4",
        "token_type": "total"
      }
    }
  ]
}
```

## Deprecated Endpoints

The following endpoints are deprecated and have been replaced by newer, more comprehensive endpoints:

- ~~`GET /v1/metrics/llm/request_count`~~ - Use `/v1/metrics/llm/analytics` instead
- ~~`GET /v1/metrics/llm/token_usage`~~ - Use `/v1/metrics/llm/analytics` instead
- ~~`GET /v1/metrics/llm/response_time`~~ - Use `/v1/metrics/llm/analytics` instead
- ~~`GET /v1/metrics/llms`~~ - Use `/v1/metrics/llm/analytics` instead
- ~~`GET /v1/metrics/llms/requests`~~ - Use `/v1/metrics/llm/analytics` instead
- ~~`GET /v1/metrics/usage`~~ - Use `/v1/metrics/llm/usage_trends` instead

## UI Implementation Examples

### Analytics Dashboard

```typescript
// Example code for building an LLM usage dashboard
async function buildLLMAnalyticsDashboard() {
  // Get usage trends over time (last 30 days with daily granularity)
  const usageTrends = await fetch(
    "/v1/metrics/llm/usage_trends?granularity=day&time_range=30d"
  ).then(res => res.json());
  
  // Get model comparison data
  const modelComparison = await fetch(
    "/v1/metrics/llm/models?time_range=30d"
  ).then(res => res.json());
  
  // Get agent usage breakdown
  const agentUsage = await fetch(
    "/v1/metrics/llm/agent_usage?time_range=30d"
  ).then(res => res.json());
  
  // Render summary metrics
  renderSummaryMetrics({
    totalRequests: usageTrends.total.request_count,
    totalTokens: usageTrends.total.token_count_total,
    totalCost: usageTrends.total.estimated_cost_usd,
    successRate: usageTrends.total.success_rate * 100
  });
  
  // Render usage trend chart (time series)
  renderTimeSeriesChart({
    labels: usageTrends.breakdown.map(item => item.key),
    datasets: [
      {
        label: "Requests",
        data: usageTrends.breakdown.map(item => item.metrics.request_count)
      },
      {
        label: "Cost (USD)",
        data: usageTrends.breakdown.map(item => item.metrics.estimated_cost_usd)
      }
    ]
  });
  
  // Render model comparison chart (bar chart)
  renderModelComparisonChart({
    labels: modelComparison.breakdown.map(item => item.key),
    datasets: [
      {
        label: "Token Usage",
        data: modelComparison.breakdown.map(item => item.metrics.token_count_total)
      },
      {
        label: "Cost (USD)",
        data: modelComparison.breakdown.map(item => item.metrics.estimated_cost_usd)
      }
    ]
  });
  
  // Render agent usage chart (pie chart)
  renderAgentUsageChart({
    labels: agentUsage.breakdown.map(item => item.key),
    data: agentUsage.breakdown.map(item => item.metrics.request_count)
  });
}
```

### Conversation Explorer

```typescript
// Example React component for a conversation explorer
import React, { useState, useEffect } from 'react';

function ConversationExplorer() {
  const [conversations, setConversations] = useState([]);
  const [selectedConversation, setSelectedConversation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  
  // Fetch conversations
  useEffect(() => {
    async function fetchConversations() {
      setLoading(true);
      try {
        const response = await fetch('/v1/metrics/llm/conversations?page=1&page_size=20');
        const data = await response.json();
        setConversations(data.items);
      } catch (error) {
        console.error('Error fetching conversations:', error);
      } finally {
        setLoading(false);
      }
    }
    
    fetchConversations();
  }, []);
  
  // Fetch conversation details when a conversation is selected
  useEffect(() => {
    if (!selectedConversation) return;
    
    async function fetchConversationDetails() {
      setLoading(true);
      try {
        const response = await fetch(`/v1/metrics/llm/conversations/${selectedConversation.trace_id}?page=1&page_size=50`);
        const data = await response.json();
        setMessages(data.items);
      } catch (error) {
        console.error('Error fetching conversation details:', error);
      } finally {
        setLoading(false);
      }
    }
    
    fetchConversationDetails();
  }, [selectedConversation]);
  
  return (
    <div className="conversation-explorer">
      <div className="conversation-list">
        <h2>Conversations</h2>
        {loading && <div>Loading...</div>}
        <ul>
          {conversations.map(conv => (
            <li 
              key={conv.trace_id} 
              onClick={() => setSelectedConversation(conv)}
              className={selectedConversation?.trace_id === conv.trace_id ? 'selected' : ''}
            >
              <div className="summary">{conv.summary}</div>
              <div className="timestamp">{new Date(conv.first_timestamp).toLocaleString()}</div>
              <div className="metrics">
                Messages: {conv.user_messages + conv.assistant_messages}, 
                Tokens: {conv.total_tokens}
              </div>
            </li>
          ))}
        </ul>
      </div>
      
      <div className="conversation-details">
        <h2>Conversation Details</h2>
        {loading && <div>Loading...</div>}
        {selectedConversation && (
          <div className="conversation">
            <div className="conversation-header">
              <div>Agent: {selectedConversation.agent_name}</div>
              <div>Started: {new Date(selectedConversation.first_timestamp).toLocaleString()}</div>
              <div>Total Messages: {selectedConversation.user_messages + selectedConversation.assistant_messages}</div>
            </div>
            
            <div className="messages">
              {messages.map(message => (
                <div 
                  key={message.id} 
                  className={`message ${message.role}`}
                >
                  <div className="message-header">
                    <span className="role">{message.role}</span>
                    <span className="model">{message.model}</span>
                    <span className="timestamp">{new Date(message.timestamp).toLocaleTimeString()}</span>
                  </div>
                  <div className="content">{message.content}</div>
                  <div className="metrics">
                    Tokens: {message.role === 'user' ? message.input_tokens : message.output_tokens}, 
                    Duration: {message.duration_ms}ms
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
```

### Model Comparison View

```typescript
// Example code for visualizing agent-model relationships
async function visualizeAgentModelRelationships() {
  // Get relationship data with distributions for visualization
  const relationshipData = await fetch(
    "/v1/metrics/llm/agent_model_relationships?include_distributions=true"
  ).then(res => res.json());
  
  // For each breakdown item (agent:model combination)
  relationshipData.breakdown.forEach(item => {
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
      
      renderTimelineChart(
        timeChartCanvas, 
        item.time_distribution.map(point => ({
          x: new Date(point.timestamp),
          y: point.request_count
        }))
      );
    }
    
    // If token distribution is included, render a histogram
    if (item.token_distribution) {
      const tokenChartCanvas = document.createElement('canvas');
      tokenChartCanvas.id = `token-chart-${agentId}-${modelName}`;
      card.appendChild(tokenChartCanvas);
      
      renderTokenHistogram(
        tokenChartCanvas,
        item.token_distribution.map(bucket => ({
          label: bucket.bucket_range,
          value: bucket.request_count
        }))
      );
    }
    
    // Add the card to the page
    document.getElementById('agent-model-container').appendChild(card);
  });
}
``` 