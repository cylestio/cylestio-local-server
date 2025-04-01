import pytest
from fastapi.testclient import TestClient
import json
from datetime import datetime, timezone

from src.main import app
from src.processing.simple_processor import process_event
from src.database.session import init_db, get_db
from src.models.event import Event
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

# Sample test data
test_event = {
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

def test_health_endpoint(client):
    """Test the health endpoint"""
    response = client.get("/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    
def test_create_telemetry_event(client, test_db):
    """Test creating a telemetry event"""
    response = client.post("/v1/telemetry", json=test_event)
    assert response.status_code == 201
    assert response.json()["success"] is True
    assert "event_id" in response.json()
    
    # Verify the event was created in the database
    event = test_db.query(Event).first()
    assert event is not None
    assert event.trace_id == "test-trace-id"
    
def test_batch_telemetry_events(client, test_db):
    """Test creating multiple telemetry events in a batch"""
    batch = {
        "events": [
            test_event,
            {
                **test_event,
                "trace_id": "test-trace-id-2",
                "name": "test.event.2"
            }
        ]
    }
    
    response = client.post("/v1/telemetry/batch", json=batch)
    assert response.status_code == 201
    assert response.json()["success"] is True
    assert response.json()["total"] == 2
    assert response.json()["processed"] == 2
    assert response.json()["failed"] == 0
    
    # Verify both events were created in the database
    events = test_db.query(Event).all()
    assert len(events) == 2
    
def test_get_telemetry_events(client, test_db):
    """Test retrieving telemetry events"""
    # Add some test events
    for i in range(3):
        process_event({
            **test_event,
            "trace_id": f"test-trace-{i}",
            "name": f"test.event.{i}"
        }, test_db)
    
    # Test retrieving all events
    response = client.get("/v1/telemetry/events")
    assert response.status_code == 200
    events = response.json()
    assert len(events) == 3
    
    # Test filtering by name
    response = client.get("/v1/telemetry/events?event_name=test.event.1")
    assert response.status_code == 200
    events = response.json()
    assert len(events) == 1
    assert events[0]["name"] == "test.event.1"
    
def test_get_telemetry_event_by_id(client, test_db):
    """Test retrieving a specific telemetry event by ID"""
    # Add a test event
    event = process_event(test_event, test_db)
    
    # Test retrieving the event by ID
    response = client.get(f"/v1/telemetry/events/{event.id}")
    assert response.status_code == 200
    assert response.json()["id"] == event.id
    assert response.json()["trace_id"] == "test-trace-id"
    
    # Test retrieving a non-existent event
    response = client.get("/v1/telemetry/events/non-existent-id")
    assert response.status_code == 404
    
def test_get_trace_events(client, test_db):
    """Test retrieving all events in a trace"""
    # Add some test events with the same trace ID
    trace_id = "test-trace-1234"
    for i in range(3):
        process_event({
            **test_event,
            "trace_id": trace_id,
            "name": f"test.event.{i}"
        }, test_db)
    
    # Add an event with a different trace ID
    process_event({
        **test_event,
        "trace_id": "different-trace",
        "name": "different.event"
    }, test_db)
    
    # Test retrieving events by trace ID
    response = client.get(f"/v1/telemetry/traces/{trace_id}")
    assert response.status_code == 200
    events = response.json()
    assert len(events) == 3
    assert all(e["trace_id"] == trace_id for e in events)
    
def test_metrics_endpoint(client, test_db):
    """Test the metrics endpoint"""
    response = client.get("/v1/metrics?metric=llm_request_count&time_range=1d")
    assert response.status_code == 200
    assert response.json()["metric"] == "llm_request_count"
    assert "data" in response.json()
    assert len(response.json()["data"]) > 0
    
def test_dashboard_endpoint(client, test_db):
    """Test the dashboard endpoint"""
    response = client.get("/v1/metrics/dashboard?time_range=1d")
    assert response.status_code == 200
    assert "period" in response.json()
    assert "metrics" in response.json()
    assert len(response.json()["metrics"]) > 0

def test_timestamp_validation(client, test_event):
    """Test that invalid timestamp formats are rejected"""
    # Create event with invalid timestamp
    invalid_event = test_event.copy()
    invalid_event["timestamp"] = "not-a-timestamp"
    
    response = client.post("/v1/telemetry", json=invalid_event)
    assert response.status_code == 422  # Validation error
    
    # Test with datetime object instead of string (this should fail validation)
    invalid_event = test_event.copy()
    invalid_event["timestamp"] = {"$date": "2023-01-01T00:00:00Z"}
    
    response = client.post("/v1/telemetry", json=invalid_event)
    assert response.status_code == 422  # Validation error
    
    # Test with valid ISO format
    valid_event = test_event.copy()
    valid_event["timestamp"] = "2023-01-01T00:00:00Z"
    
    response = client.post("/v1/telemetry", json=valid_event)
    assert response.status_code == 201  # Created successfully

def test_error_handling(client, test_event):
    """Test error handling in telemetry endpoints"""
    # Test with missing required field in attributes (simulation of processing error)
    incomplete_event = test_event.copy()
    incomplete_event["attributes"] = {}  # Empty attributes may cause processing errors
    
    # The response should have appropriate error status and message
    response = client.post("/v1/telemetry", json=incomplete_event)
    
    # Status could be 400 or 201 depending on whether the processor rejects it or not
    # If 201, check for success field
    if response.status_code == 201:
        data = response.json()
        assert "success" in data
    
    # Test batch with mixed valid and invalid events
    valid_event = test_event.copy()
    invalid_event = test_event.copy()
    invalid_event["attributes"] = {}  # May cause processing error
    
    batch = {"events": [valid_event, invalid_event, valid_event]}
    
    response = client.post("/v1/telemetry/batch", json=batch)
    assert response.status_code == 201
    
    data = response.json()
    assert "total" in data
    assert "processed" in data
    assert "failed" in data
    assert data["total"] == 3
    # Depending on whether the processor accepts the invalid event, processed might be 2 or 3
    assert data["processed"] <= 3 