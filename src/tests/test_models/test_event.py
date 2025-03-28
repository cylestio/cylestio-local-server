"""
Tests for the Event model.
"""
import json
import datetime
import pytest

from src.models.agent import Agent
from src.models.session import Session
from src.models.trace import Trace
from src.models.span import Span
from src.models.event import Event


@pytest.fixture
def test_agent(db_session):
    """Create a test agent for use in event tests."""
    agent = Agent(
        agent_id="test-event-agent",
        name="Test Event Agent",
        first_seen=datetime.datetime.utcnow(),
        last_seen=datetime.datetime.utcnow()
    )
    db_session.add(agent)
    db_session.commit()
    return agent


@pytest.fixture
def test_session(db_session, test_agent):
    """Create a test session for use in event tests."""
    session = Session(
        session_id="test-event-session",
        agent_id=test_agent.agent_id,
        start_timestamp=datetime.datetime.utcnow()
    )
    db_session.add(session)
    db_session.commit()
    return session


@pytest.fixture
def test_trace(db_session, test_agent):
    """Create a test trace for use in event tests."""
    trace = Trace(
        trace_id="test-event-trace",
        agent_id=test_agent.agent_id,
        start_timestamp=datetime.datetime.utcnow()
    )
    db_session.add(trace)
    db_session.commit()
    return trace


@pytest.fixture
def test_span(db_session, test_trace):
    """Create a test span for use in event tests."""
    span = Span(
        span_id="test-event-span",
        trace_id=test_trace.trace_id,
        name="Test Span",
        start_timestamp=datetime.datetime.utcnow()
    )
    db_session.add(span)
    db_session.commit()
    return span


def test_event_creation(db_session, test_agent, test_session, test_trace, test_span):
    """Test creating a new event."""
    # Create a new event
    event = Event(
        agent_id=test_agent.agent_id,
        session_id=test_session.session_id,
        trace_id=test_trace.trace_id,
        span_id=test_span.span_id,
        timestamp=datetime.datetime.utcnow(),
        schema_version="1.0",
        name="test.event",
        level="INFO",
        event_type="test"
    )
    
    db_session.add(event)
    db_session.commit()
    
    # Query the event
    saved_event = db_session.query(Event).filter(Event.id == event.id).first()
    
    # Verify
    assert saved_event is not None
    assert saved_event.agent_id == test_agent.agent_id
    assert saved_event.session_id == test_session.session_id
    assert saved_event.trace_id == test_trace.trace_id
    assert saved_event.span_id == test_span.span_id
    assert saved_event.schema_version == "1.0"
    assert saved_event.name == "test.event"
    assert saved_event.level == "INFO"
    assert saved_event.event_type == "test"


def test_event_required_fields(db_session, test_agent):
    """Test that required fields must be provided."""
    # Try to create an event with missing required fields
    event = Event(
        agent_id=test_agent.agent_id,
        # Missing: timestamp, schema_version, name, level, event_type
    )
    
    db_session.add(event)
    
    # Should raise an IntegrityError when committing
    with pytest.raises(Exception):
        db_session.commit()
    
    # Rollback for cleanup
    db_session.rollback()


def test_event_relationships(db_session, test_agent, test_session, test_trace, test_span):
    """Test event relationships to other entities."""
    # Create a new event
    event = Event(
        agent_id=test_agent.agent_id,
        session_id=test_session.session_id,
        trace_id=test_trace.trace_id,
        span_id=test_span.span_id,
        timestamp=datetime.datetime.utcnow(),
        schema_version="1.0",
        name="test.event.relationships",
        level="INFO",
        event_type="test"
    )
    
    db_session.add(event)
    db_session.commit()
    
    # Query the event
    saved_event = db_session.query(Event).filter(Event.id == event.id).first()
    
    # Verify relationships
    assert saved_event.agent.agent_id == test_agent.agent_id
    assert saved_event.session.session_id == test_session.session_id
    assert saved_event.trace.trace_id == test_trace.trace_id
    assert saved_event.span.span_id == test_span.span_id


def test_event_without_optional_relationships(db_session, test_agent):
    """Test creating an event without optional relationships."""
    # Create a new event without session, trace, or span
    event = Event(
        agent_id=test_agent.agent_id,
        timestamp=datetime.datetime.utcnow(),
        schema_version="1.0",
        name="test.event.no.relationships",
        level="INFO",
        event_type="test"
    )
    
    db_session.add(event)
    db_session.commit()
    
    # Query the event
    saved_event = db_session.query(Event).filter(Event.id == event.id).first()
    
    # Verify
    assert saved_event is not None
    assert saved_event.session_id is None
    assert saved_event.trace_id is None
    assert saved_event.span_id is None
    assert saved_event.session is None
    assert saved_event.trace is None
    assert saved_event.span is None


def test_determine_event_type():
    """Test the _determine_event_type static method."""
    # Test different event name prefixes
    assert Event._determine_event_type("llm.call.start") == "llm"
    assert Event._determine_event_type("tool.execution") == "tool"
    assert Event._determine_event_type("security.alert") == "security"
    assert Event._determine_event_type("framework.startup") == "framework"
    assert Event._determine_event_type("framework_patch") == "framework"
    assert Event._determine_event_type("monitoring.start") == "monitoring"
    assert Event._determine_event_type("unknown.event") == "other"


def test_from_telemetry_basic(db_session):
    """Test creating an event from basic telemetry data."""
    # Create a simple telemetry record
    telemetry_data = {
        "agent_id": "telemetry-agent-id",
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "schema_version": "1.0",
        "name": "test.event",
        "level": "INFO",
        "attributes": {}
    }
    
    # Create an event from the telemetry data
    event = Event.from_telemetry(db_session, telemetry_data)
    
    # Verify
    assert event is not None
    assert event.agent_id == "telemetry-agent-id"
    assert event.schema_version == "1.0"
    assert event.name == "test.event"
    assert event.level == "INFO"
    assert event.event_type == "other"  # Should default to "other"


def test_get_specialized_event(db_session, test_agent):
    """Test the get_specialized_event property."""
    # Create an event
    event = Event(
        agent_id=test_agent.agent_id,
        timestamp=datetime.datetime.utcnow(),
        schema_version="1.0",
        name="test.event",
        level="INFO",
        event_type="other"
    )
    
    db_session.add(event)
    db_session.commit()
    
    # The event doesn't have a specialized event yet
    assert event.get_specialized_event is None
    
    # We would need to create specialized events to fully test this,
    # but that's better done in the tests for the specialized event models 