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