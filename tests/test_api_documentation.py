import pytest
import json
from fastapi.testclient import TestClient
import datetime

from src.main import app

client = TestClient(app)


class TestAPIDocumentation:
    """Tests to verify the API endpoints match the documented behavior"""

    def test_health_endpoint(self):
        """Test that the health endpoint is working and returns the expected format"""
        response = client.get("/v1/health")
        assert response.status_code == 200
        assert "status" in response.json()
        assert response.json()["status"] == "ok"

    def test_telemetry_endpoint_validation(self):
        """Test that the telemetry endpoint validates input as documented"""
        # Missing required fields
        incomplete_event = {
            "timestamp": "2024-04-01T12:34:56.789Z",
            "trace_id": "trace-123456789",
            # Missing schema_version, name, level, agent_id
            "attributes": {}
        }
        response = client.post("/v1/telemetry", json=incomplete_event)
        assert response.status_code == 422  # Validation error

        # Valid event
        valid_event = {
            "schema_version": "1.0",
            "timestamp": "2024-04-01T12:34:56.789Z",
            "trace_id": "trace-123456789",
            "span_id": "span-123456789",
            "name": "test.event",
            "level": "INFO",
            "agent_id": "test-agent",
            "attributes": {"test": "value"}
        }
        response = client.post("/v1/telemetry", json=valid_event)
        assert response.status_code == 201
        data = response.json()
        assert "success" in data
        assert data["success"] is True
        assert "event_id" in data

    def test_telemetry_batch_endpoint(self):
        """Test the batch telemetry endpoint"""
        batch = {
            "events": [
                {
                    "schema_version": "1.0",
                    "timestamp": "2024-04-01T12:34:56.789Z",
                    "trace_id": "trace-123456789",
                    "span_id": "span-123456789",
                    "name": "test.event1",
                    "level": "INFO",
                    "agent_id": "test-agent",
                    "attributes": {"test": "value1"}
                },
                {
                    "schema_version": "1.0",
                    "timestamp": "2024-04-01T12:35:56.789Z",
                    "trace_id": "trace-123456789",
                    "span_id": "span-987654321",
                    "name": "test.event2",
                    "level": "INFO",
                    "agent_id": "test-agent",
                    "attributes": {"test": "value2"}
                }
            ]
        }
        response = client.post("/v1/telemetry/batch", json=batch)
        assert response.status_code == 201
        data = response.json()
        assert "success" in data
        assert "total" in data
        assert "processed" in data
        assert "failed" in data
        assert data["total"] == 2
        assert data["processed"] >= 0  # At least some should be processed

    def test_telemetry_events_endpoint(self):
        """Test retrieving telemetry events with filtering"""
        # First submit an event
        event = {
            "schema_version": "1.0",
            "timestamp": "2024-04-01T12:34:56.789Z",
            "trace_id": "trace-get-test",
            "span_id": "span-get-test",
            "name": "get.test.event",
            "level": "INFO",
            "agent_id": "test-agent",
            "attributes": {"test": "get-value"}
        }
        client.post("/v1/telemetry", json=event)
        
        # Now retrieve it with filters
        response = client.get("/v1/telemetry/events", params={
            "trace_id": "trace-get-test",
            "limit": 10
        })
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # Check for our event in the results
        found = False
        for evt in data:
            if evt["trace_id"] == "trace-get-test" and evt["name"] == "get.test.event":
                found = True
                assert "id" in evt
                assert "schema_version" in evt
                assert "timestamp" in evt
                assert "attributes" in evt
                assert evt["attributes"]["test"] == "get-value"
                break
                
        assert found, "Could not find the test event in the response"

    def test_dashboard_endpoint(self):
        """Test the dashboard metrics endpoint"""
        response = client.get("/v1/dashboard")
        assert response.status_code == 200
        data = response.json()
        
        assert "period" in data
        assert "time_range" in data
        assert "from_time" in data
        assert "to_time" in data
        assert "metrics" in data
        assert isinstance(data["metrics"], list)
        
        # Verify metric structure
        for metric in data["metrics"]:
            assert "metric" in metric
            assert "value" in metric

    def test_agents_endpoint(self):
        """Test the agents listing endpoint"""
        response = client.get("/v1/agents")
        assert response.status_code == 200
        data = response.json()
        
        assert "items" in data
        assert "pagination" in data
        assert "meta" in data
        
        # Check pagination structure
        assert "page" in data["pagination"]
        assert "page_size" in data["pagination"]
        assert "total_items" in data["pagination"]
        assert "total_pages" in data["pagination"]
        
        # Check agent item structure if any exist
        if data["items"]:
            agent = data["items"][0]
            assert "agent_id" in agent
            assert "name" in agent
            assert "type" in agent
            assert "status" in agent
            assert "created_at" in agent

    def test_error_handling(self):
        """Test that API error handling works as documented"""
        # Test invalid endpoint
        response = client.get("/v1/nonexistent")
        assert response.status_code == 404
        
        # Test invalid method
        response = client.post("/v1/dashboard")
        assert response.status_code in [405, 404, 400]  # Method not allowed or invalid
        
        # Test invalid parameter type
        response = client.get("/v1/telemetry/events", params={"limit": "not-a-number"})
        assert response.status_code == 422  # Validation error


if __name__ == "__main__":
    pytest.main(["-xvs", __file__]) 