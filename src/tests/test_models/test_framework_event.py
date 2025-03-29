"""
Tests for the FrameworkEvent model.
"""
import json
import datetime
import pytest

from models.agent import Agent
from models.event import Event
from models.framework_event import FrameworkEvent


@pytest.fixture
def test_agent(db_session):
    """Create a test agent for use in framework event tests."""
    agent = Agent(
        agent_id="test-framework-agent",
        name="Test Framework Agent",
        first_seen=datetime.datetime.utcnow(),
        last_seen=datetime.datetime.utcnow()
    )
    db_session.add(agent)
    db_session.commit()
    return agent


@pytest.fixture
def test_event(db_session, test_agent):
    """Create a test event for use in framework event tests."""
    event = Event(
        agent_id=test_agent.id,
        timestamp=datetime.datetime.utcnow(),
        schema_version="1.0",
        name="framework.startup",
        level="INFO",
        event_type="framework"
    )
    db_session.add(event)
    db_session.commit()
    return event


def test_framework_event_creation(db_session, test_event):
    """Test creating a new framework event."""
    # Create a new framework event
    framework_event = FrameworkEvent(
        event_id=test_event.id,
        event_type="startup",
        framework_name="langchain",
        framework_version="0.0.310",
        details=json.dumps({
            "python_version": "3.10.12",
            "environment": "production",
            "modules": ["langchain.chains", "langchain.llms"]
        })
    )
    
    db_session.add(framework_event)
    db_session.commit()
    
    # Query the framework event
    saved_event = db_session.query(FrameworkEvent).filter(
        FrameworkEvent.event_id == test_event.id
    ).first()
    
    # Verify
    assert saved_event is not None
    assert saved_event.event_id == test_event.id
    assert saved_event.event_type == "startup"
    assert saved_event.framework_name == "langchain"
    assert saved_event.framework_version == "0.0.310"
    assert json.loads(saved_event.details) == {
        "python_version": "3.10.12",
        "environment": "production",
        "modules": ["langchain.chains", "langchain.llms"]
    }


def test_framework_event_relationships(db_session, test_event):
    """Test framework event relationships."""
    # Create a new framework event
    framework_event = FrameworkEvent(
        event_id=test_event.id,
        event_type="config_change",
        framework_name="langchain",
        framework_version="0.0.310"
    )
    
    db_session.add(framework_event)
    db_session.commit()
    
    # Verify the relationship with the event
    assert framework_event.event.id == test_event.id
    assert framework_event.event.name == "framework.startup"
    
    # Verify from the other direction (event to framework event)
    assert test_event.framework_event.id == framework_event.id
    assert test_event.framework_event.framework_name == "langchain"


def test_from_event_startup(db_session, test_event):
    """Test creating a framework event from a startup event."""
    # Create event data for framework startup
    event_data = {
        "name": "framework.startup",
        "payload": {
            "framework_name": "langchain",
            "framework_version": "0.0.310",
            "python_version": "3.10.12",
            "environment": "development",
            "debug_mode": True
        }
    }
    
    # Update the test event with this data
    test_event.data = json.dumps(event_data)
    db_session.commit()
    
    # Create framework event from event
    framework_event = FrameworkEvent.from_event(db_session, test_event)
    
    # Verify
    assert framework_event is not None
    assert framework_event.event_id == test_event.id
    assert framework_event.event_type == "startup"
    assert framework_event.framework_name == "langchain"
    assert framework_event.framework_version == "0.0.310"
    assert framework_event.details is not None
    
    details_dict = json.loads(framework_event.details)
    assert details_dict["python_version"] == "3.10.12"
    assert details_dict["environment"] == "development"
    assert details_dict["debug_mode"] is True


def test_from_event_shutdown(db_session, test_event):
    """Test creating a framework event from a shutdown event."""
    # Create event data for framework shutdown
    event_data = {
        "name": "framework.shutdown",
        "payload": {
            "framework_name": "langchain",
            "framework_version": "0.0.310",
            "uptime_seconds": 3600,
            "clean_exit": True
        }
    }
    
    # Update the test event with this data
    test_event.name = "framework.shutdown"  # Update event name
    test_event.data = json.dumps(event_data)
    db_session.commit()
    
    # Create framework event from event
    framework_event = FrameworkEvent.from_event(db_session, test_event)
    
    # Verify
    assert framework_event is not None
    assert framework_event.event_id == test_event.id
    assert framework_event.event_type == "shutdown"
    assert framework_event.framework_name == "langchain"
    assert framework_event.framework_version == "0.0.310"
    assert framework_event.details is not None
    
    details_dict = json.loads(framework_event.details)
    assert details_dict["uptime_seconds"] == 3600
    assert details_dict["clean_exit"] is True


