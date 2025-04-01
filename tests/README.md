# Cylestio Telemetry Server Testing Framework

This directory contains a comprehensive testing framework for the Cylestio local telemetry server.

## Overview

The testing framework is designed to validate all aspects of the telemetry server, including data extraction logic, relationship management, event processing, and performance characteristics.

The tests are organized into categories:

1. **Unit Tests**: Test individual components in isolation
2. **Integration Tests**: Test interactions between components
3. **End-to-End Tests**: Test realistic workflows through the complete system
4. **Performance Tests**: Measure throughput, memory usage, and scaling

## Prerequisites

- Python 3.12
- SQLite (for database tests)

## Installation

Create a Python 3.12 virtual environment and install the dependencies:

```bash
# Create a venv at the repo level
python3.12 -m venv ../venv
source ../venv/bin/activate

# Install testing dependencies
pip install -r requirements.txt

# Install the package in development mode
pip install -e ..
```

## Running Tests

### Running All Tests

To run the complete test suite:

```bash
python run_all_tests.py
```

### Running Specific Test Categories

To run only specific test categories:

```bash
python run_all_tests.py --categories unit integration
```

Available categories:
- `unit`: Basic unit tests
- `integration`: Component integration tests
- `e2e`: End-to-end workflow tests
- `performance`: Performance benchmarks

### Test Options

```bash
python run_all_tests.py --help
```

Common options:
- `--coverage`: Generate code coverage report
- `--verbose`: Enable verbose output
- `--skip-performance`: Skip performance tests (faster test runs)
- `--skip-heavy`: Skip tests with large datasets (faster test runs)
- `--report PATH`: Path for test report output (default: test_report.json)
- `--html-report`: Generate HTML test report in addition to JSON

### Running Individual Tests

To run a specific test file:

```bash
python -m pytest test_models/test_llm_interaction_comprehensive.py -v
```

## Test Structure

- `conftest.py`: Common test fixtures and utilities
- `test_utils.py`: Helper functions for test data generation
- `test_models/`: Unit tests for data models
- `test_integration/`: Integration tests for component interactions
- `test_e2e/`: End-to-end workflow tests
- `test_performance/`: Performance benchmark tests
- `run_all_tests.py`: Test runner script

## Test Coverage

The test suite aims to achieve at least 80% code coverage across all components.

To check code coverage for a specific set of tests:

```bash
python -m pytest test_models/ --cov=src.models --cov-report=term-missing
```

## Performance Benchmarks

Performance tests measure:
- Event processing throughput (events/second)
- Memory usage during processing
- Database query performance
- Scaling characteristics with increasing data volume

To run only performance tests:

```bash
python run_all_tests.py --categories performance
```

## Adding New Tests

When adding new components or fixing bugs:

1. Add unit tests for basic functionality
2. Add integration tests for component interactions
3. Extend end-to-end tests for realistic workflows
4. Update performance tests if the changes affect processing efficiency

Follow the existing test patterns and use the `test_utils.py` helpers for test data generation.

## Continuous Integration

The test suite is designed to be run in CI/CD pipelines. The test runner produces a JSON report that can be parsed by CI tools.

## Troubleshooting

If tests are failing:

1. Run with the `--verbose` flag for more detailed output
2. Check that all dependencies are installed
3. Run specific failing tests in isolation to debug
4. Verify that the database is properly initialized
5. Check for environment-specific issues (file permissions, etc.) 