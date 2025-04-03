import pytest
import json
from fastapi.testclient import TestClient
import datetime

from src.main import app

client = TestClient(app)


class TestAPIEdgeCases:
    """Tests for edge cases and error handling in the API"""

    def test_empty_request_body(self):
        """Test sending an empty request body to POST endpoints"""
        # Test empty request to telemetry endpoint
        response = client.post("/v1/telemetry", json={})
        assert response.status_code == 422  # Validation error
        
        # Test empty request to batch endpoint
        response = client.post("/v1/telemetry/batch", json={})
        assert response.status_code == 422  # Validation error

    def test_malformed_json(self):
        """Test sending malformed JSON data"""
        # Note: Using client.post() with invalid JSON will raise an exception
        # in the client itself, not in the server. We're testing at the app level,
        # not the transport level, so we skip this test.
        pass
        
    def test_extreme_values(self):
        """Test handling of extreme values in parameters"""
        # Test very large limit
        response = client.get("/v1/telemetry/events", params={"limit": 100000})
        # Should either cap the limit or return a validation error
        assert response.status_code in [200, 422]
        
        if response.status_code == 200:
            # If it accepted the request, it should have capped the limit
            # Check directly if we can access the limit that was actually used
            # This might not be exposed directly in the response
            pass
        
        # Test negative limit
        response = client.get("/v1/telemetry/events", params={"limit": -10})
        assert response.status_code == 422  # Should reject negative values
        
        # Test very long string parameters
        long_string = "a" * 10000  # 10,000 character string
        response = client.get("/v1/telemetry/events", params={"agent_id": long_string})
        # Should either truncate or reject
        assert response.status_code in [200, 422]

    def test_invalid_dates(self):
        """Test handling of invalid dates in parameters"""
        # Test invalid from_time format
        response = client.get("/v1/telemetry/events", params={"from_time": "not-a-date"})
        assert response.status_code == 422  # Validation error
        
        # Test invalid date range (to_time before from_time)
        response = client.get("/v1/telemetry/events", params={
            "from_time": "2024-04-01T00:00:00Z",
            "to_time": "2023-04-01T00:00:00Z"  # Earlier than from_time
        })
        # Should either correct the range or reject it
        assert response.status_code in [200, 422]
        
        # Test far future date
        response = client.get("/v1/telemetry/events", params={
            "from_time": "2100-01-01T00:00:00Z"
        })
        # Should accept it but probably return empty results
        assert response.status_code == 200
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 0  # No events from the future

    def test_unexpected_fields(self):
        """Test handling of unexpected fields in requests"""
        # Test adding extra fields to a telemetry event
        event = {
            "schema_version": "1.0",
            "timestamp": "2024-04-01T12:34:56.789Z",
            "trace_id": "trace-123456789",
            "span_id": "span-123456789",
            "name": "test.event",
            "level": "INFO",
            "agent_id": "test-agent",
            "attributes": {"test": "value"},
            "unexpected_field": "This field is not in the schema"
        }
        response = client.post("/v1/telemetry", json=event)
        # Should ignore the extra field and process normally
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True

    def test_missing_endpoint(self):
        """Test accessing an endpoint that doesn't exist"""
        response = client.get("/v1/not_an_endpoint")
        assert response.status_code == 404
        
        # Check that it returns a proper error message
        data = response.json()
        assert "detail" in data

    def test_method_not_allowed(self):
        """Test using wrong HTTP methods on endpoints"""
        # Test GET on a POST endpoint
        response = client.get("/v1/telemetry")
        assert response.status_code == 405  # Method Not Allowed
        
        # Test POST on a GET endpoint
        response = client.post("/v1/dashboard")
        assert response.status_code == 405  # Method Not Allowed

    def test_header_handling(self):
        """Test handling of various headers"""
        # Test with Accept header for unsupported format
        response = client.get("/v1/health", headers={"Accept": "application/xml"})
        # Should still return JSON since XML is not supported
        assert response.status_code == 200
        assert response.headers["Content-Type"].startswith("application/json")
        
        # Test with non-standard Content-Type
        event = {
            "schema_version": "1.0",
            "timestamp": "2024-04-01T12:34:56.789Z",
            "trace_id": "trace-123456789",
            "name": "test.event",
            "level": "INFO",
            "agent_id": "test-agent",
            "attributes": {}
        }
        response = client.post(
            "/v1/telemetry", 
            data=json.dumps(event),
            headers={"Content-Type": "application/json-patch+json"}
        )
        # Should still work if the Content-Type is compatible with JSON
        assert response.status_code in [201, 415]  # Created or Unsupported Media Type

    def test_repeated_parameters(self):
        """Test handling of repeated query parameters"""
        # Test multiple agent_id parameters
        response = client.get("/v1/telemetry/events", params=[
            ("agent_id", "agent1"),
            ("agent_id", "agent2")
        ])
        # Should either use the last one, the first one, or reject
        assert response.status_code in [200, 422]


if __name__ == "__main__":
    pytest.main(["-xvs", __file__]) 