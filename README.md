# Cylestio Local Server

A lightweight, self-hosted server for collecting, processing, and analyzing telemetry data from AI agents.

![License](https://img.shields.io/github/license/cylestio/cylestio-local-server)
[![PyPI version](https://badge.fury.io/py/cylestio-local-server.svg)](https://badge.fury.io/py/cylestio-local-server)

## Overview

Cylestio Local Server provides a comprehensive solution for monitoring and analyzing AI agent behavior through telemetry data collection. This server offers powerful tools for tracking agent performance, usage patterns, and identifying potential issues.

### Key Features

- ✅ **Simple REST API** for submitting telemetry events
- ✅ **Metrics aggregation and retrieval** for performance analysis
- ✅ **Trace and span management** for distributed operations
- ✅ **Filtering and querying capabilities** for data exploration
- ✅ **Dashboard-ready metrics** for visualization
- ✅ **LLM interaction tracking** for understanding AI behavior

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [Database Design](#database-design)
- [Development](#development)
- [Contributing](#contributing)
- [License](#license)

## Installation

### Option 1: Install from PyPI (Recommended)

```bash
pip install cylestio-local-server
```

### Option 2: Install from Source

```bash
# Clone the repository
git clone https://github.com/cylestio/cylestio-local-server.git
cd cylestio-local-server

# Install in development mode
pip install -e .
```

## Quick Start

### Starting the server (from PyPI installation)

```bash
# Start with default settings (port 8000, database in current directory)
cylestio-server

# Specify host, port and database path
cylestio-server --host 127.0.0.1 --port 9000 --db-path /path/to/database.db

# Enable development mode with auto-reload
cylestio-server --reload --debug
```

### Starting the server (from source)

```bash
# From the repository root
python -m src.main

# With custom port
python -m src.main --port 9000
```

### Verify Installation

1. Open your browser and navigate to:
   ```
   http://localhost:8000/docs
   ```
   This will open the Swagger UI documentation where you can explore and test the API.

2. Test the health endpoint:
   ```bash
   curl http://localhost:8000/v1/health
   ```
   You should see a response like:
   ```json
   {"status":"ok"}
   ```

## Configuration

The server can be configured using environment variables, command-line arguments, or a `.env` file in the root directory.

### Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| `HOST` | Server host address | `0.0.0.0` |
| `PORT` | Server port | `8000` |
| `DEBUG` | Enable debug mode | `false` |
| `DATABASE_URL` | Database connection string | `sqlite:///cylestio.db` |
| `API_PREFIX` | Prefix for API routes | `/api` |
| `RATE_LIMIT_PER_MINUTE` | API rate limit per client | `100` |
| `LOG_LEVEL` | Logging level | `INFO` |

### Example .env File

```
# Server settings
HOST=0.0.0.0
PORT=8000
DEBUG=false

# Database settings
DATABASE_URL=sqlite:///cylestio.db

# API settings
API_PREFIX=/api
RATE_LIMIT_PER_MINUTE=100

# Logging settings
LOG_LEVEL=INFO
```

## API Reference

The Cylestio Local Server provides a comprehensive API for submitting telemetry events and retrieving metrics.

### Main Endpoint Categories

- **Telemetry Submission**: Submit telemetry events from AI agents
- **Agent Metrics**: Get metrics for specific agents
- **LLM Interactions**: Track and analyze LLM usage
- **Tool Usage**: Monitor tool invocations and performance
- **Session Management**: Track user sessions and interactions
- **Trace Analysis**: Analyze execution traces for debugging

For detailed API documentation, refer to the Swagger UI at `/docs` when the server is running.

## Database Design

The server uses a relational database (SQLite by default) with a carefully designed schema optimized for telemetry data:

- **Events**: Base table for all telemetry events
- **LLM Interactions**: Tracks LLM requests and responses
- **Tool Executions**: Records tool invocations and results
- **Sessions**: Groups related events by session
- **Spans**: Manages distributed tracing data

The database schema supports:
- JSON attribute storage for flexible metadata
- Relationship tracking between related events
- Efficient querying for analytics

## System Architecture

The system is built with a modular architecture consisting of four main layers:

1. **REST API Layer**: Handles HTTP requests and responses
2. **Processing Layer**: Validates and normalizes telemetry data
3. **Analysis Layer**: Computes metrics and insights
4. **Database Layer**: Persists and retrieves data

This layered approach provides a clean separation of concerns and makes the system maintainable and extensible.

## Development

### Running Tests

```bash
# Run all tests
python -m pytest

# Run with coverage report
python -m pytest --cov=src
```

### Code Structure

- `src/api/`: API endpoints and controllers
- `src/database/`: Database models and repositories
- `src/processing/`: Data processing and validation
- `src/analysis/`: Metrics computation and analysis
- `src/models/`: Data models and schemas
- `src/utils/`: Utility functions and helpers
- `src/config/`: Configuration management
- `src/services/`: Business logic services

## Contributing

We welcome contributions from the community! Please follow these steps to contribute:

1. Fork the repository
2. Create a new branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests to ensure they pass
5. Commit your changes (`git commit -m 'Add some amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

Please read our [Contributing Guidelines](CONTRIBUTING.md) for more details.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgements

- FastAPI for the powerful API framework
- SQLAlchemy for the ORM capabilities
- The AI agent monitoring community for feedback and support 