import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timezone

from src.main import app

client = TestClient(app)

def test_health_endpoint():
    """Test the health check endpoint"""
    response = client.get("/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "ok"

def test_api_documentation():
    """Test that the API documentation is accessible"""
    response = client.get("/docs")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

def create_test_event(name="test.event", level="INFO", agent_id="test-agent"):
    """Helper function to create test event data"""
    return {
        "schema_version": "1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "trace_id": f"trace-{datetime.now().timestamp()}",
        "span_id": f"span-{datetime.now().timestamp()}",
        "parent_span_id": None,
        "name": name,
        "level": level,
        "agent_id": agent_id,
        "attributes": {
            "test.attribute": "test-value"
        }
    }

def test_telemetry_validation():
    """Test validation for telemetry event creation"""
    # Test with invalid event (missing required fields)
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
    
    # Test with invalid level
    invalid_level_event = create_test_event(level="INVALID_LEVEL")
    response = client.post("/v1/telemetry", json=invalid_level_event)
    assert response.status_code == 422  # Validation error

def test_metrics_endpoints():
    """Test that metrics endpoints return expected structure"""
    # Test dashboard endpoint
    response = client.get("/v1/metrics/dashboard?time_range=1d")
    assert response.status_code == 200
    data = response.json()
    assert "period" in data
    assert "metrics" in data
    
    # Test agent metrics endpoint
    response = client.get("/v1/metrics/agents?time_range=1d")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    
    # Test individual metric endpoint
    response = client.get("/v1/metrics?metric=llm_request_count&time_range=1d")
    assert response.status_code == 200
    data = response.json()
    assert "metric" in data
    assert "from_time" in data
    assert "to_time" in data
    assert "data" in data

def test_error_handling():
    """Test error handling in the API"""
    # Test 404 for non-existent event
    response = client.get("/v1/telemetry/events/non-existent-id")
    assert response.status_code == 404
    assert "error" in response.json()
    
    # Test 404 for non-existent endpoint
    response = client.get("/v1/non-existent")
    assert response.status_code == 404
    assert "error" in response.json() or "detail" in response.json()
    
    # Test invalid time range format
    response = client.get("/v1/metrics?metric=llm_request_count&time_range=invalid")
    assert response.status_code == 400 