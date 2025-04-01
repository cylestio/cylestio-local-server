import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timezone

from src.main import app
from src.database.session import get_db
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Setup in-memory test database
TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture
def test_db():
    """Create test database tables and provide a test database session"""
    from src.models.base import Base
    Base.metadata.create_all(bind=engine)
    
    # Create test session that overrides the dependency
    def override_get_db():
        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()
            
    app.dependency_overrides[get_db] = override_get_db
    
    yield TestingSessionLocal()
    
    # Clean up
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides = {}

@pytest.fixture
def client(test_db):
    """Create a test client for the API"""
    return TestClient(app)

# Sample test data
valid_event = {
    "schema_version": "1.0",
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "trace_id": "test-trace-id",
    "span_id": "test-span-id",
    "parent_span_id": None,
    "name": "test.event",
    "level": "INFO",
    "agent_id": "test-agent",
    "attributes": {
        "test.attribute": "test-value"
    }
}

def test_telemetry_validation_errors(client):
    """Test validation errors for telemetry endpoint"""
    # Missing required field
    invalid_event = valid_event.copy()
    del invalid_event["timestamp"]
    
    response = client.post("/v1/telemetry", json=invalid_event)
    assert response.status_code == 422  # Validation error
    
    # Invalid timestamp format
    invalid_event = valid_event.copy()
    invalid_event["timestamp"] = "not-a-timestamp"
    
    response = client.post("/v1/telemetry", json=invalid_event)
    assert response.status_code == 422  # Validation error
    
    # Invalid level
    invalid_event = valid_event.copy()
    invalid_event["level"] = "NOT_A_LEVEL"
    
    response = client.post("/v1/telemetry", json=invalid_event)
    assert response.status_code == 422  # Validation error

def test_telemetry_batch_validation(client):
    """Test batch validation for telemetry endpoint"""
    # Empty batch
    response = client.post("/v1/telemetry/batch", json={"events": []})
    assert response.status_code == 201  # Should be valid but process 0 events
    
    # Batch with invalid event
    invalid_event = valid_event.copy()
    del invalid_event["timestamp"]
    
    response = client.post("/v1/telemetry/batch", json={"events": [valid_event, invalid_event]})
    assert response.status_code == 422  # Validation error
    
    # Batch with mixing valid events and events that cause processing errors
    event_that_may_cause_error = valid_event.copy()
    event_that_may_cause_error["attributes"] = {}  # Empty attributes might cause processing errors
    
    response = client.post("/v1/telemetry/batch", json={"events": [valid_event, event_that_may_cause_error]})
    if response.status_code == 201:
        data = response.json()
        assert data["total"] == 2
        # Should have at least one successful event
        assert data["processed"] >= 1

def test_telemetry_get_nonexistent(client):
    """Test getting non-existent telemetry events"""
    response = client.get("/v1/telemetry/events/nonexistent")
    assert response.status_code == 404
    
    response = client.get("/v1/telemetry/traces/nonexistent")
    assert response.status_code == 200
    assert response.json() == []  # Should return empty list
    
def test_metrics_validation(client):
    """Test validation for metrics endpoints"""
    # Invalid metric name
    response = client.get("/v1/metrics?metric=invalid_metric&time_range=1d")
    assert response.status_code in [400, 404, 422]  # Either not found or validation error
    
    # Invalid time range
    response = client.get("/v1/metrics?metric=llm_request_count&time_range=invalid")
    assert response.status_code in [400, 422]  # Either bad request or validation error 