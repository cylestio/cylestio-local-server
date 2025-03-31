"""
Tests for security alert trigger associations.

This file tests the functionality for associating security alerts with their triggering events.
"""
import json
import datetime
from datetime import timedelta
import pytest
from unittest.mock import MagicMock, patch

from processing.simple_processor import SimpleProcessor
from models.event import Event
from models.agent import Agent
from models.security_alert import SecurityAlert, SecurityAlertTrigger
from models.llm_interaction import LLMInteraction


@pytest.fixture
def test_agent(db_session):
    """Create a test agent for use in security alert tests."""
    agent = Agent(
        agent_id="test-security-agent",
        name="Test Security Agent",
        first_seen=datetime.datetime.utcnow(),
        last_seen=datetime.datetime.utcnow()
    )
    db_session.add(agent)
    db_session.commit()
    return agent


@pytest.fixture
def test_processor(db_session_factory):
    """Create a SimpleProcessor instance with a session factory."""
    return SimpleProcessor(db_session_factory)


@pytest.fixture
def test_security_event(db_session, test_agent):
    """Create a test security event."""
    event = Event(
        agent_id=test_agent.agent_id,
        timestamp=datetime.datetime.utcnow(),
        schema_version="1.0",
        name="security.alert",
        level="WARNING",
        event_type="security",
        span_id="test-span-id"
    )
    db_session.add(event)
    db_session.commit()
    return event


@pytest.fixture
def test_llm_event(db_session, test_agent):
    """Create a test LLM event that could be a trigger."""
    event = Event(
        agent_id=test_agent.agent_id,
        timestamp=datetime.datetime.utcnow() - timedelta(seconds=30),
        schema_version="1.0",
        name="llm.completion",
        level="INFO",
        event_type="llm",
        span_id="test-span-id"
    )
    db_session.add(event)
    db_session.flush()
    
    # Set the raw_attributes for the LLM interaction
    llm_interaction = LLMInteraction(
        event_id=event.id,
        model="test-model",
        vendor="test-vendor",
        interaction_type="request",
        raw_attributes=json.dumps({
            "prompt": "This is a test prompt containing potentially harmful content"
        })
    )
    db_session.add(llm_interaction)
    db_session.commit()
    
    return event


@pytest.fixture
def test_security_alert(db_session, test_security_event):
    """Create a test security alert."""
    alert = SecurityAlert(
        event_id=test_security_event.id,
        alert_type="suspicious_prompt",
        severity="MEDIUM",
        description="Potentially harmful content detected"
    )
    db_session.add(alert)
    db_session.flush()
    
    # Set raw_attributes after creation
    alert.raw_attributes = json.dumps({
        "vendor": "Azure",
        "suspicious_content": "harmful content detected"
    })
    db_session.commit()
    
    return alert


