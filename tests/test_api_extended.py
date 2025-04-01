import pytest
import uuid
from fastapi.testclient import TestClient
import json
from datetime import datetime, timezone, timedelta

from src.main import app
from src.processing.simple_processor import process_event
from src.database.session import get_db
from src.models.event import Event
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Setup in-memory test database with a unique identifier
TEST_DATABASE_URL = f"sqlite:///:memory:{uuid.uuid4()}"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Sample test data
def create_test_event(name="test.event", level="INFO", agent_id="test-agent", trace_id=None):
    """Helper function to create test event data"""
    if trace_id is None:
        trace_id = f"trace-{datetime.now().timestamp()}"
        
    return {
        "schema_version": "1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "trace_id": trace_id,
        "span_id": f"span-{datetime.now().timestamp()}",
        "parent_span_id": None,
        "name": name,
        "level": level,
        "agent_id": agent_id,
        "attributes": {
            "test.attribute": "test-value",
            "llm.request.model": "test-model" if "llm" in name else None,
            "llm.request.tokens": 100 if "llm" in name else None,
            "llm.response.time_ms": 1500 if "llm" in name else None,
            "tool.name": "test-tool" if "tool" in name else None,
            "status": "success" if "success" in name else ("error" if "error" in name else "success")
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

@pytest.fixture
def populated_db(test_db):
    """Populate database with test data"""
    # Create a variety of test events
    events = [
        # LLM events
        create_test_event(name="llm.request", agent_id="agent1"),
        create_test_event(name="llm.response", agent_id="agent1"),
        create_test_event(name="llm.request", agent_id="agent2"),
        create_test_event(name="llm.error", level="ERROR", agent_id="agent2"),
        
        # Tool events
        create_test_event(name="tool.execution", agent_id="agent1"),
        create_test_event(name="tool.success", agent_id="agent1"),
        create_test_event(name="tool.error", level="ERROR", agent_id="agent2"),
        
        # Session events
        create_test_event(name="session.start", agent_id="agent1"),
        create_test_event(name="session.end", agent_id="agent1"),
        create_test_event(name="session.start", agent_id="agent2"),
        
        # Other events with same trace ID
        create_test_event(name="chain.start", agent_id="agent1", trace_id="shared-trace"),
        create_test_event(name="chain.step", agent_id="agent1", trace_id="shared-trace"),
        create_test_event(name="chain.end", agent_id="agent1", trace_id="shared-trace")
    ]
    
    # Process events
    for event in events:
        process_event(event, test_db)
    
    return test_db

def test_telemetry_event_validation(client):
    """Test validation for telemetry event creation"""
    # Missing required fields
    invalid_event = {
        "schema_version": "1.0",
        # Missing timestamp
        "trace_id": "test-trace-id",
        # Missing name
        "level": "INFO",
        "agent_id": "test-agent"
    }
    
    response = client.post("/v1/telemetry", json=invalid_event)
    assert response.status_code == 422  # Validation error
    
    # Invalid event level
    invalid_level_event = create_test_event(level="INVALID_LEVEL")
    response = client.post("/v1/telemetry", json=invalid_level_event)
    assert response.status_code == 422  # Validation error

def test_batch_size_validation(client):
    """Test batch size validation"""
    # Create a batch with more than 1000 events
    events = [create_test_event() for _ in range(1001)]
    batch = {"events": events}
    
    response = client.post("/v1/telemetry/batch", json=batch)
    assert response.status_code == 422  # Validation error
    assert "Batch size exceeds maximum" in response.text

def test_telemetry_pagination(client, populated_db):
    """Test pagination for telemetry events retrieval"""
    # Test with limit and offset
    response = client.get("/v1/telemetry/events?limit=5&offset=0")
    assert response.status_code == 200
    assert len(response.json()) == 5
    
    response = client.get("/v1/telemetry/events?limit=5&offset=5")
    assert response.status_code == 200
    assert len(response.json()) == 5
    
    # The first and second pages should have different events
    first_page = client.get("/v1/telemetry/events?limit=5&offset=0").json()
    second_page = client.get("/v1/telemetry/events?limit=5&offset=5").json()
    
    first_ids = [event["id"] for event in first_page]
    second_ids = [event["id"] for event in second_page]
    
    # No overlapping IDs between pages
    assert not set(first_ids).intersection(set(second_ids))

def test_telemetry_filtering(client, populated_db):
    """Test filtering for telemetry events retrieval"""
    # Filter by agent_id
    response = client.get("/v1/telemetry/events?agent_id=agent1")
    assert response.status_code == 200
    events = response.json()
    assert all(e["agent_id"] == "agent1" for e in events)
    
    # Filter by level
    response = client.get("/v1/telemetry/events?level=ERROR")
    assert response.status_code == 200
    events = response.json()
    assert all(e["level"] == "ERROR" for e in events)
    
    # Filter by event_name
    response = client.get("/v1/telemetry/events?event_name=llm.request")
    assert response.status_code == 200
    events = response.json()
    assert all(e["name"] == "llm.request" for e in events)
    
    # Filter by trace_id
    response = client.get("/v1/telemetry/events?trace_id=shared-trace")
    assert response.status_code == 200
    events = response.json()
    assert all(e["trace_id"] == "shared-trace" for e in events)
    
    # Combined filters
    response = client.get("/v1/telemetry/events?agent_id=agent1&level=INFO")
    assert response.status_code == 200
    events = response.json()
    assert all(e["agent_id"] == "agent1" and e["level"] == "INFO" for e in events)

def test_trace_endpoint(client, populated_db):
    """Test retrieving events by trace ID"""
    response = client.get("/v1/telemetry/traces/shared-trace")
    assert response.status_code == 200
    events = response.json()
    assert len(events) == 3  # We created 3 events with this trace ID
    assert all(e["trace_id"] == "shared-trace" for e in events)
    
    # Check for ordering by timestamp
    timestamps = [datetime.fromisoformat(e["timestamp"]) for e in events]
    assert timestamps == sorted(timestamps)

def test_metrics_validation(client):
    """Test validation for metrics queries"""
    # Invalid time range
    response = client.get("/v1/metrics?metric=llm_request_count&time_range=invalid")
    assert response.status_code == 400
    
    # Invalid interval
    response = client.get("/v1/metrics?metric=llm_request_count&time_range=1d&interval=invalid")
    assert response.status_code == 400
    
    # Invalid metric type
    response = client.get("/v1/metrics?metric=invalid_metric&time_range=1d")
    assert response.status_code == 400

def test_metrics_dashboard(client, populated_db):
    """Test dashboard metrics endpoint"""
    response = client.get("/v1/metrics/dashboard?time_range=1d")
    assert response.status_code == 200
    data = response.json()
    
    assert "period" in data
    assert "metrics" in data
    
    # Check that all expected metrics are present
    metrics = {m["metric"] for m in data["metrics"]}
    expected_metrics = {
        "llm_request_count", "llm_token_usage", "llm_avg_response_time",
        "tool_execution_count", "error_count", "session_count"
    }
    assert metrics.issuperset(expected_metrics)
    
    # Test filtering by agent
    response = client.get("/v1/metrics/dashboard?time_range=1d&agent_id=agent1")
    assert response.status_code == 200

def test_agent_metrics(client, populated_db):
    """Test agent metrics endpoint"""
    response = client.get("/v1/metrics/agents?time_range=1d")
    assert response.status_code == 200
    data = response.json()
    
    assert isinstance(data, list)
    assert len(data) > 0
    
    # Check data structure
    for agent_metric in data:
        assert "agent_id" in agent_metric
        assert "llm_requests" in agent_metric
        assert "timestamp" in agent_metric

def test_all_metric_types(client, populated_db):
    """Test all available metric types"""
    metric_types = [
        "llm_request_count", "llm_token_usage", "llm_response_time",
        "tool_execution_count", "tool_success_rate", "error_count", "session_count"
    ]
    
    for metric in metric_types:
        response = client.get(f"/v1/metrics?metric={metric}&time_range=1d")
        assert response.status_code == 200, f"Failed for metric: {metric}"
        data = response.json()
        
        assert data["metric"] == metric
        assert "from_time" in data
        assert "to_time" in data
        assert "data" in data
        assert len(data["data"]) > 0

def test_error_handling(client):
    """Test error handling in the API"""
    # Test 404 for non-existent event
    response = client.get("/v1/telemetry/events/non-existent-id")
    assert response.status_code == 404
    assert "error" in response.json()
    
    # Test 404 for non-existent endpoint
    response = client.get("/v1/non-existent")
    assert response.status_code == 404
    assert "error" in response.json() or "detail" in response.json() 