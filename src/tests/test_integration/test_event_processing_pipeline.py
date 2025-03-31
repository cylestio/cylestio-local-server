"""
Integration tests for the event processing pipeline.

These tests validate the entire event processing pipeline from event ingestion
to database storage, focusing on how components work together.
"""
import json
import datetime
import pytest
import uuid

from models.agent import Agent
from models.event import Event
from models.llm_interaction import LLMInteraction
from models.security_alert import SecurityAlert
from models.framework_event import FrameworkEvent
from models.tool_interaction import ToolInteraction
from models.session import Session as SessionModel
from models.span import Span
from models.trace import Trace

from processing.simple_processor import SimpleProcessor
from tests.test_utils import (
    generate_llm_interaction_data, generate_security_alert_data,
    generate_framework_event_data, generate_tool_interaction_data,
    generate_span_data, generate_session_data, verify_database_state
)


class TestBasicEventProcessing:
    """Test basic event processing for different event types."""
    
    def test_llm_event_processing(self, simple_processor, db_session):
        """Test processing of LLM events."""
        # Create base event data
        agent_id = f"test-agent-{uuid.uuid4()}"
        timestamp = datetime.datetime.utcnow()
        
        # Create a start event
        start_event = {
            "name": "llm.call.start",
            "timestamp": timestamp.isoformat() + "Z",
            "agent_id": agent_id,
            "event_type": "llm",
            "level": "INFO",
            "schema_version": "1.0",
            "attributes": generate_llm_interaction_data("start")["attributes"]
        }
        
        # Process the start event
        start_result = simple_processor.process_event(start_event)
        assert start_result["success"] is True
        
        # Create a finish event
        finish_event = {
            "name": "llm.call.finish",
            "timestamp": (timestamp + datetime.timedelta(seconds=1)).isoformat() + "Z",
            "agent_id": agent_id,
            "event_type": "llm",
            "level": "INFO",
            "schema_version": "1.0",
            "attributes": generate_llm_interaction_data("finish")["attributes"]
        }
        
        # Process the finish event
        finish_result = simple_processor.process_event(finish_event)
        assert finish_result["success"] is True
        
        # Verify database state
        db_state = verify_database_state(db_session, {
            "events": 2,
            "llm_interactions": 2
        })
        assert all(db_state.values())
        
        # Verify LLM interactions details
        llm_interactions = db_session.query(LLMInteraction).all()
        assert len(llm_interactions) == 2
        
        start_interaction = next((i for i in llm_interactions if i.interaction_type == "start"), None)
        finish_interaction = next((i for i in llm_interactions if i.interaction_type == "finish"), None)
        
        assert start_interaction is not None
        assert finish_interaction is not None
        assert start_interaction.vendor == "anthropic"
        assert finish_interaction.vendor == "anthropic"
        assert start_interaction.model == "claude-3-haiku-20240307"
        assert finish_interaction.model == "claude-3-haiku-20240307"
        assert finish_interaction.duration_ms == 450
        assert finish_interaction.input_tokens == 15
        assert finish_interaction.output_tokens == 45
        assert finish_interaction.total_tokens == 60
    
    def test_security_alert_processing(self, simple_processor, db_session):
        """Test processing of security alert events."""
        # Create base event data
        agent_id = f"test-agent-{uuid.uuid4()}"
        timestamp = datetime.datetime.utcnow()
        
        # Create a security alert event
        security_event = {
            "name": "security.alert.detected",
            "timestamp": timestamp.isoformat() + "Z",
            "agent_id": agent_id,
            "event_type": "security",
            "level": "WARN",
            "schema_version": "1.0",
            "attributes": generate_security_alert_data()["attributes"]
        }
        
        # Process the security event
        result = simple_processor.process_event(security_event)
        assert result["success"] is True
        
        # Verify database state
        db_state = verify_database_state(db_session, {
            "events": 1,
            "security_alerts": 1
        })
        assert all(db_state.values())
        
        # Verify security alert details
        security_alerts = db_session.query(SecurityAlert).all()
        assert len(security_alerts) == 1
        
        alert = security_alerts[0]
        assert alert.alert_type == "content_policy_violation"
        assert alert.severity == "medium"
        assert alert.source == "content_filter"
        assert alert.details["policy"] == "harmful_content"
        assert alert.details["score"] == 0.85
        assert alert.flagged_content == "This is potentially harmful content"
    
    def test_framework_event_processing(self, simple_processor, db_session):
        """Test processing of framework events."""
        # Create base event data
        agent_id = f"test-agent-{uuid.uuid4()}"
        timestamp = datetime.datetime.utcnow()
        
        # Create a framework event
        framework_event = {
            "name": "framework.component.start",
            "timestamp": timestamp.isoformat() + "Z",
            "agent_id": agent_id,
            "event_type": "framework",
            "level": "INFO",
            "schema_version": "1.0",
            "attributes": generate_framework_event_data("langchain")["attributes"]
        }
        
        # Process the framework event
        result = simple_processor.process_event(framework_event)
        assert result["success"] is True
        
        # Verify database state
        db_state = verify_database_state(db_session, {
            "events": 1,
            "framework_events": 1
        })
        assert all(db_state.values())
        
        # Verify framework event details
        framework_events = db_session.query(FrameworkEvent).all()
        assert len(framework_events) == 1
        
        fw_event = framework_events[0]
        assert fw_event.framework_type == "langchain"
        assert fw_event.framework_version == "0.1.0"
        assert fw_event.component_type == "Chain"
        assert fw_event.component_name == "TestChain"
    
    def test_tool_interaction_processing(self, simple_processor, db_session):
        """Test processing of tool interaction events."""
        # Create base event data
        agent_id = f"test-agent-{uuid.uuid4()}"
        timestamp = datetime.datetime.utcnow()
        
        # Create a start event
        start_event = {
            "name": "tool.execution.start",
            "timestamp": timestamp.isoformat() + "Z",
            "agent_id": agent_id,
            "event_type": "tool",
            "level": "INFO",
            "schema_version": "1.0",
            "attributes": generate_tool_interaction_data("start")["attributes"]
        }
        
        # Process the start event
        start_result = simple_processor.process_event(start_event)
        assert start_result["success"] is True
        
        # Create a finish event
        finish_event = {
            "name": "tool.execution.finish",
            "timestamp": (timestamp + datetime.timedelta(seconds=1)).isoformat() + "Z",
            "agent_id": agent_id,
            "event_type": "tool",
            "level": "INFO",
            "schema_version": "1.0",
            "attributes": generate_tool_interaction_data("finish")["attributes"]
        }
        
        # Process the finish event
        finish_result = simple_processor.process_event(finish_event)
        assert finish_result["success"] is True
        
        # Verify database state
        db_state = verify_database_state(db_session, {
            "events": 2,
            "tool_interactions": 2
        })
        assert all(db_state.values())
        
        # Verify tool interactions details
        tool_interactions = db_session.query(ToolInteraction).all()
        assert len(tool_interactions) == 2
        
        start_interaction = next((i for i in tool_interactions if "start" in i.event.name), None)
        finish_interaction = next((i for i in tool_interactions if "finish" in i.event.name), None)
        
        assert start_interaction is not None
        assert finish_interaction is not None
        assert start_interaction.tool_name == "weather_api"
        assert finish_interaction.tool_name == "weather_api"
        assert start_interaction.tool_input == {"location": "San Francisco, CA"}
        assert finish_interaction.tool_output == {"temperature": 72, "conditions": "sunny"}
        assert finish_interaction.duration_ms == 350
        assert finish_interaction.status == "success"
    
    def test_span_processing(self, simple_processor, db_session):
        """Test processing of span events."""
        # Create base event data
        agent_id = f"test-agent-{uuid.uuid4()}"
        timestamp = datetime.datetime.utcnow()
        
        # Create span data with ID
        span_data, span_id = generate_span_data(is_root=True)
        
        # Create a span event
        span_event = {
            "name": "span.start",
            "timestamp": timestamp.isoformat() + "Z",
            "agent_id": agent_id,
            "event_type": "span",
            "level": "INFO",
            "schema_version": "1.0",
            "attributes": span_data["attributes"]
        }
        
        # Process the span event
        result = simple_processor.process_event(span_event)
        assert result["success"] is True
        
        # Verify database state
        db_state = verify_database_state(db_session, {
            "events": 1,
            "spans": 1
        })
        assert all(db_state.values())
        
        # Verify span details
        spans = db_session.query(Span).all()
        assert len(spans) == 1
        
        span = spans[0]
        assert span.span_id == span_id
        assert span.name == "test_span"
        assert span.start_time is not None
        assert span.parent_id is None  # Root span
    
    def test_session_processing(self, simple_processor, db_session):
        """Test processing of session events."""
        # Create base event data
        agent_id = f"test-agent-{uuid.uuid4()}"
        timestamp = datetime.datetime.utcnow()
        
        # Create session data with ID
        session_data, session_id = generate_session_data()
        
        # Create a session event
        session_event = {
            "name": "session.start",
            "timestamp": timestamp.isoformat() + "Z",
            "agent_id": agent_id,
            "event_type": "session",
            "level": "INFO",
            "schema_version": "1.0",
            "attributes": session_data["attributes"]
        }
        
        # Process the session event
        result = simple_processor.process_event(session_event)
        assert result["success"] is True
        
        # Verify database state
        db_state = verify_database_state(db_session, {
            "events": 1,
            "sessions": 1
        })
        assert all(db_state.values())
        
        # Verify session details
        sessions = db_session.query(SessionModel).all()
        assert len(sessions) == 1
        
        session = sessions[0]
        assert session.session_id == session_id
        assert session.name == "test_session"
        assert session.start_time is not None