class TestSecurityAlertTriggers:
    """Tests for security alert trigger associations."""
    
    def test_try_create_security_trigger_span_id_match(self, db_session, test_processor, test_security_alert, test_llm_event):
        """Test creating a security alert trigger with matching span_id."""
        # Call the method
        test_processor._try_create_security_trigger(test_security_alert, db_session)
        
        # Check that a trigger was created
        trigger = db_session.query(SecurityAlertTrigger).filter(
            SecurityAlertTrigger.alert_id == test_security_alert.id
        ).first()
        
        assert trigger is not None
        assert trigger.alert_id == test_security_alert.id
        assert trigger.triggering_event_id == test_llm_event.id
    
    def test_try_create_security_trigger_content_match(self, db_session, test_processor, test_security_alert, test_llm_event):
        """Test creating a security alert trigger with content matching."""
        # Change span_id to break span_id matching
        test_llm_event.span_id = "different-span-id"
        
        # Set up raw attributes for content matching
        test_security_alert.raw_attributes = json.dumps({
            "suspicious_content": "harmful content detected in prompt"
        })
        
        # Make sure timestamps are appropriate for content matching
        # (event should be before alert)
        test_llm_event.timestamp = test_security_alert.event.timestamp - timedelta(seconds=30)
        
        # Verify the event has the right type for content matching
        test_llm_event.event_type = "llm"
        
        # Update LLM interaction raw attributes
        test_llm_event.llm_interaction.raw_attributes = json.dumps({
            "prompt": "This contains harmful content that should be detected"
        })
        db_session.commit()
        
        # Call the method
        test_processor._try_create_security_trigger(test_security_alert, db_session)
        
        # Check that a trigger was created
        trigger = db_session.query(SecurityAlertTrigger).filter(
            SecurityAlertTrigger.alert_id == test_security_alert.id
        ).first()
        
        assert trigger is not None
        assert trigger.alert_id == test_security_alert.id
        assert trigger.triggering_event_id == test_llm_event.id
    
    def test_compare_security_content(self, test_processor, test_security_alert, test_llm_event):
        """Test the content comparison logic."""
        # Ensure the raw_attributes are set properly
        test_security_alert.raw_attributes = json.dumps({
            "suspicious_content": "harmful content detected"
        })
        test_llm_event.llm_interaction.raw_attributes = json.dumps({
            "prompt": "This contains harmful content that should be detected"
        })
        
        # Test a match
        result = test_processor._compare_security_content(test_security_alert, test_llm_event)
        assert result is True
        
        # Test no match
        test_llm_event.llm_interaction.raw_attributes = json.dumps({
            "prompt": "This is a completely innocent prompt"
        })
        result = test_processor._compare_security_content(test_security_alert, test_llm_event)
        assert result is False
    
    def test_check_event_as_security_trigger(self, db_session, test_processor, test_security_alert, test_llm_event):
        """Test retroactively checking an event as a security trigger."""
        # Create a different event that arrives later
        later_event = Event(
            agent_id=test_llm_event.agent_id,
            timestamp=datetime.datetime.utcnow() + timedelta(seconds=30),
            schema_version="1.0",
            name="llm.completion",
            level="INFO",
            event_type="llm",
            span_id=test_security_alert.event.span_id
        )
        db_session.add(later_event)
        db_session.flush()
        
        # Add LLM interaction for the event
        llm_interaction = LLMInteraction(
            event_id=later_event.id,
            model="test-model",
            vendor="test-vendor",
            interaction_type="request",
            raw_attributes=json.dumps({
                "prompt": "This contains harmful content"
            })
        )
        db_session.add(llm_interaction)
        db_session.commit()
        
        # Call the method
        test_processor._check_event_as_security_trigger(later_event, db_session)
        
        # Check that a trigger was created
        trigger = db_session.query(SecurityAlertTrigger).filter(
            SecurityAlertTrigger.alert_id == test_security_alert.id
        ).first()
        
        assert trigger is not None
        assert trigger.alert_id == test_security_alert.id
        assert trigger.triggering_event_id == later_event.id
    
    def test_transform_event_with_security_trigger_check(self, db_session, test_processor, test_security_alert):
        """Test that _transform_event calls _check_event_as_security_trigger."""
        # Create event data
        event_data = {
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "name": "llm.completion",
            "level": "INFO",
            "agent_id": test_security_alert.event.agent_id,
            "span_id": test_security_alert.event.span_id,
            "trace_id": "test-trace-id",  # Add trace_id to avoid NULL constraint error
            "schema_version": "1.0",
            "attributes": {
                "prompt": "This contains harmful content"
            }
        }
        
        # Mock the _check_event_as_security_trigger method
        with patch.object(test_processor, '_check_event_as_security_trigger') as mock_check:
            # Call _transform_event
            event, related_models = test_processor._transform_event(event_data, db_session)
            
            # Check that _check_event_as_security_trigger was called
            mock_check.assert_called_once()
            assert mock_check.call_args[0][0] == event
            assert mock_check.call_args[0][1] == db_session
    
    def test_end_to_end_security_alert_flow(self, db_session, test_processor, test_agent):
        """Test the end-to-end flow of security alert trigger association."""
        # Create an LLM event
        llm_event_data = {
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "name": "llm.completion",
            "level": "INFO",
            "agent_id": test_agent.agent_id,
            "span_id": "test-span-1234",
            "trace_id": "test-trace-1234",
            "schema_version": "1.0",
            "attributes": {
                "prompt": "This contains harmful content that should be detected"
            }
        }
        
        # Process the LLM event
        llm_event, related_models = test_processor._transform_event(llm_event_data, db_session)
        db_session.add(llm_event)
        db_session.commit()
        
        # Add LLM interaction for testing
        llm_interaction = LLMInteraction(
            event_id=llm_event.id,
            model="test-model",
            vendor="test-vendor",
            interaction_type="request",
            raw_attributes=json.dumps({
                "prompt": "This contains harmful content that should be detected"
            })
        )
        db_session.add(llm_interaction)
        db_session.commit()
        
        # Create a security alert event
        security_event_data = {
            "timestamp": (datetime.datetime.utcnow() + timedelta(seconds=10)).isoformat(),
            "name": "security.alert",
            "level": "WARNING",
            "agent_id": test_agent.agent_id,
            "span_id": "test-span-1234",  # Same span_id
            "trace_id": "test-trace-1234",  # Same trace_id
            "schema_version": "1.0",
            "attributes": {
                "alert_type": "suspicious_prompt",
                "severity": "MEDIUM",
                "description": "Potentially harmful content detected",
                "suspicious_content": "harmful content detected"
            }
        }
        
        # Process the security event
        security_event, related_models = test_processor._transform_event(security_event_data, db_session)
        db_session.add(security_event)
        for model in related_models:
            db_session.add(model)
        db_session.commit()
        
        # Find the security alert
        security_alert = db_session.query(SecurityAlert).filter(
            SecurityAlert.event_id == security_event.id
        ).first()
        
        assert security_alert is not None
        
        # Check if a trigger was created
        trigger = db_session.query(SecurityAlertTrigger).filter(
            SecurityAlertTrigger.alert_id == security_alert.id
        ).first()
        
        assert trigger is not None
        assert trigger.alert_id == security_alert.id
        assert trigger.triggering_event_id == llm_event.id
    
    def test_security_alert_before_triggering_event(self, db_session, test_processor, test_agent):
        """Test the case where a security alert arrives before its triggering event."""
        # Create a security alert event first
        security_event_data = {
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "name": "security.alert",
            "level": "WARNING",
            "agent_id": test_agent.agent_id,
            "span_id": "test-span-5678",
            "trace_id": "test-trace-5678",
            "schema_version": "1.0",
            "attributes": {
                "alert_type": "suspicious_prompt",
                "severity": "MEDIUM",
                "description": "Potentially harmful content detected",
                "suspicious_content": "harmful content detected"
            }
        }
        
        # Process the security event
        security_event, related_models = test_processor._transform_event(security_event_data, db_session)
        db_session.add(security_event)
        for model in related_models:
            db_session.add(model)
        db_session.commit()
        
        # Find the security alert
        security_alert = db_session.query(SecurityAlert).filter(
            SecurityAlert.event_id == security_event.id
        ).first()
        
        assert security_alert is not None
        
        # No trigger should exist yet
        trigger = db_session.query(SecurityAlertTrigger).filter(
            SecurityAlertTrigger.alert_id == security_alert.id
        ).first()
        
        assert trigger is None
        
        # Create an LLM event that arrives later
        llm_event_data = {
            "timestamp": (datetime.datetime.utcnow() + timedelta(seconds=30)).isoformat(),
            "name": "llm.completion",
            "level": "INFO",
            "agent_id": test_agent.agent_id,
            "span_id": "test-span-5678",  # Same span_id
            "trace_id": "test-trace-5678",  # Same trace_id
            "schema_version": "1.0",
            "attributes": {
                "prompt": "This contains harmful content that should be detected"
            }
        }
        
        # Process the LLM event
        llm_event, _ = test_processor._transform_event(llm_event_data, db_session)
        db_session.add(llm_event)
        db_session.commit()
        
        # Add LLM interaction for testing
        llm_interaction = LLMInteraction(
            event_id=llm_event.id,
            model="test-model",
            vendor="test-vendor",
            interaction_type="request",
            raw_attributes=json.dumps({
                "prompt": "This contains harmful content that should be detected"
            })
        )
        db_session.add(llm_interaction)
        db_session.commit()
        
        # Check if a trigger was created retroactively
        trigger = db_session.query(SecurityAlertTrigger).filter(
            SecurityAlertTrigger.alert_id == security_alert.id
        ).first()
        
        assert trigger is not None
        assert trigger.alert_id == security_alert.id
        assert trigger.triggering_event_id == llm_event.id 