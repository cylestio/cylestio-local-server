# Cylestio Local Server - System Architecture Design

## 1. Overview

The Cylestio Local Server is a lightweight API server for consuming and analyzing JSON telemetry data from the cylestio-monitor tool. This document outlines the high-level architecture designed to meet the requirements for the MVP implementation.

### 1.1 Core Capabilities

The system architecture is designed to support four primary capabilities:

1. **REST API Layer**: Receiving and responding to telemetry data requests
2. **Processing Layer**: Transforming, validating, and normalizing incoming data
3. **Analysis Layer**: Computing metrics and producing insights from stored data
4. **Database Layer**: Persisting telemetry data for later analysis

### 1.2 Design Principles

The architecture follows these key design principles:

1. **Modularity**: Components are designed with clear boundaries and responsibilities
2. **Loose Coupling**: Components interact through well-defined interfaces
3. **Single Responsibility**: Each component focuses on a specific functional domain
4. **Extensibility**: The system can be extended with minimal changes to existing code
5. **Testability**: Components can be tested in isolation
6. **Security by Design**: Security considerations are incorporated throughout

## 2. Component Definition

### 2.1 REST API Layer

**Primary Responsibility**: Expose HTTP endpoints for receiving telemetry data, querying metrics, and administrative functions.

**Key Components**:
- **API Router**: Routes requests to appropriate handlers
- **Request Validators**: Validate incoming requests against JSON schemas
- **Response Formatters**: Format responses consistently
- **Authentication/Authorization**: Validate access rights (future extension)
- **Rate Limiting**: Protect against abuse (future extension)

**Technology**: FastAPI (for its performance, automatic documentation, and async support)

### 2.2 Processing Layer

**Primary Responsibility**: Transform, validate, and normalize incoming telemetry data.

**Key Components**:
- **Schema Validators**: Validate incoming data against telemetry schema
- **Data Normalizer**: Convert JSON data into relational structures
- **Data Enricher**: Add derived fields or metadata
- **Event Correlator**: Link related events (by trace_id, span_id, etc.)

**Technology**: Pydantic (for validation), custom processing logic

### 2.3 Analysis Layer

**Primary Responsibility**: Compute metrics and produce insights from stored data.

**Key Components**:
- **Metric Calculators**: Implement algorithms for computing metrics
- **Query Builders**: Generate optimized database queries
- **Aggregators**: Aggregate data across dimensions (time, agent, model, etc.)
- **Report Generators**: Generate structured reports

**Technology**: SQLAlchemy (for query building), Pandas (for data manipulation)

### 2.4 Database Layer

**Primary Responsibility**: Persist telemetry data in normalized form for efficient querying.

**Key Components**:
- **ORM Models**: Define database schema
- **Repository Pattern**: Abstract database operations
- **Migration Tools**: Manage schema changes
- **Connection Pool**: Manage database connections

**Technology**: SQLAlchemy (ORM), SQLite (database)

### 2.5 Cross-Cutting Components

**Config Management**:
- Load and validate configuration from files, environment variables
- Provide centralized access to configuration settings

**Logging and Error Handling**:
- Consistent logging across components
- Centralized error handling and reporting

**Utilities**:
- Common functions and helpers used across components

## 3. Data Flow and Component Interactions

### 3.1 Telemetry Data Ingestion Flow

1. **API Layer**: 
   - Receives JSON telemetry data via POST request
   - Validates basic request structure
   - Passes data to Processing Layer

2. **Processing Layer**:
   - Validates telemetry data against schema
   - Normalizes data into relational structures
   - Enriches data with derived fields
   - Passes normalized data to Database Layer

3. **Database Layer**:
   - Maps normalized data to ORM models
   - Persists data to database
   - Returns success/failure status

4. **API Layer**:
   - Returns appropriate response to client

### 3.2 Analytics Query Flow

1. **API Layer**:
   - Receives query parameters via GET request
   - Validates parameters
   - Passes parameters to Analysis Layer

2. **Analysis Layer**:
   - Builds database queries based on parameters
   - Retrieves data through Database Layer
   - Processes and aggregates data
   - Returns computed metrics

