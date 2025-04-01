"""
Integration tests for the SimpleProcessor with database.

This module contains integration tests that ensure the SimpleProcessor correctly
processes events and stores them in the database.
"""
import os
import json
import pytest
from sqlalchemy.orm import Session

from src.models.base import Base, init_db, get_db, create_all
from src.models.event import Event
from src.models.agent import Agent
from src.models.trace import Trace
from src.models.span import Span
from src.models.llm_interaction import LLMInteraction
from src.models.security_alert import SecurityAlert
from src.models.framework_event import FrameworkEvent

from src.processing import SimpleProcessor


@pytest.fixture(scope="function")
def db_path(tmp_path, request):
    """
    Create a temporary database file for testing.
    Each test gets its own unique database file.
    """
    # Use the test name to create a unique database file for each test
    db_file = tmp_path / f"{request.node.name}.db"
    db_url = f"sqlite:///{db_file}"
    
    # Initialize the database
    engine = init_db(db_url, echo=False)
    create_all()
    
    yield db_url
    
    # Clean up
    if os.path.exists(db_file):
        os.remove(db_file)


@pytest.fixture(scope="function")
def db_session(db_path):
    """
    Get a database session for testing.
    Each test gets its own isolated database session.
    """
    # Create a session that will be closed and cleaned up after the test
    session = None
    for session in get_db():
        break
    
    # Ensure we have a session
    assert session is not None
    
    yield session
    
    # Explicitly close the session to ensure cleanup
    session.close()


@pytest.fixture(scope="function")
def processor(db_path):
    """
    Create a SimpleProcessor instance with a database session factory.
    Each test gets its own processor with its own database.
    """
    return SimpleProcessor(get_db)


@pytest.fixture(scope="function")
def example_records():
    """
    Load example records from example_records.json.
    Use a fresh copy for each test to prevent modifications affecting other tests.
    """
    file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "example_records.json")

    records = []
    try:
        with open(file_path, 'r') as f:
            for line in f:
                records.append(json.loads(line))
    except FileNotFoundError:
        # Return empty records if file not found
        print(f"Warning: example_records.json not found at {file_path}")
        return []
    
    # Return a copy to ensure test isolation
    import copy
    return copy.deepcopy(records)


def test_process_event(processor, example_records, db_session):
    """Test processing a single event from example_records.json."""
    # Skip if no records available
    if not example_records:
        pytest.skip("No example records available")
    
    # Process the first event
    result = processor.process_event(example_records[0])
    
    # Check the result
    assert result["success"] is True
    assert "event_id" in result
    assert result["event_name"] == example_records[0]["name"]
    
    # Check that the event was stored in the database
    event = db_session.query(Event).filter_by(id=result["event_id"]).first()
    assert event is not None
    assert event.name == example_records[0]["name"]
    assert event.agent_id == example_records[0]["agent_id"]
    
    # Check that the agent was created
    agent = db_session.query(Agent).filter_by(agent_id=example_records[0]["agent_id"]).first()
    assert agent is not None


def test_process_batch(processor, example_records, db_session):
    """Test processing a batch of events from example_records.json."""
    # Skip if not enough records available
    if len(example_records) < 5:
        pytest.skip("Not enough example records available")
    
    # Take the first 5 records for batch processing
    batch_records = example_records[:5]
    
    # Process the batch
    result = processor.process_batch(batch_records)
    
    # Check the result
    assert result["total"] == 5
    assert result["successful"] == 5
    assert result["failed"] == 0
    
    # Check that all events were stored in the database
    for i, record in enumerate(batch_records):
        event = db_session.query(Event).filter_by(name=record["name"], agent_id=record["agent_id"]).first()
        assert event is not None, f"Event {i} was not stored in the database"


def test_process_llm_events(processor, example_records, db_session):
    """Test processing LLM events from example_records.json."""
    # Find LLM events
    llm_events = [record for record in example_records if record["name"].startswith("llm.")]
    
    if not llm_events:
        pytest.skip("No LLM events in example_records.json")
    
    # Process the first LLM event
    result = processor.process_event(llm_events[0])
    
    # Check the result
    assert result["success"] is True
    
    # Check that the event was stored in the database
    event = db_session.query(Event).filter_by(id=result["event_id"]).first()
    assert event is not None
    assert event.event_type == "llm"
    
    # Check that the LLM interaction was created
    assert event.llm_interaction is not None
    assert event.llm_interaction.event_id == event.id


def test_process_security_alerts(processor, example_records, db_session):
    """Test processing security alert events from example_records.json."""
    # Find security alert events
    security_events = [record for record in example_records if record["name"].startswith("security.")]
    
    if not security_events:
        pytest.skip("No security alert events in example_records.json")
    
    # Process the first security event
    result = processor.process_event(security_events[0])
    
    # Check the result
    assert result["success"] is True
    
    # Check that the event was stored in the database
    event = db_session.query(Event).filter_by(id=result["event_id"]).first()
    assert event is not None
    assert event.event_type == "security"
    
    # Check that the security alert was created
    assert event.security_alert is not None
    assert event.security_alert.event_id == event.id


def test_process_framework_events(processor, example_records, db_session):
    """Test processing framework events from example_records.json."""
    # Find framework events
    framework_events = [record for record in example_records if record["name"].startswith("framework.")]
    
    if not framework_events:
        pytest.skip("No framework events in example_records.json")
    
    # Process the first framework event
    result = processor.process_event(framework_events[0])
    
    # Check the result
    assert result["success"] is True
    
    # Check that the event was stored in the database
    event = db_session.query(Event).filter_by(id=result["event_id"]).first()
    assert event is not None
    assert event.event_type == "framework"
    
    # Check that the framework event was created
    assert event.framework_event is not None
    assert event.framework_event.event_id == event.id


def test_process_traces_and_spans(processor, example_records, db_session):
    """Test processing events with traces and spans from example_records.json."""
    # Find events with traces and spans
    trace_events = [record for record in example_records 
                   if "trace_id" in record and record["trace_id"] and 
                      "span_id" in record and record["span_id"]]
    
    if not trace_events:
        pytest.skip("No events with traces and spans in example_records.json")
    
    # Process the first trace event
    result = processor.process_event(trace_events[0])
    
    # Check the result
    assert result["success"] is True
    
    # Check that the event was stored in the database
    event = db_session.query(Event).filter_by(id=result["event_id"]).first()
    assert event is not None
    assert event.trace_id == trace_events[0]["trace_id"]
    assert event.span_id == trace_events[0]["span_id"]
    
    # Check that the trace was created
    trace = db_session.query(Trace).filter_by(trace_id=trace_events[0]["trace_id"]).first()
    assert trace is not None
    
    # Check that the span was created
    span = db_session.query(Span).filter_by(span_id=trace_events[0]["span_id"]).first()
    assert span is not None
    assert span.trace_id == trace_events[0]["trace_id"] 