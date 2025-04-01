"""
Test utilities for the Cylestio Local Server.

This module provides utility functions for testing.
"""
import json
import datetime
import pytest
from pathlib import Path


def generate_test_event_json():
    """
    Generate a test event JSON object.
    """
    return {
        "name": "test.event.name",
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "agent_id": "test-agent",
        "event_type": "test",
        "level": "INFO",
        "schema_version": "1.0",
        "attributes": {
            "test_attribute": "test_value"
        }
    }


def load_sample_events(max_events=None):
    """
    Load sample events from example_records.json file.
    
    Args:
        max_events: Maximum number of events to load (None for all)
        
    Returns:
        List of event dictionaries
    """
    example_file = Path("example_records.json")
    if not example_file.exists():
        pytest.skip("example_records.json not found, skipping test")
        
    events = []
    with open(example_file, 'r') as f:
        for i, line in enumerate(f):
            if max_events is not None and i >= max_events:
                break
                
            try:
                event_data = json.loads(line)
                events.append(event_data)
            except json.JSONDecodeError:
                continue
                
    if not events:
        pytest.skip("No events found in example_records.json")
        
    return events 