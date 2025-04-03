# API Documentation and Testing Resources

This directory contains comprehensive documentation and testing resources for the Cylestio Local Server API. These resources are designed to help developers understand and interact with the API effectively.

## Documentation

### API Specification

- [**OpenAPI Specification**](./openapi.yaml) - Complete API reference in OpenAPI/Swagger format describing all endpoints, parameters, request/response formats, and schemas.

### Endpoint Guides

Detailed guides for specific API categories, including examples, parameter descriptions, and common use cases:

- [**Telemetry Endpoints Guide**](./telemetry-endpoints-guide.md) - Documentation for submitting and retrieving telemetry events.
- [**Metrics Endpoints Guide**](./metrics-endpoints-guide.md) - Guide to retrieving aggregated metrics and analytics.
- [**Agent Endpoints Guide**](./agent-endpoints-guide.md) - Documentation for agent-specific operations and data retrieval.

## Testing Resources

The following test files are available to validate API functionality:

- [**API Documentation Tests**](../../tests/test_api_documentation.py) - Tests that verify API responses match the documented formats and behavior.
- [**API Edge Cases Tests**](../../tests/test_api_edge_cases.py) - Tests for handling edge cases and error conditions.

## Additional Resources

### Future Development Plans

The following roadmap items detail planned improvements to the API infrastructure:

- [**Performance and Load Testing**](../../tasks/06-01-ROADMAP-ITEMS.md#performance-and-load-testing-for-apis) - Plans for performance benchmarking and capacity planning.
- [**API Change Management Process**](../../tasks/06-01-ROADMAP-ITEMS.md#api-change-management-process) - Strategy for API versioning, backwards compatibility, and change notifications.

## Using the API Documentation

To explore the API using the OpenAPI specification:

1. Use tools like Swagger UI or Redoc to render the `openapi.yaml` file
2. For local development, run Swagger UI with:

```bash
docker run -p 8080:8080 -e SWAGGER_JSON=/api/openapi.yaml -v $(pwd)/docs/api:/api swaggerapi/swagger-ui
```

3. Navigate to `http://localhost:8080` to interactively browse the API

## Contributing to Documentation

When contributing to the API or its documentation:

1. Update the OpenAPI specification (`openapi.yaml`) to reflect any API changes
2. Update the relevant endpoint guides to include examples of new functionality
3. Add or update tests to validate new endpoints or changed behavior
4. Follow the API change management process for any breaking changes

## Running the Tests

To run the API tests:

```bash
pytest tests/test_api_documentation.py
pytest tests/test_api_edge_cases.py
```

For more specific test cases:

```bash
pytest tests/test_api_documentation.py::TestAPIDocumentation::test_telemetry_endpoint_validation
``` 