class TestComplexEventProcessing:
    """Test processing of complex event sequences with relationships."""
    
    def test_llm_with_security_alert(self, simple_processor, db_session):
        """Test processing of an LLM event followed by a related security alert."""
        # Create base event data
        agent_id = f"test-agent-{uuid.uuid4()}"
        timestamp = datetime.datetime.utcnow()
        
        # Create an LLM event
        llm_event = {
            "name": "llm.call.start",
            "timestamp": timestamp.isoformat() + "Z",
            "agent_id": agent_id,
            "event_type": "llm",
            "level": "INFO",
            "schema_version": "1.0",
            "attributes": generate_llm_interaction_data("start")["attributes"]
        }
        
        # Process the LLM event
        llm_result = simple_processor.process_event(llm_event)
        assert llm_result["success"] is True
        
        # Get the LLM interaction from the database
        llm_interaction = db_session.query(LLMInteraction).first()
        assert llm_interaction is not None
        
        # Create a security alert event that references the LLM interaction
        security_data = generate_security_alert_data()
        security_data["attributes"]["security.alert.related_llm_interaction_id"] = llm_interaction.id
        
        security_event = {
            "name": "security.alert.detected",
            "timestamp": (timestamp + datetime.timedelta(seconds=1)).isoformat() + "Z",
            "agent_id": agent_id,
            "event_type": "security",
            "level": "WARN",
            "schema_version": "1.0",
            "attributes": security_data["attributes"]
        }
        
        # Process the security event
        security_result = simple_processor.process_event(security_event)
        assert security_result["success"] is True
        
        # Verify database state
        db_state = verify_database_state(db_session, {
            "events": 2,
            "llm_interactions": 1,
            "security_alerts": 1
        })
        assert all(db_state.values())
        
        # Verify relationship between security alert and LLM interaction
        security_alert = db_session.query(SecurityAlert).first()
        assert security_alert is not None
        assert security_alert.related_interaction_id == llm_interaction.id
        assert security_alert.related_llm_interaction.id == llm_interaction.id
    
    def test_span_with_children(self, simple_processor, db_session):
        """Test processing of a parent span with child spans."""
        # Create base event data
        agent_id = f"test-agent-{uuid.uuid4()}"
        timestamp = datetime.datetime.utcnow()
        
        # Create a root span
        root_span_data, root_span_id = generate_span_data(is_root=True)
        
        root_event = {
            "name": "span.start",
            "timestamp": timestamp.isoformat() + "Z",
            "agent_id": agent_id,
            "event_type": "span",
            "level": "INFO",
            "schema_version": "1.0",
            "attributes": root_span_data["attributes"]
        }
        
        # Process the root span event
        root_result = simple_processor.process_event(root_event)
        assert root_result["success"] is True
        
        # Create child span data
        child_data = {
            "attributes": {
                "span.id": str(uuid.uuid4()),
                "span.name": "child_span",
                "span.start_time": (timestamp + datetime.timedelta(seconds=1)).isoformat() + "Z",
                "span.parent_id": root_span_id
            }
        }
        
        child_event = {
            "name": "span.start",
            "timestamp": (timestamp + datetime.timedelta(seconds=1)).isoformat() + "Z",
            "agent_id": agent_id,
            "event_type": "span",
            "level": "INFO",
            "schema_version": "1.0",
            "attributes": child_data["attributes"]
        }
        
        # Process the child span event
        child_result = simple_processor.process_event(child_event)
        assert child_result["success"] is True
        
        # Verify database state
        db_state = verify_database_state(db_session, {
            "events": 2,
            "spans": 2
        })
        assert all(db_state.values())
        
        # Verify parent-child relationship
        child_span = db_session.query(Span).filter(Span.parent_id == root_span_id).first()
        assert child_span is not None
        assert child_span.name == "child_span"
        assert child_span.parent_id == root_span_id
    
    def test_tool_with_llm_relationship(self, simple_processor, db_session):
        """Test processing of a tool event related to an LLM interaction."""
        # Create base event data
        agent_id = f"test-agent-{uuid.uuid4()}"
        timestamp = datetime.datetime.utcnow()
        
        # Create an LLM event
        llm_event = {
            "name": "llm.call.start",
            "timestamp": timestamp.isoformat() + "Z",
            "agent_id": agent_id,
            "event_type": "llm",
            "level": "INFO",
            "schema_version": "1.0",
            "attributes": generate_llm_interaction_data("start")["attributes"]
        }
        
        # Process the LLM event
        llm_result = simple_processor.process_event(llm_event)
        assert llm_result["success"] is True
        
        # Get the LLM interaction from the database
        llm_interaction = db_session.query(LLMInteraction).first()
        assert llm_interaction is not None
        
        # Create a tool event that references the LLM interaction
        tool_data = generate_tool_interaction_data("start")
        tool_data["attributes"]["tool.parent_llm_interaction_id"] = llm_interaction.id
        
        tool_event = {
            "name": "tool.execution.start",
            "timestamp": (timestamp + datetime.timedelta(seconds=1)).isoformat() + "Z",
            "agent_id": agent_id,
            "event_type": "tool",
            "level": "INFO",
            "schema_version": "1.0",
            "attributes": tool_data["attributes"]
        }
        
        # Process the tool event
        tool_result = simple_processor.process_event(tool_event)
        assert tool_result["success"] is True
        
        # Verify database state
        db_state = verify_database_state(db_session, {
            "events": 2,
            "llm_interactions": 1,
            "tool_interactions": 1
        })
        assert all(db_state.values())
        
        # Verify relationship between tool and LLM interaction if implemented
        tool_interaction = db_session.query(ToolInteraction).first()
        assert tool_interaction is not None
        
        # This assumes the relationship is implemented in the model
        if hasattr(tool_interaction, 'parent_llm_interaction_id'):
            assert tool_interaction.parent_llm_interaction_id == llm_interaction.id