3. **Database Layer**:
   - Executes optimized queries
   - Returns result sets

4. **API Layer**:
   - Formats results
   - Returns response to client

### 3.3 Component Interaction Diagram

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│                 │      │                 │      │                 │      │                 │
│   REST API      │◄────►│   Processing    │◄────►│   Analysis      │◄────►│   Database      │
│   Layer         │      │   Layer         │      │   Layer         │      │   Layer         │
│                 │      │                 │      │                 │      │                 │
└─────────────────┘      └─────────────────┘      └─────────────────┘      └─────────────────┘
        ▲                        ▲                        ▲                        ▲
        │                        │                        │                        │
        │                        │                        │                        │
        ▼                        ▼                        ▼                        ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                             │
│                                  Cross-Cutting Components                                   │
│                                                                                             │
│                    Configuration        Logging        Error Handling                       │
│                                                                                             │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

## 4. Technology Selection Rationale

### 4.1 FastAPI

- **Performance**: Built on Starlette with significant performance benefits
- **Validation**: Automatic request validation using Pydantic
- **Documentation**: Automatic OpenAPI/Swagger documentation
- **Async Support**: Native support for async/await
- **Type Hints**: First-class support for Python type hints

### 4.2 SQLAlchemy

- **ORM Capabilities**: Robust object-relational mapping
- **Query Generation**: Powerful query building interface
- **Database Agnostic**: Works with multiple database backends
- **Migration Support**: Alembic integration for schema migrations
- **Performance**: Optimized for both simple and complex queries

### 4.3 SQLite

- **Simplicity**: No need for separate database server
- **Performance**: Excellent for moderate workloads
- **Reliability**: ACID-compliant for data integrity
- **Portability**: Single file database, easy to back up
- **Future Migration**: Can be replaced with PostgreSQL for scaling

### 4.4 Pydantic

- **Data Validation**: Robust validation with clear error messages
- **Schema Definition**: Declarative schema definitions with type hints
- **JSON Integration**: Excellent JSON serialization/deserialization
- **Performance**: Validation implemented in Rust for speed

## 5. Database Schema Design

### 5.1 Core Tables

1. **Events**:
   - `id`: Primary key
   - `schema_version`: Schema version
   - `timestamp`: Event timestamp
   - `trace_id`: Trace identifier
   - `span_id`: Span identifier
   - `parent_span_id`: Parent span identifier
   - `name`: Event name
   - `level`: Log level
   - `agent_id`: Agent identifier

2. **Attributes**:
   - `id`: Primary key
   - `event_id`: Foreign key to Events
   - `key`: Attribute name
   - `value`: Attribute value
   - `value_type`: Data type of value

3. **Sessions**:
   - `id`: Session identifier (primary key)
   - `agent_id`: Agent identifier
   - `start_time`: Session start time
   - `end_time`: Session end time

4. **Agents**:
   - `id`: Agent identifier (primary key)
   - `first_seen`: First seen timestamp
   - `last_seen`: Last seen timestamp
   - `environment`: Environment information

5. **LLMCalls**:
   - `id`: Primary key
   - `event_id`: Foreign key to Events
   - `vendor`: LLM provider
   - `model`: Model name
   - `request_type`: Type of request
   - `request_timestamp`: Request timestamp
   - `response_id`: Response identifier
   - `response_timestamp`: Response timestamp
   - `duration_ms`: Duration in milliseconds
   - `stop_reason`: Stop reason
   - `input_tokens`: Input token count
   - `output_tokens`: Output token count
   - `total_tokens`: Total token count

6. **ToolExecutions**:
   - `id`: Primary key
   - `event_id`: Foreign key to Events
   - `tool_name`: Tool name
   - `tool_id`: Tool identifier
   - `status`: Execution status
   - `result_type`: Result type

### 5.2 Relationships

- Events have many Attributes (one-to-many)
- Events belong to Sessions (many-to-one)
- Sessions belong to Agents (many-to-one)
- LLMCalls extend Events (one-to-one)
- ToolExecutions extend Events (one-to-one)

## 6. Error Handling Strategy

### 6.1 Error Categories

