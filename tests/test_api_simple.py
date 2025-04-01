import pytest
from fastapi import FastAPI, HTTPException, Depends, Query, Path
from fastapi.testclient import TestClient
from pydantic import BaseModel, field_validator, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

# Create a minimal FastAPI app for testing
app = FastAPI()

# Models for request validation
class TelemetryEvent(BaseModel):
    schema_version: str = "1.0"
    timestamp: str
    trace_id: str
    span_id: Optional[str] = None
    parent_span_id: Optional[str] = None
    name: str
    level: str
    agent_id: str
    attributes: Optional[Dict[str, Any]] = None

    @field_validator('level')
    def validate_level(cls, v):
        allowed_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v not in allowed_levels:
            raise ValueError(f"Level must be one of {allowed_levels}")
        return v

class TelemetryBatch(BaseModel):
    events: List[TelemetryEvent]
    
    @field_validator('events')
    def validate_batch_size(cls, v):
        if len(v) > 1000:
            raise ValueError("Batch size exceeds maximum of 1000 events")
        return v

# Mock database
events_db = {}

# Routes
@app.get("/v1/health")
def health_check():
    return {"status": "ok"}

@app.post("/v1/telemetry")
def create_event(event: TelemetryEvent):
    event_id = str(uuid.uuid4())
    events_db[event_id] = event.model_dump()
    return {"id": event_id, "status": "created"}

@app.post("/v1/telemetry/batch")
def create_batch(batch: TelemetryBatch):
    event_ids = []
    for event in batch.events:
        event_id = str(uuid.uuid4())
        events_db[event_id] = event.model_dump()
        event_ids.append(event_id)
    
    return {"ids": event_ids, "count": len(event_ids)}

@app.get("/v1/telemetry/events/{event_id}")
def get_event(event_id: str):
    if event_id not in events_db:
        raise HTTPException(status_code=404, detail={"error": "Event not found"})
    return events_db[event_id]

@app.get("/v1/telemetry/events")
def list_events(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    agent_id: Optional[str] = None,
    level: Optional[str] = None,
    event_name: Optional[str] = None,
    trace_id: Optional[str] = None
):
    filtered_events = []
    
    for event_id, event in events_db.items():
        if agent_id and event["agent_id"] != agent_id:
            continue
        if level and event["level"] != level:
            continue
        if event_name and event["name"] != event_name:
            continue
        if trace_id and event["trace_id"] != trace_id:
            continue
        
        filtered_events.append({"id": event_id, **event})
    
    # Apply pagination
    paginated = filtered_events[offset:offset+limit]
    return paginated

@app.get("/v1/metrics/dashboard")
def dashboard(time_range: str = "1d", agent_id: Optional[str] = None):
    return {
        "period": {"from": "2023-01-01", "to": "2023-01-02"},
        "metrics": [
            {"metric": "llm_request_count", "value": 100},
            {"metric": "llm_token_usage", "value": 1000},
            {"metric": "llm_avg_response_time", "value": 500},
            {"metric": "tool_execution_count", "value": 50},
            {"metric": "error_count", "value": 10},
            {"metric": "session_count", "value": 5}
        ]
    }

@app.get("/v1/metrics")
def get_metric(
    metric: str,
    time_range: str = "1d",
    interval: Optional[str] = None,
    agent_id: Optional[str] = None
):
    valid_metrics = [
        "llm_request_count", "llm_token_usage", "llm_response_time",
        "tool_execution_count", "tool_success_rate", "error_count", "session_count"
    ]
    
    if metric not in valid_metrics:
        raise HTTPException(status_code=400, detail={"error": f"Invalid metric. Must be one of {valid_metrics}"})
    
    return {
        "metric": metric,
        "from_time": "2023-01-01T00:00:00Z",
        "to_time": "2023-01-02T00:00:00Z",
        "interval": interval or "1h",
        "data": [
            {"timestamp": "2023-01-01T00:00:00Z", "value": 10},
            {"timestamp": "2023-01-01T01:00:00Z", "value": 15},
            {"timestamp": "2023-01-01T02:00:00Z", "value": 20}
        ]
    }

