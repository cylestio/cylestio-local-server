import pytest
import requests
import subprocess
import time
import os
import signal
import sys
import json
from datetime import datetime, timezone

def test_api_endpoints():
    """
    Test basic API endpoints by starting the server and making HTTP requests.
    This is a minimal test that doesn't rely on importing the app directly,
    which avoids SQLAlchemy model registration issues.
    """
    # Start the server in a subprocess
    server_process = None
    
    try:
        # Start the server with the correct Python path
        # Change working directory to the root directory so imports work
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        os.chdir(project_root)
        
        # Run the server as a module
        cmd = [sys.executable, "-m", "uvicorn", "src.main:app", "--host", "127.0.0.1", "--port", "8001"]
        server_process = subprocess.Popen(cmd)
        
        # Wait for the server to start
        time.sleep(3)
        
        # Base URL (using port 8001 to avoid conflicts)
        base_url = "http://127.0.0.1:8001"
        
        print(f"Testing API at {base_url}")
        
        # Test health endpoint
        health_response = requests.get(f"{base_url}/v1/health")
        assert health_response.status_code == 200
        health_data = health_response.json()
        assert "status" in health_data
        assert health_data["status"] == "ok"
        
        print("Health endpoint test passed ✓")
        
        # Test metrics dashboard endpoint
        dashboard_response = requests.get(f"{base_url}/v1/metrics/dashboard?time_range=1d")
        assert dashboard_response.status_code == 200
        dashboard_data = dashboard_response.json()
        assert "period" in dashboard_data
        assert "metrics" in dashboard_data
        
        print("Metrics dashboard endpoint test passed ✓")
        
        # Test creating a telemetry event with invalid data (validation)
        invalid_event = {
            "schema_version": "1.0",
            # Missing required fields
            "level": "INFO",
            "agent_id": "test-agent"
        }
        create_response = requests.post(f"{base_url}/v1/telemetry", json=invalid_event)
        assert create_response.status_code == 422  # Validation error
        
        print("Invalid event validation test passed ✓")
        
        # Test a valid event creation
        valid_event = {
            "schema_version": "1.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "trace_id": f"trace-{datetime.now().timestamp()}",
            "span_id": f"span-{datetime.now().timestamp()}",
            "name": "test.event",
            "level": "INFO",
            "agent_id": "test-agent",
            "attributes": {
                "test.attribute": "test-value"
            }
        }
        
        # Note: This might return 200 or 201 depending on implementation
        valid_response = requests.post(f"{base_url}/v1/telemetry", json=valid_event)
        assert valid_response.status_code in [200, 201]
        
        print("Valid event creation test passed ✓")
        
        # Test error handling for non-existent resource
        not_found_response = requests.get(f"{base_url}/v1/telemetry/events/non-existent-id")
        assert not_found_response.status_code == 404
        
        print("Error handling test passed ✓")
        
        # Test batch event submission
        batch_data = {
            "events": [valid_event]
        }
        batch_response = requests.post(f"{base_url}/v1/telemetry/batch", json=batch_data)
        assert batch_response.status_code in [200, 201]
        
        print("Batch event submission test passed ✓")
        
        # Test metrics endpoints
        metrics_response = requests.get(f"{base_url}/v1/metrics?metric=llm_request_count&time_range=1d")
        assert metrics_response.status_code == 200
        
        print("Metrics endpoint test passed ✓")
        
        # Test agent metrics
        agent_metrics_response = requests.get(f"{base_url}/v1/metrics/agents?time_range=1d")
        assert agent_metrics_response.status_code == 200
        
        print("Agent metrics endpoint test passed ✓")
        
        print("\n🎉 All API tests passed successfully! 🎉")
        
    finally:
        # Clean up the server process
        if server_process:
            print("Shutting down server...")
            server_process.terminate()
            server_process.wait()
            print("Server shutdown complete.")

if __name__ == "__main__":
    test_api_endpoints() 