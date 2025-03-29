"""
Tests for the Agent model.
"""
import datetime
import pytest
from sqlalchemy.exc import IntegrityError

from models.agent import Agent


def test_agent_creation(db_session):
    """Test creating a new agent."""
    # Create a new agent
    agent = Agent(
        agent_id="test-agent-id",
        name="Test Agent",
        system_info="Test System",
        version="1.0.0",
        first_seen=datetime.datetime.utcnow(),
        last_seen=datetime.datetime.utcnow(),
        is_active=True
    )
    
    db_session.add(agent)
    db_session.commit()
    
    # Query the agent
    saved_agent = db_session.query(Agent).filter(Agent.agent_id == "test-agent-id").first()
    
    # Verify
    assert saved_agent is not None
    assert saved_agent.agent_id == "test-agent-id"
    assert saved_agent.name == "Test Agent"
    assert saved_agent.system_info == "Test System"
    assert saved_agent.version == "1.0.0"
    assert saved_agent.is_active is True


def test_agent_uniqueness(db_session):
    """Test that agent_id must be unique."""
    # Create a new agent
    agent1 = Agent(
        agent_id="unique-agent-id",
        name="Test Agent 1",
        first_seen=datetime.datetime.utcnow(),
        last_seen=datetime.datetime.utcnow()
    )
    db_session.add(agent1)
    db_session.commit()
    
    # Try to create another agent with the same agent_id
    agent2 = Agent(
        agent_id="unique-agent-id",
        name="Test Agent 2",
        first_seen=datetime.datetime.utcnow(),
        last_seen=datetime.datetime.utcnow()
    )
    db_session.add(agent2)
    
    # Verify that an IntegrityError is raised
    with pytest.raises(IntegrityError):
        db_session.commit()
    
    # Rollback for cleanup
    db_session.rollback()


def test_agent_get_or_create_new(db_session):
    """Test get_or_create method when creating a new agent."""
    # Use get_or_create to create a new agent
    agent = Agent.get_or_create(
        db_session,
        agent_id="new-agent-id",
        name="New Agent",
        system_info="New System",
        version="2.0.0"
    )
    
    db_session.commit()
    
    # Verify
    assert agent is not None
    assert agent.agent_id == "new-agent-id"
    assert agent.name == "New Agent"
    assert agent.system_info == "New System"
    assert agent.version == "2.0.0"
    assert agent.is_active is True
    
    # Verify first_seen and last_seen
    assert agent.first_seen is not None
    assert agent.last_seen is not None


def test_agent_get_or_create_existing(db_session):
    """Test get_or_create method with an existing agent."""
    # Create an agent
    agent1 = Agent(
        agent_id="existing-agent-id",
        name="Existing Agent",
        system_info="Existing System",
        version="3.0.0",
        first_seen=datetime.datetime.utcnow(),
        last_seen=datetime.datetime.utcnow(),
        is_active=True
    )
    db_session.add(agent1)
    db_session.commit()
    
    # Use get_or_create to get the existing agent
    agent2 = Agent.get_or_create(
        db_session,
        agent_id="existing-agent-id",
        name="Updated Agent",
        system_info="Updated System",
        version="3.1.0"
    )
    
    db_session.commit()
    
    # Verify that we got the existing agent
    assert agent2.id == agent1.id
    assert agent2.agent_id == "existing-agent-id"
    
    # Version should be updated, but name should not be changed if already set
    assert agent2.version == "3.1.0"
    assert agent2.name == "Existing Agent"  # name should not change
    assert agent2.system_info == "Existing System"  # system_info should not change


def test_agent_update_last_seen(db_session):
    """Test updating an agent's last_seen timestamp."""
    # Create an agent
    old_time = datetime.datetime(2020, 1, 1, 12, 0, 0)
    agent = Agent(
        agent_id="update-agent-id",
        name="Update Agent",
        first_seen=old_time,
        last_seen=old_time
    )
    db_session.add(agent)
    db_session.commit()
    
    # Update last_seen
    agent.update_last_seen(db_session)
    db_session.commit()
    
    # Refresh the agent from the database
    db_session.refresh(agent)
    
    # Verify
    assert agent.last_seen > old_time


def test_agent_deactivate_reactivate(db_session):
    """Test deactivating and reactivating an agent."""
    # Create an agent
    agent = Agent(
        agent_id="active-agent-id",
        name="Active Agent",
        first_seen=datetime.datetime.utcnow(),
        last_seen=datetime.datetime.utcnow(),
        is_active=True
    )
    db_session.add(agent)
    db_session.commit()
    
    # Deactivate
    agent.deactivate(db_session)
    db_session.commit()
    db_session.refresh(agent)
    
    # Verify
    assert agent.is_active is False
    
    # Reactivate
    old_last_seen = agent.last_seen
    agent.reactivate(db_session)
    db_session.commit()
    db_session.refresh(agent)
    
    # Verify
    assert agent.is_active is True
    assert agent.last_seen > old_last_seen


def test_agent_generate_id():
    """Test generating an agent ID."""
    agent_id1 = Agent.generate_agent_id()
    agent_id2 = Agent.generate_agent_id()
    
    # Verify that IDs are strings and unique
    assert isinstance(agent_id1, str)
    assert isinstance(agent_id2, str)
    assert agent_id1 != agent_id2


def test_agent_get_statistics(db_session):
    """Test getting statistics for an agent."""
    # This will require setting up related models like Event, Trace, Session
    # For now, just test that the method exists and returns a dictionary
    
    # Create an agent
    agent = Agent(
        agent_id="stats-agent-id",
        name="Stats Agent",
        first_seen=datetime.datetime.utcnow(),
        last_seen=datetime.datetime.utcnow()
    )
    db_session.add(agent)
    db_session.commit()
    
    # Get statistics
    stats = agent.get_statistics(db_session)
    
    # Verify
    assert isinstance(stats, dict)
    assert "event_count" in stats
    assert "trace_count" in stats
    assert "session_count" in stats
    assert "first_seen" in stats
    assert "last_seen" in stats
    assert "is_active" in stats 