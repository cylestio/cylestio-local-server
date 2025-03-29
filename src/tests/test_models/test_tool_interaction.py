"""
Tests for the ToolInteraction model.
"""
import json
import datetime
import pytest

from models.agent import Agent
from models.event import Event
from models.tool_interaction import ToolInteraction


@pytest.fixture
def test_agent(db_session):
    """Create a test agent for use in tool interaction tests."""
    agent = Agent(
        agent_id="test-tool-agent",
        name="Test Tool Agent",
        first_seen=datetime.datetime.utcnow(),
        last_seen=datetime.datetime.utcnow()
    )
    db_session.add(agent)
    db_session.commit()
    return agent


@pytest.fixture
def test_event(db_session, test_agent):
    """Create a test event for use in tool interaction tests."""
    event = Event(
        agent_id=test_agent.id,
        timestamp=datetime.datetime.utcnow(),
        schema_version="1.0",
        name="tool.call.start",
        level="INFO",
        event_type="tool"
    )
    db_session.add(event)
    db_session.commit()
    return event


def test_tool_interaction_creation(db_session, test_event):
    """Test creating a new tool interaction."""
    # Create a new tool interaction
    tool_interaction = ToolInteraction(
        event_id=test_event.id,
        interaction_type="start",
        tool_name="web_search",
        parameters=json.dumps({"query": "What is the weather today?"})
    )
    
    db_session.add(tool_interaction)
    db_session.commit()
    
    # Query the tool interaction
    saved_interaction = db_session.query(ToolInteraction).filter(
        ToolInteraction.event_id == test_event.id
    ).first()
    
    # Verify
    assert saved_interaction is not None
    assert saved_interaction.event_id == test_event.id
    assert saved_interaction.interaction_type == "start"
    assert saved_interaction.tool_name == "web_search"
    assert json.loads(saved_interaction.parameters) == {"query": "What is the weather today?"}
    assert saved_interaction.result is None
    assert saved_interaction.error is None
    assert saved_interaction.status_code is None
    assert saved_interaction.response_time_ms is None


def test_tool_interaction_relationships(db_session, test_event):
    """Test tool interaction relationships."""
    # Create a new tool interaction
    tool_interaction = ToolInteraction(
        event_id=test_event.id,
        interaction_type="start",
        tool_name="file_search",
        parameters=json.dumps({"pattern": "*.py"})
    )
    
    db_session.add(tool_interaction)
    db_session.commit()
    
    # Verify the relationship with the event
    assert tool_interaction.event.id == test_event.id
    assert tool_interaction.event.name == "tool.call.start"

    # Verify from the other direction (event to tool interaction)
    assert test_event.tool_interaction.id == tool_interaction.id
    assert test_event.tool_interaction.tool_name == "file_search"


def test_from_event_start(db_session, test_event):
    """Test creating a tool interaction from a start event."""
    # Create event data for tool start
    event_data = {
        "name": "tool.call.start",
        "payload": {
            "tool_name": "api_request",
            "parameters": {
                "url": "https://api.example.com/data",
                "method": "GET",
                "headers": {"Authorization": "Bearer token123"}
            }
        }
    }
    
    # Update the test event with this data
    test_event.data = json.dumps(event_data)
    db_session.commit()
    
    # Create tool interaction from event
    tool_interaction = ToolInteraction.from_event(db_session, test_event)
    
    # Verify
    assert tool_interaction is not None
    assert tool_interaction.event_id == test_event.id
    assert tool_interaction.interaction_type == "start"
    assert tool_interaction.tool_name == "api_request"
    assert json.loads(tool_interaction.parameters) == {
        "url": "https://api.example.com/data",
        "method": "GET",
        "headers": {"Authorization": "Bearer token123"}
    }
    assert tool_interaction.result is None
    assert tool_interaction.error is None


def test_from_event_finish(db_session, test_event):
    """Test creating a tool interaction from a finish event."""
    # Create event data for tool finish
    event_data = {
        "name": "tool.call.finish",
        "payload": {
            "tool_name": "weather_api",
            "result": {
                "temperature": 72,
                "conditions": "sunny",
                "location": "San Francisco"
            },
            "status_code": 200,
            "response_time_ms": 150
        }
    }
    
    # Update the test event with this data
    test_event.name = "tool.call.finish"  # Update event name
    test_event.data = json.dumps(event_data)
    db_session.commit()
    
    # Create tool interaction from event
    tool_interaction = ToolInteraction.from_event(db_session, test_event)
    
    # Verify
    assert tool_interaction is not None
    assert tool_interaction.event_id == test_event.id
    assert tool_interaction.interaction_type == "finish"
    assert tool_interaction.tool_name == "weather_api"
    assert tool_interaction.parameters is None
    assert json.loads(tool_interaction.result) == {
        "temperature": 72,
        "conditions": "sunny",
        "location": "San Francisco"
    }
    assert tool_interaction.status_code == 200
    assert tool_interaction.response_time_ms == 150
    assert tool_interaction.error is None