def test_from_event_config_change(db_session, test_event):
    """Test creating a framework event from a config change event."""
    # Create event data for framework config change
    event_data = {
        "name": "framework.config_change",
        "payload": {
            "framework_name": "langchain",
            "framework_version": "0.0.310",
            "changes": {
                "llm_provider": {"old": "openai", "new": "anthropic"},
                "temperature": {"old": 0.7, "new": 0.5},
                "max_tokens": {"old": 1024, "new": 2048}
            },
            "change_source": "api_call"
        }
    }
    
    # Update the test event with this data
    test_event.name = "framework.config_change"  # Update event name
    test_event.data = json.dumps(event_data)
    db_session.commit()
    
    # Create framework event from event
    framework_event = FrameworkEvent.from_event(db_session, test_event)
    
    # Verify
    assert framework_event is not None
    assert framework_event.event_id == test_event.id
    assert framework_event.event_type == "config_change"
    assert framework_event.framework_name == "langchain"
    assert framework_event.framework_version == "0.0.310"
    assert framework_event.details is not None
    
    details_dict = json.loads(framework_event.details)
    assert "changes" in details_dict
    assert details_dict["changes"]["llm_provider"]["old"] == "openai"
    assert details_dict["changes"]["llm_provider"]["new"] == "anthropic"
    assert details_dict["changes"]["temperature"]["old"] == 0.7
    assert details_dict["changes"]["temperature"]["new"] == 0.5
    assert details_dict["change_source"] == "api_call"


def test_from_event_with_minimal_data(db_session, test_event):
    """Test creating a framework event with minimal event data."""
    # Create minimal event data
    event_data = {
        "name": "framework.error",
        "payload": {
            "framework_name": "langchain"
        }
    }
    
    # Update the test event with this data
    test_event.name = "framework.error"  # Update event name
    test_event.data = json.dumps(event_data)
    db_session.commit()
    
    # Create framework event from event
    framework_event = FrameworkEvent.from_event(db_session, test_event)
    
    # Verify
    assert framework_event is not None
    assert framework_event.event_id == test_event.id
    assert framework_event.event_type == "error"
    assert framework_event.framework_name == "langchain"
    assert framework_event.framework_version is None
    assert framework_event.details is None


def test_get_details_dict(db_session, test_event):
    """Test the get_details_dict method."""
    # Create a framework event with JSON details
    framework_event = FrameworkEvent(
        event_id=test_event.id,
        event_type="component_load",
        framework_name="langchain",
        framework_version="0.0.310",
        details=json.dumps({
            "component_type": "retriever",
            "component_name": "VectorStoreRetriever",
            "config": {
                "search_type": "similarity",
                "search_kwargs": {"k": 5}
            }
        })
    )
    
    db_session.add(framework_event)
    db_session.commit()
    
    # Get details as dictionary
    details_dict = framework_event.get_details_dict()
    
    # Verify
    assert isinstance(details_dict, dict)
    assert details_dict["component_type"] == "retriever"
    assert details_dict["component_name"] == "VectorStoreRetriever"
    assert details_dict["config"]["search_type"] == "similarity"
    assert details_dict["config"]["search_kwargs"]["k"] == 5


def test_get_details_dict_with_invalid_json(db_session, test_event):
    """Test the get_details_dict method with invalid JSON."""
    # Create a framework event with invalid JSON details
    framework_event = FrameworkEvent(
        event_id=test_event.id,
        event_type="test_event",
        framework_name="test_framework",
        details="{not valid json}"
    )
    
    db_session.add(framework_event)
    db_session.commit()
    
    # Get details as dictionary should return None for invalid JSON
    details_dict = framework_event.get_details_dict()
    
    # Verify
    assert details_dict is None


def test_events_by_framework(db_session, test_agent):
    """Test the events_by_framework class method."""
    # Create multiple events for the agent
    events = []
    for i in range(5):
        event = Event(
            agent_id=test_agent.id,
            timestamp=datetime.datetime.utcnow(),
            schema_version="1.0",
            name=f"framework.event{i}",
            level="INFO",
            event_type="framework"
        )
        db_session.add(event)
        events.append(event)
    db_session.commit()
    
    # Create framework events with different frameworks
    framework_events = []
    frameworks = ["langchain", "llamaindex", "langchain", "langchain", "llamaindex"]
    
    for i, event in enumerate(events):
        framework_event = FrameworkEvent(
            event_id=event.id,
            event_type=f"event{i}",
            framework_name=frameworks[i],
            framework_version="1.0.0"
        )
        db_session.add(framework_event)
        framework_events.append(framework_event)
    db_session.commit()
    
    # Get events by framework
    langchain_events = FrameworkEvent.events_by_framework(db_session, "langchain")
    llamaindex_events = FrameworkEvent.events_by_framework(db_session, "llamaindex")
    
    # Verify
    assert len(langchain_events) == 3
    assert all(event.framework_name == "langchain" for event in langchain_events)
    
    assert len(llamaindex_events) == 2
    assert all(event.framework_name == "llamaindex" for event in llamaindex_events) 