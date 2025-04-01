# Cylestio Local Server

A lightweight API server for consuming and analyzing JSON telemetry data from the cylestio-monitor tool.

## Architecture

The system architecture is designed with four key components:

1. **REST API Layer (FastAPI)**: Receiving and responding to telemetry data requests
2. **Processing Layer**: Transforming, validating, and normalizing incoming data
3. **Analysis Layer**: Computing metrics and producing insights from stored data
4. **Database Layer (SQLAlchemy + SQLite)**: Persisting telemetry data for later analysis

For full architecture details, see the [architecture design document](src/architecture_design.md).

## Project Structure

```
src/
├── api/           # REST API components
├── processing/    # Data processing logic
├── analysis/      # Analytics and reporting
├── database/      # ORM models and database interactions
├── config/        # Configuration management
├── utils/         # Common utilities
└── models/        # Domain models
```

## Getting Started

Instructions for setup and configuration will be added as development progresses.

## License

See the [LICENSE](LICENSE) file for details.

## Testing and Evaluation

To verify the functionality of the Cylestio Local Server, you can use the provided process_example_event.py script to process example telemetry data and check the database output:

```bash
# Run the end-to-end processing script
python process_example_event.py
```

This script will:
1. Create a SQLite database at `/tmp/cylestio_demo.db`
2. Process all events from `example_records.json`
3. Generate a summary of the processed events
4. Show database statistics and sample records

## Project Structure

- `src/` - Contains the main implementation:
  - `models/` - SQLAlchemy ORM models
  - `processing/` - Event processing logic
  - `analysis/` - Analytics and query interface
  - `api/` - REST API implementation
  - `utils/` - Utility functions
- `tests/` - Tests for each component
- `docs/` - Documentation
- `example_records.json` - Sample telemetry data for testing
