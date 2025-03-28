"""
Tests for the Session model.
"""
import datetime
import pytest
from sqlalchemy.exc import IntegrityError

from src.models.agent import Agent
from src.models.session import Session


@pytest.fixture
def test_agent(db_session):
    """Create a test agent for use in session tests."""
    agent = Agent(
        agent_id="test-session-agent",
        name="Test Session Agent",
        first_seen=datetime.datetime.utcnow(),
        last_seen=datetime.datetime.utcnow()
    )
    db_session.add(agent)
    db_session.commit()
    return agent


def test_session_creation(db_session, test_agent):
    """Test creating a new session."""
    # Create a new session
    session = Session(
        agent_id=test_agent.id,
        session_id="test-session-id",
        start_timestamp=datetime.datetime.utcnow()
    )
    
    db_session.add(session)
    db_session.commit()
    
    # Query the session
    saved_session = db_session.query(Session).filter(Session.session_id == "test-session-id").first()
    
    # Verify
    assert saved_session is not None
    assert saved_session.session_id == "test-session-id"
    assert saved_session.agent_id == test_agent.id
    assert saved_session.start_timestamp is not None
    assert saved_session.end_timestamp is None


def test_session_uniqueness(db_session, test_agent):
    """Test that session_id must be unique."""
    # Create a new session
    session1 = Session(
        agent_id=test_agent.id,
        session_id="unique-session-id",
        start_timestamp=datetime.datetime.utcnow()
    )
    db_session.add(session1)
    db_session.commit()
    
    # Try to create another session with the same session_id
    session2 = Session(
        agent_id=test_agent.id,
        session_id="unique-session-id",
        start_timestamp=datetime.datetime.utcnow()
    )
    db_session.add(session2)
    
    # Verify that an IntegrityError is raised
    with pytest.raises(IntegrityError):
        db_session.commit()
    
    # Rollback for cleanup
    db_session.rollback()


def test_session_get_or_create_new(db_session, test_agent):
    """Test get_or_create method when creating a new session."""
    # Use get_or_create to create a new session
    session = Session.get_or_create(
        db_session,
        session_id="new-session-id",
        agent_id=test_agent.id
    )
    
    db_session.commit()
    
    # Verify
    assert session is not None
    assert session.session_id == "new-session-id"
    assert session.agent_id == test_agent.id
    assert session.start_timestamp is not None
    assert session.end_timestamp is None


def test_session_get_or_create_existing(db_session, test_agent):
    """Test get_or_create method with an existing session."""
    # Create a session
    start_time = datetime.datetime.utcnow()
    session1 = Session(
        agent_id=test_agent.id,
        session_id="existing-session-id",
        start_timestamp=start_time
    )
    db_session.add(session1)
    db_session.commit()
    
    # Use get_or_create to get the existing session
    session2 = Session.get_or_create(
        db_session,
        session_id="existing-session-id",
        agent_id=test_agent.id
    )
    
    db_session.commit()
    
    # Verify that we got the existing session
    assert session2.id == session1.id
    assert session2.session_id == "existing-session-id"
    assert session2.start_timestamp == start_time


def test_session_end(db_session, test_agent):
    """Test ending a session."""
    # Create a session
    session = Session(
        agent_id=test_agent.id,
        session_id="end-session-id",
        start_timestamp=datetime.datetime.utcnow()
    )
    db_session.add(session)
    db_session.commit()
    
    # End the session
    session.end_session(db_session)
    db_session.commit()
    
    # Query the session
    saved_session = db_session.query(Session).filter(Session.session_id == "end-session-id").first()
    
    # Verify
    assert saved_session.end_timestamp is not None
    assert saved_session.start_timestamp < saved_session.end_timestamp


def test_session_end_with_timestamp(db_session, test_agent):
    """Test ending a session with a specific timestamp."""
    # Create a session
    start_time = datetime.datetime(2020, 1, 1, 12, 0, 0)
    end_time = datetime.datetime(2020, 1, 1, 13, 0, 0)
    
    session = Session(
        agent_id=test_agent.id,
        session_id="end-time-session-id",
        start_timestamp=start_time
    )
    db_session.add(session)
    db_session.commit()
    
    # End the session with a specific timestamp
    session.end_session(db_session, end_timestamp=end_time)
    db_session.commit()
    
    # Query the session
    saved_session = db_session.query(Session).filter(Session.session_id == "end-time-session-id").first()
    
    # Verify
    assert saved_session.end_timestamp == end_time


def test_session_duration(db_session, test_agent):
    """Test getting the duration of a session."""
    # Create a session with start and end times
    start_time = datetime.datetime(2020, 1, 1, 12, 0, 0)
    end_time = datetime.datetime(2020, 1, 1, 13, 0, 0)
    
    session = Session(
        agent_id=test_agent.id,
        session_id="duration-session-id",
        start_timestamp=start_time,
        end_timestamp=end_time
    )
    db_session.add(session)
    db_session.commit()
    
    # Get the duration
    duration = session.get_duration_seconds()
    
    # Verify (should be 3600 seconds = 1 hour)
    assert duration == 3600.0


def test_session_no_duration_if_not_ended(db_session, test_agent):
    """Test that duration is None if session hasn't ended."""
    # Create a session with no end time
    session = Session(
        agent_id=test_agent.id,
        session_id="no-duration-session-id",
        start_timestamp=datetime.datetime.utcnow()
    )
    db_session.add(session)
    db_session.commit()
    
    # Get the duration
    duration = session.get_duration_seconds()
    
    # Verify
    assert duration is None


def test_session_generate_id():
    """Test generating a session ID."""
    session_id1 = Session.generate_session_id()
    session_id2 = Session.generate_session_id()
    
    # Verify that IDs are strings and unique
    assert isinstance(session_id1, str)
    assert isinstance(session_id2, str)
    assert session_id1 != session_id2


def test_session_statistics(db_session, test_agent):
    """Test getting statistics for a session."""
    # Create a session
    session = Session(
        agent_id=test_agent.id,
        session_id="stats-session-id",
        start_timestamp=datetime.datetime.utcnow()
    )
    db_session.add(session)
    db_session.commit()
    
    # Get statistics
    stats = session.get_statistics(db_session)
    
    # Verify
    assert isinstance(stats, dict)
    assert "event_count" in stats
    assert "event_types" in stats
    assert "trace_count" in stats
    assert "start_timestamp" in stats
    assert "end_timestamp" in stats
    assert "duration_seconds" in stats 