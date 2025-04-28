"""
Tests for the security event processing implementation.

This module tests that security events are properly processed
and stored in the database with the correct fields.
"""
import pytest
import json
from datetime import datetime
from unittest.mock import MagicMock, patch

from sqlalchemy.orm import Session

from src.models.security_alert import SecurityAlert
from src.models.event import Event
from src.services.security_event_processor import process_security_event


@pytest.fixture
def sample_security_event():
    """Fixture providing a sample security event in OpenTelemetry format."""
    return {
        "schema_version": "1.0",
        "timestamp": "2024-04-10T11:43:14.312935", 
        "trace_id": "d773c49ac81542aeb0a19c957c162d53", 
        "span_id": "9b2e531efe9ac834", 
        "parent_span_id": None,
        "name": "security.content.dangerous", 
        "level": "SECURITY_ALERT", 
        "attributes": {
            "llm.vendor": "openai",
            "security.alert_level": "dangerous", 
            "security.keywords": ["credit_card:****1234"], 
            "security.content_sample": "I need help with my credit card ****1234", 
            "security.detection_time": "2024-04-10T11:43:14.312929",
            "security.category": "sensitive_data", 
            "security.severity": "high", 
            "security.description": "Credit card number detected in prompt"
        },
        "agent_id": "test-agent-123"
    }


def test_security_event_processing(sample_security_event):
    """Test that security events are properly processed."""
    # Mock database session
    mock_db = MagicMock(spec=Session)
    
    # Configure the mock to handle flush operations
    def add_mock(obj):
        if isinstance(obj, Event):
            obj.id = 1  # Assign an ID as if it was inserted
    
    mock_db.add.side_effect = add_mock
    
    # Process the security event
    event, security_alert = process_security_event(mock_db, sample_security_event)
    
    # Verify that the event was created correctly
    assert event.name == "security.content.dangerous"
    assert event.level == "SECURITY_ALERT"
    assert event.agent_id == "test-agent-123"
    assert event.trace_id == "d773c49ac81542aeb0a19c957c162d53"
    assert event.span_id == "9b2e531efe9ac834"
    assert event.schema_version == "1.0"
    assert event.event_type == "security"
    
    # Verify that the security alert was created correctly
    assert security_alert.event_id == 1
    assert security_alert.schema_version == "1.0"
    assert security_alert.trace_id == "d773c49ac81542aeb0a19c957c162d53"
    assert security_alert.span_id == "9b2e531efe9ac834"
    assert security_alert.event_name == "security.content.dangerous"
    assert security_alert.log_level == "SECURITY_ALERT"
    assert security_alert.alert_level == "dangerous"
    assert security_alert.category == "sensitive_data"
    assert security_alert.severity == "high"
    assert security_alert.description == "Credit card number detected in prompt"
    assert security_alert.llm_vendor == "openai"
    assert security_alert.content_sample == "I need help with my credit card ****1234"
    assert isinstance(security_alert.keywords, list)
    assert "credit_card:****1234" in security_alert.keywords
    
    # Verify that objects were added to the session (agent, event, security_alert)
    assert mock_db.add.call_count == 3


@pytest.fixture
def sample_security_events_batch():
    """Fixture providing a batch of security events for testing."""
    return [
        {
            "schema_version": "1.0",
            "timestamp": "2024-04-10T11:43:14.312935", 
            "trace_id": "trace1", 
            "span_id": "span1", 
            "name": "security.content.suspicious", 
            "level": "SECURITY_ALERT", 
            "attributes": {
                "llm.vendor": "openai",
                "security.alert_level": "suspicious", 
                "security.category": "prompt_injection", 
                "security.severity": "medium", 
                "security.description": "Potential prompt injection attempt"
            },
            "agent_id": "agent1"
        },
        {
            "schema_version": "1.0",
            "timestamp": "2024-04-10T12:00:00.000000", 
            "trace_id": "trace2", 
            "span_id": "span2", 
            "name": "security.content.critical", 
            "level": "SECURITY_ALERT", 
            "attributes": {
                "llm.vendor": "anthropic",
                "security.alert_level": "critical", 
                "security.category": "malicious_code", 
                "security.severity": "critical", 
                "security.description": "Malicious code execution attempt"
            },
            "agent_id": "agent2"
        }
    ]


def test_from_telemetry_event_method():
    """Test the from_telemetry_event method in SecurityAlert model."""
    # Create mock event
    event = MagicMock(spec=Event)
    event.id = 1
    
    # Create mock session
    mock_db = MagicMock(spec=Session)
    
    # Create sample telemetry data
    telemetry_data = {
        "schema_version": "1.0",
        "trace_id": "trace123",
        "span_id": "span123",
        "parent_span_id": "parent123",
        "name": "security.content.dangerous",
        "level": "SECURITY_ALERT",
        "attributes": {
            "llm.vendor": "openai",
            "security.alert_level": "dangerous",
            "security.keywords": ["ssn:***-**-1234"],
            "security.content_sample": "My SSN is ***-**-1234",
            "security.detection_time": "2024-04-10T15:00:00.000000",
            "security.category": "sensitive_data",
            "security.severity": "high",
            "security.description": "SSN detected in prompt"
        }
    }
    
    # Call the method
    security_alert = SecurityAlert.from_telemetry_event(mock_db, event, telemetry_data)
    
    # Verify the result
    assert security_alert.event_id == 1
    assert security_alert.schema_version == "1.0"
    assert security_alert.trace_id == "trace123"
    assert security_alert.span_id == "span123"
    assert security_alert.parent_span_id == "parent123"
    assert security_alert.event_name == "security.content.dangerous"
    assert security_alert.log_level == "SECURITY_ALERT"
    assert security_alert.alert_level == "dangerous"
    assert security_alert.category == "sensitive_data"
    assert security_alert.severity == "high"
    assert security_alert.description == "SSN detected in prompt"
    assert security_alert.llm_vendor == "openai"
    assert security_alert.content_sample == "My SSN is ***-**-1234"
    assert isinstance(security_alert.keywords, list)
    assert "ssn:***-**-1234" in security_alert.keywords


if __name__ == "__main__":
    pytest.main(["-xvs", __file__]) 