#!/usr/bin/env python3
import json
import requests
import sys

def submit_batch(file_path, api_url="http://localhost:8002"):
    """Submit a batch of telemetry events to the API."""
    
    # Read the raw JSON array from the file
    with open(file_path, 'r') as f:
        events = json.load(f)
    
    # Wrap the array in an object with 'events' key as expected by the API
    batch_payload = {"events": events}
    
    # Submit to the API
    batch_endpoint = f"{api_url}/v1/telemetry/batch"
    print(f"Submitting {len(events)} events to {batch_endpoint}")
    
    try:
        response = requests.post(batch_endpoint, json=batch_payload)
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 201:
            result = response.json()
            print(f"Success: {result['success']}")
            print(f"Total: {result['total']}")
            print(f"Processed: {result['processed']}")
            print(f"Failed: {result['failed']}")
            if result.get('details'):
                print("Failure details:")
                for detail in result['details']:
                    print(f"  - Event {detail['index']}: {detail['error']}")
            return True
        else:
            print("Error response:")
            print(response.text)
            return False
    except Exception as e:
        print(f"Error submitting batch: {str(e)}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python submit_batch.py <json_file_path> [api_url]")
        sys.exit(1)
    
    file_path = sys.argv[1]
    api_url = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:8002"
    
    success = submit_batch(file_path, api_url)
    sys.exit(0 if success else 1) 