@app.get("/v1/metrics/agents")
def get_agent_metrics(time_range: str = "1d"):
    return [
        {
            "agent_id": "agent1",
            "llm_requests": 50,
            "tool_executions": 25,
            "errors": 5,
            "timestamp": "2023-01-01T00:00:00Z"
        },
        {
            "agent_id": "agent2",
            "llm_requests": 30,
            "tool_executions": 15,
            "errors": 2,
            "timestamp": "2023-01-01T00:00:00Z"
        }
    ]

@app.get("/v1/telemetry/traces/{trace_id}")
def get_trace(trace_id: str):
    filtered_events = []
    
    for event_id, event in events_db.items():
        if event["trace_id"] == trace_id:
            filtered_events.append({"id": event_id, **event})
    
    if not filtered_events:
        raise HTTPException(status_code=404, detail={"error": "Trace not found"})
    
    return filtered_events

# Create test client
client = TestClient(app)

def test_health_endpoint():
    """Test the health check endpoint"""
    response = client.get("/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "ok"

def test_telemetry_creation():
    """Test creating telemetry events"""
    valid_event = {
        "schema_version": "1.0",
        "timestamp": datetime.now().isoformat(),
        "trace_id": "trace-123",
        "span_id": "span-123",
        "name": "test.event",
        "level": "INFO",
        "agent_id": "test-agent",
        "attributes": {
            "test.attribute": "test-value"
        }
    }
    
    response = client.post("/v1/telemetry", json=valid_event)
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert "status" in data
    assert data["status"] == "created"
    
    # Test invalid event (missing required field)
    invalid_event = {
        "schema_version": "1.0",
        # Missing timestamp
        "trace_id": "trace-123",
        "name": "test.event",
        "level": "INFO",
        "agent_id": "test-agent"
    }
    
    response = client.post("/v1/telemetry", json=invalid_event)
    assert response.status_code == 422  # Validation error
    
    # Test invalid level
    invalid_level_event = valid_event.copy()
    invalid_level_event["level"] = "INVALID_LEVEL"
    
    response = client.post("/v1/telemetry", json=invalid_level_event)
    assert response.status_code == 422  # Validation error

def test_batch_creation():
    """Test batch event creation"""
    valid_event = {
        "schema_version": "1.0",
        "timestamp": datetime.now().isoformat(),
        "trace_id": "trace-123",
        "span_id": "span-123",
        "name": "test.event",
        "level": "INFO",
        "agent_id": "test-agent",
        "attributes": {
            "test.attribute": "test-value"
        }
    }
    
    # Create a batch with 3 events
    batch = {"events": [valid_event, valid_event, valid_event]}
    
    response = client.post("/v1/telemetry/batch", json=batch)
    assert response.status_code == 200
    data = response.json()
    assert "ids" in data
    assert "count" in data
    assert data["count"] == 3
    assert len(data["ids"]) == 3

def test_metrics_endpoint():
    """Test the metrics endpoint"""
    response = client.get("/v1/metrics?metric=llm_request_count&time_range=1d")
    assert response.status_code == 200
    data = response.json()
    
    assert "metric" in data
    assert data["metric"] == "llm_request_count"
    assert "from_time" in data
    assert "to_time" in data
    assert "data" in data
    assert len(data["data"]) > 0
    
    # Test invalid metric
    response = client.get("/v1/metrics?metric=invalid_metric&time_range=1d")
    assert response.status_code == 400

def test_metrics_dashboard():
    """Test the metrics dashboard endpoint"""
    response = client.get("/v1/metrics/dashboard?time_range=1d")
    assert response.status_code == 200
    data = response.json()
    assert "period" in data
    assert "metrics" in data
    
    # Check that expected metrics are present
    metrics = {m["metric"] for m in data["metrics"]}
    expected_metrics = {
        "llm_request_count", "llm_token_usage", "llm_avg_response_time",
        "tool_execution_count", "error_count", "session_count"
    }
    assert metrics == expected_metrics

def test_agent_metrics():
    """Test the agent metrics endpoint"""
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

def test_event_retrieval():
    """Test retrieving individual events"""
    # First create an event
    valid_event = {
        "schema_version": "1.0",
        "timestamp": datetime.now().isoformat(),
        "trace_id": "trace-retrieval",
        "span_id": "span-retrieval",
        "name": "test.retrieval",
        "level": "INFO",
        "agent_id": "test-agent",
        "attributes": {
            "test.attribute": "test-value"
        }
    }
    
    create_response = client.post("/v1/telemetry", json=valid_event)
    assert create_response.status_code == 200
    event_id = create_response.json()["id"]
    
    # Now retrieve the event
    response = client.get(f"/v1/telemetry/events/{event_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["trace_id"] == "trace-retrieval"
    assert data["name"] == "test.retrieval"
    
    # Test retrieving non-existent event
    response = client.get("/v1/telemetry/events/non-existent-id")
    assert response.status_code == 404

def test_trace_retrieval():
    """Test retrieving events by trace ID"""
    # Create events with the same trace ID
    trace_id = f"trace-{uuid.uuid4()}"
    
    events = [
        {
            "schema_version": "1.0",
            "timestamp": datetime.now().isoformat(),
            "trace_id": trace_id,
            "span_id": f"span-{i}",
            "name": f"test.trace.{i}",
            "level": "INFO",
            "agent_id": "test-agent",
            "attributes": {
                "test.attribute": f"value-{i}"
            }
        }
        for i in range(3)
    ]
    
    # Create the events
    for event in events:
        response = client.post("/v1/telemetry", json=event)
        assert response.status_code == 200
    
    # Now retrieve events by trace ID
    response = client.get(f"/v1/telemetry/traces/{trace_id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    assert all(e["trace_id"] == trace_id for e in data)
    
    # Test retrieving non-existent trace
    response = client.get("/v1/telemetry/traces/non-existent-trace")
    assert response.status_code == 404

def test_event_filtering():
    """Test filtering events"""
    # Create events with different properties
    base_event = {
        "schema_version": "1.0",
        "timestamp": datetime.now().isoformat(),
        "trace_id": "trace-filter",
        "level": "INFO",
        "attributes": {}
    }
    
    # Agent filter events
    agent1_event = {**base_event, "name": "test.agent1", "agent_id": "agent1", "span_id": "span-agent1"}
    agent2_event = {**base_event, "name": "test.agent2", "agent_id": "agent2", "span_id": "span-agent2"}
    
    # Level filter events
    info_event = {**base_event, "name": "test.info", "agent_id": "test-agent", "level": "INFO", "span_id": "span-info"}
    error_event = {**base_event, "name": "test.error", "agent_id": "test-agent", "level": "ERROR", "span_id": "span-error"}
    
    # Create the events
    for event in [agent1_event, agent2_event, info_event, error_event]:
        response = client.post("/v1/telemetry", json=event)
        assert response.status_code == 200
    
    # Test filtering by agent_id
    response = client.get("/v1/telemetry/events?agent_id=agent1")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert all(e["agent_id"] == "agent1" for e in data)
    
    # Test filtering by level
    response = client.get("/v1/telemetry/events?level=ERROR")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert all(e["level"] == "ERROR" for e in data)
    
    # Test combined filters
    response = client.get("/v1/telemetry/events?agent_id=test-agent&level=INFO")
    assert response.status_code == 200
    data = response.json()
    assert all(e["agent_id"] == "test-agent" and e["level"] == "INFO" for e in data)

if __name__ == "__main__":
    pytest.main(["-v", __file__]) 