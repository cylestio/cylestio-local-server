#!/usr/bin/env python
"""
Manual testing script for the API.
This script sends various requests to the API to test its functionality.
"""
import requests
import json
from datetime import datetime, timezone
import argparse

# Default API URL
DEFAULT_API_URL = "http://localhost:8002/v1"

def test_health(api_url):
    """Test the health endpoint"""
    url = f"{api_url}/health"
    print(f"\n=== Testing GET {url} ===")
    
    response = requests.get(url)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200 and response.json().get("status") == "healthy":
        print("✅ Health check passed")
    else:
        print("❌ Health check failed")

def test_telemetry_submit(api_url):
    """Test submitting telemetry events"""
    url = f"{api_url}/telemetry"
    print(f"\n=== Testing POST {url} ===")
    
    # Valid event
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
    
    print(f"Submitting valid event with timestamp: {valid_event['timestamp']}")
    response = requests.post(url, json=valid_event)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 201 and response.json().get("success"):
        event_id = response.json().get("event_id")
        print(f"✅ Event submitted successfully with ID: {event_id}")
    else:
        error_detail = response.json().get("detail", {}) if response.status_code != 422 else response.json()
        print(f"❌ Event submission failed: {json.dumps(error_detail, indent=2)}")
        return
    
    # Try to retrieve the event
    get_url = f"{api_url}/telemetry/events/{event_id}"
    print(f"\n=== Testing GET {get_url} ===")
    response = requests.get(get_url)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2) if response.status_code == 200 else response.text}")
    
    if response.status_code == 200:
        print("✅ Event retrieved successfully")
    else:
        print("❌ Event retrieval failed")

def test_telemetry_batch(api_url):
    """Test submitting batch telemetry events"""
    url = f"{api_url}/telemetry/batch"
    print(f"\n=== Testing POST {url} ===")
    
    # Create a batch of events
    events = []
    for i in range(3):
        events.append({
            "schema_version": "1.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "trace_id": f"batch-trace-{i}",
            "span_id": f"batch-span-{i}",
            "parent_span_id": None,
            "name": f"batch.event.{i}",
            "level": "INFO",
            "agent_id": "test-agent",
            "attributes": {
                "batch.index": i,
                "test.attribute": "test-value"
            }
        })
    
    batch = {"events": events}
    
    print(f"Submitting batch of {len(events)} events...")
    response = requests.post(url, json=batch)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 201 and response.json().get("success"):
        print(f"✅ Batch submitted successfully, processed: {response.json().get('processed')}")
    else:
        print("❌ Batch submission failed")

def test_telemetry_events(api_url):
    """Test retrieving telemetry events"""
    url = f"{api_url}/telemetry/events"
    print(f"\n=== Testing GET {url} ===")
    
    response = requests.get(url)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        events = response.json()
        print(f"Retrieved {len(events)} events")
        if events:
            print(f"First event: {json.dumps(events[0], indent=2)}")
        print("✅ Events retrieved successfully")
    else:
        print(f"Response: {response.text}")
        print("❌ Events retrieval failed")

def test_metrics(api_url):
    """Test the metrics endpoints"""
    # Test LLM request count endpoint
    url = f"{api_url}/metrics/llm/request_count?time_range=1d"
    print(f"\n=== Testing GET {url} ===")
    
    response = requests.get(url)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        print("✅ LLM request count metrics retrieved successfully")
    else:
        print(f"Response: {response.text}")
        print("❌ LLM request count metrics retrieval failed")
    
    # Test tool execution count endpoint
    url = f"{api_url}/metrics/tool/execution_count?time_range=1d"
    print(f"\n=== Testing GET {url} ===")
    
    response = requests.get(url)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        print("✅ Tool execution count metrics retrieved successfully")
    else:
        print(f"Response: {response.text}")
        print("❌ Tool execution count metrics retrieval failed")
        
    # Test agent metrics
    agent_id = "test-agent"  # Use a known agent ID
    url = f"{api_url}/metrics/agent/{agent_id}?time_range=1d"
    print(f"\n=== Testing GET {url} ===")
    
    response = requests.get(url)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        print("✅ Agent metrics retrieved successfully")
    else:
        print(f"Response: {response.text}")
        print("❌ Agent metrics retrieval failed")

def main():
    parser = argparse.ArgumentParser(description="Test the API manually")
    parser.add_argument("--url", default=DEFAULT_API_URL, help=f"API URL (default: {DEFAULT_API_URL})")
    parser.add_argument("--tests", nargs="+", default=["all"], 
                        choices=["all", "health", "telemetry", "batch", "events", "metrics"],
                        help="Tests to run")
    
    args = parser.parse_args()
    
    tests = args.tests
    if "all" in tests:
        tests = ["health", "telemetry", "batch", "events", "metrics"]
    
    print(f"Testing API at {args.url}")
    
    if "health" in tests:
        test_health(args.url)
    
    if "telemetry" in tests:
        test_telemetry_submit(args.url)
    
    if "batch" in tests:
        test_telemetry_batch(args.url)
    
    if "events" in tests:
        test_telemetry_events(args.url)
    
    if "metrics" in tests:
        test_metrics(args.url)

if __name__ == "__main__":
    main() 