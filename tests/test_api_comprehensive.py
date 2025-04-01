"""
Comprehensive tests for the API layer.
"""
import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timezone, timedelta
import json
import uuid

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

@pytest.fixture
def test_event():
    """Create a sample test event"""
    return {
        "schema_version": "1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "trace_id": f"test-trace-{uuid.uuid4()}",
        "span_id": f"test-span-{uuid.uuid4()}",
        "parent_span_id": None,
        "name": "test.event",
        "level": "INFO",
        "agent_id": "test-agent",
        "attributes": {
            "test.attribute": "test-value",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    }

@pytest.fixture
def test_batch(test_event):
    """Create a batch of test events"""
    events = []
    for i in range(3):
        event = test_event.copy()
        event["name"] = f"test.event.{i}"
        event["trace_id"] = f"test-trace-{uuid.uuid4()}"
        event["span_id"] = f"test-span-{uuid.uuid4()}"
        event["attributes"] = {
            "test.attribute": f"test-value-{i}",
            "batch_index": i
        }
        events.append(event)
    return {"events": events}

def test_health_endpoint(client):
    """Test the health endpoint"""
    response = client.get("/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert "timestamp" in response.json()
    assert "version" in response.json()
    assert "dependencies" in response.json()
    assert "database" in response.json()["dependencies"]

def test_telemetry_create(client, test_event):
    """Test creating a single telemetry event"""
    response = client.post("/v1/telemetry", json=test_event)
    assert response.status_code == 201
    assert response.json()["success"] is True
    assert "event_id" in response.json()
    
    # Test retrieving the created event
    event_id = response.json()["event_id"]
    response = client.get(f"/v1/telemetry/events/{event_id}")
    assert response.status_code == 200
    assert response.json()["id"] == event_id
    assert response.json()["name"] == test_event["name"]
    assert response.json()["trace_id"] == test_event["trace_id"]
    assert response.json()["span_id"] == test_event["span_id"]
    assert response.json()["level"] == test_event["level"]
    assert response.json()["agent_id"] == "1"

def test_telemetry_batch_create(client, test_batch):
    """Test creating multiple telemetry events in a batch"""
    response = client.post("/v1/telemetry/batch", json=test_batch)
    assert response.status_code == 201
    assert response.json()["success"] is True
    assert response.json()["total"] == len(test_batch["events"])
    assert response.json()["processed"] == len(test_batch["events"])
    assert response.json()["failed"] == 0
    
    # Verify the events were created
    for i, event in enumerate(test_batch["events"]):
        # Get events for this trace ID
        response = client.get(f"/v1/telemetry/traces/{event['trace_id']}")
        assert response.status_code == 200
        assert len(response.json()) > 0
        
        # Find the matching event
        matching_events = [e for e in response.json() if e["name"] == event["name"]]
        assert len(matching_events) > 0
        
        # Verify event details
        matching_event = matching_events[0]
        assert matching_event["trace_id"] == event["trace_id"]
        assert matching_event["span_id"] == event["span_id"]
        assert matching_event["level"] == event["level"]
        assert matching_event["agent_id"] == "1"

def test_telemetry_retrieve(client, test_event):
    """Test retrieving telemetry events"""
    # Create a test event
    response = client.post("/v1/telemetry", json=test_event)
    assert response.status_code == 201
    event_id = response.json()["event_id"]
    
    # Test retrieving all events
    response = client.get("/v1/telemetry/events")
    assert response.status_code == 200
    assert len(response.json()) > 0
    
    # Test filtering by trace ID
    response = client.get(f"/v1/telemetry/events?trace_id={test_event['trace_id']}")
    assert response.status_code == 200
    assert len(response.json()) > 0
    assert all(e["trace_id"] == test_event["trace_id"] for e in response.json())
    
    # Test filtering by event name
    response = client.get(f"/v1/telemetry/events?event_name={test_event['name']}")
    assert response.status_code == 200
    assert len(response.json()) > 0
    assert all(e["name"] == test_event["name"] for e in response.json())
    
    # Test filtering by agent ID
    response = client.get(f"/v1/telemetry/events?agent_id=1")
    assert response.status_code == 200
    assert len(response.json()) > 0
    assert all(e["agent_id"] == "1" for e in response.json())
    
    # Test pagination
    response = client.get("/v1/telemetry/events?limit=1&offset=0")
    assert response.status_code == 200
    assert len(response.json()) == 1
    
    # Test retrieving a specific event
    response = client.get(f"/v1/telemetry/events/{event_id}")
    assert response.status_code == 200
    assert response.json()["id"] == event_id
    
    # Test retrieving an event that doesn't exist
    response = client.get("/v1/telemetry/events/non-existent-id")
    assert response.status_code == 404

def test_telemetry_traces(client, test_event):
    """Test retrieving trace events"""
    # Create a test event
    response = client.post("/v1/telemetry", json=test_event)
    assert response.status_code == 201
    
    # Test retrieving events for a trace
    response = client.get(f"/v1/telemetry/traces/{test_event['trace_id']}")
    assert response.status_code == 200
    assert len(response.json()) > 0
    assert all(e["trace_id"] == test_event["trace_id"] for e in response.json())
    
    # Test retrieving events for a trace that doesn't exist
    response = client.get("/v1/telemetry/traces/non-existent-trace")
    assert response.status_code == 200
    assert len(response.json()) == 0

def test_metrics_endpoints(client):
    """Test the metrics endpoints"""
    # Test LLM request count
    response = client.get("/v1/metrics/llm/request_count?time_range=1d")
    assert response.status_code == 200
    assert response.json()["metric"] == "llm_request_count"
    assert "data" in response.json()
    
    # Test tool execution count
    response = client.get("/v1/metrics/tool/execution_count?time_range=1d")
    assert response.status_code == 200
    assert response.json()["metric"] == "tool_execution_count"
    assert "data" in response.json()
    
    # Test session count
    response = client.get("/v1/metrics/session/count?time_range=1d")
    assert response.status_code == 200
    assert response.json()["metric"] == "session_count"
    assert "data" in response.json()
    assert isinstance(response.json()["data"][0]["value"], int)
    
    # Test agent metrics
    response = client.get("/v1/metrics/agent/test-agent?time_range=1d")
    assert response.status_code == 200
    assert response.json()["agent_id"] == "test-agent"
    assert "metrics" in response.json()

def test_error_handling(client, test_event):
    """Test error handling in the API"""
    # Test validation error - missing required field
    invalid_event = test_event.copy()
    del invalid_event["timestamp"]
    
    response = client.post("/v1/telemetry", json=invalid_event)
    assert response.status_code == 400
    
    # Test retrieving non-existent event
    response = client.get("/v1/telemetry/events/non-existent-id")
    assert response.status_code == 404
    
    # Test 404 for non-existent endpoint
    response = client.get("/v1/non-existent-endpoint")
    assert response.status_code == 404 