def test_from_event_error(db_session, test_event):
    """Test creating a tool interaction from an error event."""
    # Create event data for tool error
    event_data = {
        "name": "tool.call.error",
        "payload": {
            "tool_name": "database_query",
            "error": "Connection timeout",
            "status_code": 500,
            "response_time_ms": 3000
        }
    }
    
    # Update the test event with this data
    test_event.name = "tool.call.error"  # Update event name
    test_event.data = json.dumps(event_data)
    db_session.commit()
    
    # Create tool interaction from event
    tool_interaction = ToolInteraction.from_event(db_session, test_event)
    
    # Verify
    assert tool_interaction is not None
    assert tool_interaction.event_id == test_event.id
    assert tool_interaction.interaction_type == "error"
    assert tool_interaction.tool_name == "database_query"
    assert tool_interaction.parameters is None
    assert tool_interaction.result is None
    assert tool_interaction.error == "Connection timeout"
    assert tool_interaction.status_code == 500
    assert tool_interaction.response_time_ms == 3000


def test_get_parameters_dict(db_session, test_event):
    """Test the get_parameters_dict method."""
    # Create a tool interaction with JSON parameters
    tool_interaction = ToolInteraction(
        event_id=test_event.id,
        interaction_type="start",
        tool_name="image_generation",
        parameters=json.dumps({
            "prompt": "A sunset over mountains",
            "style": "photorealistic",
            "dimensions": {"width": 1024, "height": 768}
        })
    )
    
    db_session.add(tool_interaction)
    db_session.commit()
    
    # Get parameters as dictionary
    params_dict = tool_interaction.get_parameters_dict()
    
    # Verify
    assert isinstance(params_dict, dict)
    assert params_dict["prompt"] == "A sunset over mountains"
    assert params_dict["style"] == "photorealistic"
    assert params_dict["dimensions"]["width"] == 1024
    assert params_dict["dimensions"]["height"] == 768


def test_get_parameters_dict_with_invalid_json(db_session, test_event):
    """Test the get_parameters_dict method with invalid JSON."""
    # Create a tool interaction with invalid JSON parameters
    tool_interaction = ToolInteraction(
        event_id=test_event.id,
        interaction_type="start",
        tool_name="test_tool",
        parameters="{not valid json}"
    )
    
    db_session.add(tool_interaction)
    db_session.commit()
    
    # Get parameters as dictionary should return None for invalid JSON
    params_dict = tool_interaction.get_parameters_dict()
    
    # Verify
    assert params_dict is None


def test_get_result_dict(db_session, test_event):
    """Test the get_result_dict method."""
    # Create a tool interaction with JSON result
    tool_interaction = ToolInteraction(
        event_id=test_event.id,
        interaction_type="finish",
        tool_name="data_analysis",
        result=json.dumps({
            "mean": 45.6,
            "median": 42.0,
            "outliers": [12, 98, 102]
        })
    )
    
    db_session.add(tool_interaction)
    db_session.commit()
    
    # Get result as dictionary
    result_dict = tool_interaction.get_result_dict()
    
    # Verify
    assert isinstance(result_dict, dict)
    assert result_dict["mean"] == 45.6
    assert result_dict["median"] == 42.0
    assert result_dict["outliers"] == [12, 98, 102]


def test_get_result_dict_with_invalid_json(db_session, test_event):
    """Test the get_result_dict method with invalid JSON."""
    # Create a tool interaction with invalid JSON result
    tool_interaction = ToolInteraction(
        event_id=test_event.id,
        interaction_type="finish",
        tool_name="test_tool",
        result="{not valid json}"
    )
    
    db_session.add(tool_interaction)
    db_session.commit()
    
    # Get result as dictionary should return None for invalid JSON
    result_dict = tool_interaction.get_result_dict()
    
    # Verify
    assert result_dict is None 