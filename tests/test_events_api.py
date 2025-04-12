import json
import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.models.event import Event
from src.models.agent import Agent
from src.models.trace import Trace
from src.models.span import Span
from src.models.session import Session as SessionModel
from src.api import create_api_app

app = create_api_app()
client = TestClient(app)

def create_test_event(db, **kwargs):
    """Create a test event with given overrides"""
    # Default values
    defaults = {
        "name": "test.event",
        "timestamp": datetime.utcnow(),
        "level": "INFO",
        "agent_id": "test-agent",
        "trace_id": "test-trace",
        "span_id": "test-span",
        "parent_span_id": None,
        "session_id": "test-session",
        "schema_version": "1.0",
        "event_type": "generic",
        "raw_data": {"attributes": {"test": "value"}}
    }
    
    # Override defaults with kwargs
    event_data = {**defaults, **kwargs}
    
    # Create the event
    event = Event(**event_data)
    db.add(event)
    db.commit()
    db.refresh(event)
    
    return event

def setup_test_data(db):
    """Create test data for events API tests"""
    # Create test agent
    agent = Agent(agent_id="test-agent", name="Test Agent")
    db.add(agent)
    
    # Create test trace
    trace = Trace(trace_id="test-trace", agent_id="test-agent")
    db.add(trace)
    
    # Create test span
    span = Span(span_id="test-span", trace_id="test-trace", name="test span")
    db.add(span)
    
    # Create test session
    session = SessionModel(session_id="test-session", agent_id="test-agent")
    db.add(session)
    
    # Create various test events
    event_types = ["llm", "tool", "security", "framework", "generic"]
    levels = ["INFO", "WARNING", "ERROR"]
    
    # Create events with different timestamps, types, and levels
    now = datetime.utcnow()
    for i in range(50):
        create_test_event(
            db,
            name=f"test.event.{i}",
            timestamp=now - timedelta(minutes=i*10),
            level=levels[i % len(levels)],
            event_type=event_types[i % len(event_types)]
        )
    
    db.commit()

@pytest.fixture
def setup_db(temp_db):
    """Set up database with test data"""
    setup_test_data(temp_db)
    return temp_db

def test_list_events(setup_db):
    """Test listing events with various filters"""
    # Test default pagination
    response = client.get("/v1/telemetry/events")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) <= 100  # Default limit is 100
    
    # Test filtering by event type
    response = client.get("/v1/telemetry/events?event_type=llm")
    assert response.status_code == 200
    data = response.json()
    assert all(item["name"].startswith("test.event") for item in data)
    
    # Test time range filter
    now = datetime.utcnow()
    from_time = (now - timedelta(hours=1)).isoformat()
    to_time = now.isoformat()
    response = client.get(f"/v1/telemetry/events?from_time={from_time}&to_time={to_time}")
    assert response.status_code == 200
    
    # Test pagination
    response = client.get("/v1/telemetry/events?offset=10&limit=10")
    assert response.status_code == 200
    data = response.json()
    assert len(data) <= 10

def test_get_event_details(setup_db):
    """Test getting event details"""
    # Create a test event
    event = create_test_event(
        setup_db,
        name="test.detail.event",
        event_type="llm"
    )
    
    # Get event details
    response = client.get(f"/v1/telemetry/events/{event.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(event.id)
    assert data["name"] == "test.detail.event"
    
    # Test getting non-existent event
    response = client.get("/v1/telemetry/events/9999999")
    assert response.status_code == 404

def test_event_timeline(setup_db):
    """Test event timeline distribution"""
    # Test with different intervals
    for interval in ["1m", "5m", "1h", "1d"]:
        response = client.get(f"/v1/telemetry/events/timeline?interval={interval}")
        assert response.status_code == 200
        data = response.json()
        assert "intervals" in data
        assert data["meta"]["interval"] == interval
    
    # Test with event type filter
    response = client.get("/v1/telemetry/events/timeline?event_type=llm")
    assert response.status_code == 200
    
    # Test with invalid interval
    response = client.get("/v1/telemetry/events/timeline?interval=invalid")
    assert response.status_code == 400 

def test_session_events(setup_db):
    """Test getting events by session ID"""
    # Create events for a specific session
    session_id = "test-session-events"
    for i in range(5):
        create_test_event(
            setup_db,
            name=f"test.session.event.{i}",
            session_id=session_id
        )
    
    # Get events for the session
    response = client.get(f"/v1/telemetry/sessions/{session_id}/events")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 5
    assert all(item["name"].startswith("test.session.event") for item in data) 