1. **Validation Errors**: Invalid input data
2. **Processing Errors**: Errors during data processing
3. **Database Errors**: Database-related errors
4. **System Errors**: System-level errors
5. **Authentication/Authorization Errors**: Access control errors

### 6.2 Error Handling Approach

1. **Centralized Error Handling**:
   - Global exception handlers for consistent responses
   - Error logging with appropriate context

2. **Standardized Error Response Format**:
   ```json
   {
     "error": {
       "code": "ERROR_CODE",
       "message": "User-friendly error message",
       "details": {
         "field": "Specific field with error",
         "reason": "Detailed reason for error"
       }
     }
   }
   ```

3. **Error Propagation**:
   - Lower layers raise specific exceptions
   - Higher layers catch, log, and transform exceptions
   - API layer converts exceptions to appropriate HTTP responses

4. **Validation Error Handling**:
   - Return 400 Bad Request with validation details
   - Clear indication of which fields failed validation

5. **Graceful Degradation**:
   - System continues functioning when parts fail
   - Clear logging of degraded functionality

## 7. Configuration Management

### 7.1 Configuration Sources

1. **Configuration File**: Default settings in YAML/TOML format
2. **Environment Variables**: Override file settings
3. **Command-Line Arguments**: Override environment variables

### 7.2 Configuration Categories

1. **Server Configuration**:
   - Host, port, workers
   - API rate limits
   - CORS settings

2. **Database Configuration**:
   - Connection string
   - Pool size
   - Timeout settings

3. **Logging Configuration**:
   - Log level
   - Log format
   - Log destinations

4. **Feature Flags**:
   - Enable/disable optional features
   - Feature-specific settings

### 7.3 Configuration Management Pattern

1. **Centralized Access**:
   - Single configuration service accessible to all components
   - Typed access to configuration values

2. **Configuration Validation**:
   - Validate configuration at startup
   - Provide clear error messages for invalid configuration

3. **Default Values**:
   - Reasonable defaults for all settings
   - Clear documentation of default values

4. **Sensitive Information**:
   - Support for secure storage of sensitive values
   - Masking of sensitive values in logs

## 8. Implementation Guidelines

### 8.1 Project Structure

```
src/
├── api/
│   ├── routes/
│   ├── schemas/
│   └── middleware/
├── processing/
│   ├── validators/
│   ├── normalizers/
│   └── enrichers/
├── analysis/
│   ├── metrics/
│   ├── queries/
│   └── reports/
├── database/
│   ├── models/
│   ├── repositories/
│   └── migrations/
├── config/
│   ├── settings.py
│   └── defaults.py
├── utils/
│   ├── logging.py
│   └── errors.py
└── models/
    └── domain.py
```

### 8.2 Coding Standards

1. **Type Hints**: Use Python type hints throughout
2. **Docstrings**: Document all modules, classes, and functions
3. **Naming Conventions**: Follow PEP 8 naming conventions
4. **Test Coverage**: Aim for high test coverage
5. **Error Handling**: Consistent exception handling

### 8.3 Testing Strategy

1. **Unit Tests**: Test individual components in isolation
2. **Integration Tests**: Test component interactions
3. **API Tests**: Test API endpoints
4. **Performance Tests**: Test system under load

## 9. Future Extensions

1. **Authentication and Authorization**:
   - User management
   - Role-based access control
   - API keys/tokens

2. **Advanced Analytics**:
   - Machine learning based anomaly detection
   - Predictive analytics
   - Custom metrics and dashboards

3. **Scalability Enhancements**:
   - PostgreSQL migration
   - Caching layer
   - Async processing with message queues

4. **Export/Import**:
   - Data export to various formats
   - Bulk data import
   - Integration with other tools

## 10. Conclusion

This architecture design provides a solid foundation for the Cylestio Local Server MVP. The modular approach with clearly defined components and interfaces enables maintainability and extensibility, while the technology choices balance simplicity with performance and scalability considerations.

The implementation should focus on the core functionality first, with a path for future enhancements. By following the design principles and guidelines outlined in this document, the system will be well-positioned to evolve as requirements change. 