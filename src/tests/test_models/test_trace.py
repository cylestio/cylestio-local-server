"""
Tests for the Trace model.
"""
import datetime
import pytest

from models.agent import Agent
from models.trace import Trace


@pytest.fixture
def test_agent(db_session):
    """Create a test agent for use in trace tests."""
    agent = Agent(
        agent_id="test-trace-agent",
        name="Test Trace Agent",
        first_seen=datetime.datetime.utcnow(),
        last_seen=datetime.datetime.utcnow()
    )
    db_session.add(agent)
    db_session.commit()
    return agent


def test_trace_creation(db_session, test_agent):
    """Test creating a new trace."""
    # Create a new trace
    trace = Trace(
        trace_id="test-trace-id",
        agent_id=test_agent.agent_id,
        start_timestamp=datetime.datetime.utcnow()
    )
    
    db_session.add(trace)
    db_session.commit()
    
    # Query the trace
    saved_trace = db_session.query(Trace).filter(Trace.trace_id == "test-trace-id").first()
    
    # Verify
    assert saved_trace is not None
    assert saved_trace.trace_id == "test-trace-id"
    assert saved_trace.agent_id == test_agent.agent_id
    assert saved_trace.start_timestamp is not None
    assert saved_trace.end_timestamp is None


def test_trace_get_or_create_new(db_session, test_agent):
    """Test get_or_create method when creating a new trace."""
    # Use get_or_create to create a new trace
    trace = Trace.get_or_create(
        db_session,
        trace_id="new-trace-id",
        agent_id=test_agent.agent_id
    )
    
    db_session.commit()
    
    # Verify
    assert trace is not None
    assert trace.trace_id == "new-trace-id"
    assert trace.agent_id == test_agent.agent_id
    assert trace.start_timestamp is not None
    assert trace.end_timestamp is None


def test_trace_get_or_create_existing(db_session, test_agent):
    """Test get_or_create method with an existing trace."""
    # Create a trace
    start_time = datetime.datetime.utcnow()
    trace1 = Trace(
        trace_id="existing-trace-id",
        agent_id=test_agent.agent_id,
        start_timestamp=start_time
    )
    db_session.add(trace1)
    db_session.commit()
    
    # Use get_or_create to get the existing trace
    trace2 = Trace.get_or_create(
        db_session,
        trace_id="existing-trace-id",
        agent_id=test_agent.agent_id
    )
    
    db_session.commit()
    
    # Verify that we got the existing trace
    assert trace2.id == trace1.id
    assert trace2.trace_id == "existing-trace-id"
    assert trace2.start_timestamp == start_time


def test_trace_update_timestamps(db_session, test_agent):
    """Test updating trace timestamps."""
    # Create a trace with no timestamps
    trace = Trace(
        trace_id="update-trace-id",
        agent_id=test_agent.agent_id
    )
    db_session.add(trace)
    db_session.commit()
    
    # Set start and end timestamps
    start_time = datetime.datetime(2020, 1, 1, 12, 0, 0)
    end_time = datetime.datetime(2020, 1, 1, 13, 0, 0)
    
    trace.update_timestamps(db_session, start_time, end_time)
    db_session.commit()
    
    # Refresh from database
    db_session.refresh(trace)
    
    # Verify
    assert trace.start_timestamp == start_time
    assert trace.end_timestamp == end_time


def test_trace_update_timestamps_only_start(db_session, test_agent):
    """Test updating only the start timestamp."""
    # Create a trace with no timestamps
    trace = Trace(
        trace_id="start-only-trace-id",
        agent_id=test_agent.agent_id
    )
    db_session.add(trace)
    db_session.commit()
    
    # Set only start timestamp
    start_time = datetime.datetime(2020, 1, 1, 12, 0, 0)
    
    trace.update_timestamps(db_session, start_time)
    db_session.commit()
    
    # Refresh from database
    db_session.refresh(trace)
    
    # Verify
    assert trace.start_timestamp == start_time
    assert trace.end_timestamp is None


def test_trace_update_timestamps_only_end(db_session, test_agent):
    """Test updating only the end timestamp."""
    # Create a trace with no timestamps
    trace = Trace(
        trace_id="end-only-trace-id",
        agent_id=test_agent.agent_id
    )
    db_session.add(trace)
    db_session.commit()
    
    # Set only end timestamp
    end_time = datetime.datetime(2020, 1, 1, 13, 0, 0)
    
    trace.update_timestamps(db_session, None, end_time)
    db_session.commit()
    
    # Refresh from database
    db_session.refresh(trace)
    
    # Verify
    assert trace.start_timestamp is None
    assert trace.end_timestamp == end_time


def test_trace_duration_with_timestamps(db_session, test_agent):
    """Test trace duration calculation with timestamps."""
    # Create a trace with start and end times
    start_time = datetime.datetime(2020, 1, 1, 12, 0, 0)
    end_time = datetime.datetime(2020, 1, 1, 13, 0, 0)
    
    trace = Trace(
        trace_id="duration-trace-id",
        agent_id=test_agent.agent_id,
        start_timestamp=start_time,
        end_timestamp=end_time
    )
    db_session.add(trace)
    db_session.commit()
    
    # Get duration
    duration = trace.get_duration_seconds()
    
    # Verify (should be 3600 seconds = 1 hour)
    assert duration == 3600.0


def test_trace_duration_without_timestamps(db_session, test_agent):
    """Test trace duration calculation without timestamps."""
    # Create a trace with no timestamps
    trace = Trace(
        trace_id="no-duration-trace-id",
        agent_id=test_agent.agent_id
    )
    db_session.add(trace)
    db_session.commit()
    
    # Get duration
    duration = trace.get_duration_seconds()
    
    # Verify
    assert duration is None


def test_trace_duration_with_only_start(db_session, test_agent):
    """Test trace duration calculation with only start timestamp."""
    # Create a trace with only start time
    trace = Trace(
        trace_id="start-only-duration-trace-id",
        agent_id=test_agent.agent_id,
        start_timestamp=datetime.datetime.utcnow()
    )
    db_session.add(trace)
    db_session.commit()
    
    # Get duration
    duration = trace.get_duration_seconds()
    
    # Verify
    assert duration is None 