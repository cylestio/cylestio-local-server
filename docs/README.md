# Cylestio Local Server Documentation

Welcome to the Cylestio Local Server documentation! This guide provides all the information you need to use the Cylestio Local Server for telemetry data collection and metrics retrieval.

## Table of Contents

- [API Reference](./api/README.md) - Detailed information about all API endpoints
- [Getting Started](./guides/getting-started.md) - Instructions for setting up and running the server
- [Examples](./examples/README.md) - Code examples for common use cases
- [Telemetry Events](./guides/telemetry-events.md) - Learn about telemetry event structure and semantics
- [Metrics Guide](./guides/metrics.md) - Understanding available metrics and how to use them

## About Cylestio Local Server

Cylestio Local Server is a lightweight, self-hosted server for collecting, processing, and analyzing telemetry data from AI agents. It provides:

- Simple REST API for submitting telemetry events
- Metrics aggregation and retrieval
- Trace and span management for distributed operations
- Filtering and querying capabilities
- Dashboard-ready metrics

## Quick Start

To get started with Cylestio Local Server:

1. Install the server (see [Getting Started](./guides/getting-started.md))
2. Start the server: `uvicorn src.main:app --host 0.0.0.0 --port 8000`
3. Access the API documentation: `http://localhost:8000/docs`
4. Start sending telemetry events (see [Examples](./examples/README.md))

## Resources

- [GitHub Repository](https://github.com/cylestio/cylestio-local-server)
- [Issue Tracker](https://github.com/cylestio/cylestio-local-server/issues)

# Agent-Specific API Endpoints Implementation

This directory contains documentation for the agent-specific API endpoints in the Cylestio monitoring dashboard.

## Overview

The agent-specific endpoints provide detailed insights and metrics for individual AI agents, enabling users to drill down into specific agent performance, usage, and behavior.

## Endpoint Categories

The agent-specific endpoints are organized into several categories:

1. **Base Agent Endpoints**: Get information about agents and their configurations
   - `GET /api/v1/agents` - List all agents with filtering and pagination
   - `GET /api/v1/agents/{agent_id}` - Get detailed information about a specific agent

2. **Agent Dashboard**: Get comprehensive metrics overview for a specific agent
   - `GET /api/v1/agents/{agent_id}/dashboard` - Get dashboard metrics for an agent over a specified time period

3. **LLM-Related Endpoints**: Get information about LLM usage for a specific agent
   - `GET /api/v1/agents/{agent_id}/llms` - Get LLM usage overview for an agent
   - `GET /api/v1/agents/{agent_id}/llms/requests` - Get detailed LLM requests for an agent
   - `GET /api/v1/agents/{agent_id}/tokens` - Get token usage metrics for an agent

4. **Tool Usage Endpoints**: Get information about tool usage for a specific agent
   - `GET /api/v1/agents/{agent_id}/tools` - Get tool usage overview for an agent
   - `GET /api/v1/agents/{agent_id}/tools/executions` - Get detailed tool executions for an agent

5. **Session and Trace Endpoints**: Get information about sessions and execution traces
   - `GET /api/v1/agents/{agent_id}/sessions` - Get sessions for an agent
   - `GET /api/v1/agents/{agent_id}/traces` - Get execution traces for an agent

6. **Security and Alert Endpoints**: Get security-related information for an agent
   - `GET /api/v1/agents/{agent_id}/alerts` - Get security alerts for an agent

## Implementation Details

The agent-specific endpoints are implemented using:
- FastAPI for the API framework
- SQLAlchemy for database access
- A custom analysis layer for processing telemetry data

The endpoints follow consistent patterns:
- All endpoints support time range filtering
- List endpoints support pagination
- All endpoints connect to the analysis layer for real data processing
- Responses follow a standard structure with metadata

### Real Data Connections

The following endpoints have been fully implemented with real data connections:

- `GET /api/v1/agents/{agent_id}/sessions` - Get real session data for an agent
- `GET /api/v1/agents/{agent_id}/traces` - Get real execution trace data for an agent
- `GET /api/v1/agents/{agent_id}/alerts` - Get real security alert data for an agent

These endpoints query the database through the analysis layer and apply filtering, sorting, and pagination to return actual data instead of mock responses.

## Documentation

For detailed API documentation, see the following files:
- [Agent Endpoints](api/agent_endpoints.md) - Detailed endpoint documentation
- [API Endpoint Structure](api/api_endpoint_structure.md) - API design guidelines

## Usage Examples

### Getting Agent Dashboard Data

```python
import requests

response = requests.get(
    "http://localhost:8000/api/v1/agents/weather-agent/dashboard",
    params={"time_range": "7d"}
)
dashboard = response.json()

# Access metrics
for metric in dashboard["metrics"]:
    print(f"{metric['metric']}: {metric['value']} ({metric['change']}% {metric['trend']})")
```

### Filtering Tool Executions

```python
import requests

response = requests.get(
    "http://localhost:8000/api/v1/agents/weather-agent/tools/executions",
    params={
        "tool_name": "web_search",
        "status": "error",
        "time_range": "30d",
        "page": 1,
        "page_size": 50
    }
)
executions = response.json()

# Process executions
for execution in executions["items"]:
    print(f"Execution ID: {execution['execution_id']}")
    print(f"Timestamp: {execution['timestamp']}")
    print(f"Status: {execution['status']}")
    print(f"Error: {execution['result_summary']}")
    print("---") 