class TestBatchProcessing:
    """Test batch processing of multiple events."""
    
    def test_process_multiple_events(self, simple_processor, db_session):
        """Test processing a batch of different events."""
        # Create base event data
        agent_id = f"test-agent-{uuid.uuid4()}"
        timestamp = datetime.datetime.utcnow()
        
        # Create a batch of different events
        events = [
            # LLM start event
            {
                "name": "llm.call.start",
                "timestamp": timestamp.isoformat() + "Z",
                "agent_id": agent_id,
                "event_type": "llm",
                "level": "INFO",
                "schema_version": "1.0",
                "attributes": generate_llm_interaction_data("start")["attributes"]
            },
            # Security alert event
            {
                "name": "security.alert.detected",
                "timestamp": (timestamp + datetime.timedelta(seconds=1)).isoformat() + "Z",
                "agent_id": agent_id,
                "event_type": "security",
                "level": "WARN",
                "schema_version": "1.0",
                "attributes": generate_security_alert_data()["attributes"]
            },
            # Framework event
            {
                "name": "framework.component.start",
                "timestamp": (timestamp + datetime.timedelta(seconds=2)).isoformat() + "Z",
                "agent_id": agent_id,
                "event_type": "framework",
                "level": "INFO",
                "schema_version": "1.0",
                "attributes": generate_framework_event_data()["attributes"]
            }
        ]
        
        # Process the batch
        result = simple_processor.process_batch(events)
        
        # Verify batch processing result
        assert result["total"] == 3
        assert result["successful"] == 3
        assert result["failed"] == 0
        
        # Verify database state
        db_state = verify_database_state(db_session, {
            "events": 3,
            "llm_interactions": 1,
            "security_alerts": 1,
            "framework_events": 1
        })
        assert all(db_state.values())
    
    def test_partial_batch_failure(self, simple_processor, db_session):
        """Test batch processing with some events failing."""
        # Create base event data
        agent_id = f"test-agent-{uuid.uuid4()}"
        timestamp = datetime.datetime.utcnow()
        
        # Create a batch with some invalid events
        events = [
            # Valid LLM event
            {
                "name": "llm.call.start",
                "timestamp": timestamp.isoformat() + "Z",
                "agent_id": agent_id,
                "event_type": "llm",
                "level": "INFO",
                "schema_version": "1.0",
                "attributes": generate_llm_interaction_data("start")["attributes"]
            },
            # Invalid event (missing required fields)
            {
                "name": "invalid.event",
                "timestamp": (timestamp + datetime.timedelta(seconds=1)).isoformat() + "Z",
                # Missing agent_id and other required fields
            },
            # Valid security event
            {
                "name": "security.alert.detected",
                "timestamp": (timestamp + datetime.timedelta(seconds=2)).isoformat() + "Z",
                "agent_id": agent_id,
                "event_type": "security",
                "level": "WARN",
                "schema_version": "1.0",
                "attributes": generate_security_alert_data()["attributes"]
            }
        ]
        
        # Process the batch
        result = simple_processor.process_batch(events)
        
        # Verify batch processing result
        assert result["total"] == 3
        assert result["successful"] == 2
        assert result["failed"] == 1
        
        # Verify database state
        db_state = verify_database_state(db_session, {
            "events": 2,
            "llm_interactions": 1,
            "security_alerts": 1
        })
        assert all(db_state.values()) 