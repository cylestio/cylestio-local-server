"""
Tests for the LLMInteraction model.
"""
import json
import datetime
import pytest

from src.models.agent import Agent
from src.models.event import Event
from src.models.llm_interaction import LLMInteraction


@pytest.fixture
def test_agent(db_session):
    """Create a test agent for use in LLM interaction tests."""
    agent = Agent(
        agent_id="test-llm-agent",
        name="Test LLM Agent",
        first_seen=datetime.datetime.utcnow(),
        last_seen=datetime.datetime.utcnow()
    )
    db_session.add(agent)
    db_session.commit()
    return agent


@pytest.fixture
def test_event(db_session, test_agent):
    """Create a test event for use in LLM interaction tests."""
    event = Event(
        agent_id=test_agent.id,
        timestamp=datetime.datetime.utcnow(),
        schema_version="1.0",
        name="llm.call.start",
        level="INFO",
        event_type="llm"
    )
    db_session.add(event)
    db_session.commit()
    return event


def test_llm_interaction_creation(db_session, test_event):
    """Test creating a new LLM interaction."""
    # Create a new LLM interaction
    llm_interaction = LLMInteraction(
        event_id=test_event.id,
        interaction_type="start",
        vendor="anthropic",
        model="claude-3-haiku-20240307",
        request_timestamp=datetime.datetime.utcnow(),
        request_data={"messages": [{"role": "user", "content": "Hello"}]}
    )
    
    db_session.add(llm_interaction)
    db_session.commit()
    
    # Query the LLM interaction
    saved_interaction = db_session.query(LLMInteraction).filter(LLMInteraction.id == llm_interaction.id).first()
    
    # Verify
    assert saved_interaction is not None
    assert saved_interaction.event_id == test_event.id
    assert saved_interaction.interaction_type == "start"
    assert saved_interaction.vendor == "anthropic"
    assert saved_interaction.model == "claude-3-haiku-20240307"
    assert saved_interaction.request_timestamp is not None
    assert saved_interaction.request_data == {"messages": [{"role": "user", "content": "Hello"}]}
    assert saved_interaction.response_timestamp is None
    assert saved_interaction.duration_ms is None
    assert saved_interaction.input_tokens is None
    assert saved_interaction.output_tokens is None
    assert saved_interaction.total_tokens is None
    assert saved_interaction.response_content is None
    assert saved_interaction.response_id is None
    assert saved_interaction.stop_reason is None


def test_llm_interaction_relationships(db_session, test_event):
    """Test LLM interaction relationships."""
    # Create a new LLM interaction
    llm_interaction = LLMInteraction(
        event_id=test_event.id,
        interaction_type="start",
        vendor="anthropic",
        model="claude-3-haiku-20240307"
    )
    
    db_session.add(llm_interaction)
    db_session.commit()
    
    # Query the LLM interaction
    saved_interaction = db_session.query(LLMInteraction).filter(
        LLMInteraction.id == llm_interaction.id
    ).first()
    
    # Verify relationships
    assert saved_interaction.event.id == test_event.id
    assert test_event.llm_interaction.id == saved_interaction.id


def test_from_event_start(db_session, test_agent):
    """Test creating an LLM interaction from an event for start."""
    # Create an event with LLM start attributes
    event = Event(
        agent_id=test_agent.id,
        timestamp=datetime.datetime.utcnow(),
        schema_version="1.0",
        name="llm.call.start",
        level="INFO",
        event_type="llm"
    )
    db_session.add(event)
    db_session.commit()
    
    # Create telemetry data
    telemetry_data = {
        "attributes": {
            "llm.vendor": "anthropic",
            "llm.model": "claude-3-haiku-20240307",
            "llm.request.timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "llm.request.data": {"messages": [{"role": "user", "content": "Hello"}]}
        }
    }
    
    # Create LLM interaction from event
    llm_interaction = LLMInteraction.from_event(db_session, event, telemetry_data)
    
    # Verify
    assert llm_interaction is not None
    assert llm_interaction.event_id == event.id
    assert llm_interaction.interaction_type == "start"
    assert llm_interaction.vendor == "anthropic"
    assert llm_interaction.model == "claude-3-haiku-20240307"
    assert llm_interaction.request_timestamp is not None
    assert llm_interaction.request_data == {"messages": [{"role": "user", "content": "Hello"}]}


def test_from_event_finish(db_session, test_agent):
    """Test creating an LLM interaction from an event for finish."""
    # Create an event with LLM finish attributes
    event = Event(
        agent_id=test_agent.id,
        timestamp=datetime.datetime.utcnow(),
        schema_version="1.0",
        name="llm.call.finish",
        level="INFO",
        event_type="llm"
    )
    db_session.add(event)
    db_session.commit()
    
    # Create telemetry data
    telemetry_data = {
        "attributes": {
            "llm.vendor": "anthropic",
            "llm.model": "claude-3-haiku-20240307",
            "llm.request.timestamp": (datetime.datetime.utcnow() - datetime.timedelta(seconds=1)).isoformat() + "Z",
            "llm.response.timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "llm.response.duration_ms": 950,
            "llm.usage.input_tokens": 10,
            "llm.usage.output_tokens": 20,
            "llm.usage.total_tokens": 30,
            "llm.response.content": {"type": "text", "text": "Hello, human!"},
            "llm.response.id": "resp_12345",
            "llm.response.stop_reason": "end_turn"
        }
    }
    
    # Create LLM interaction from event
    llm_interaction = LLMInteraction.from_event(db_session, event, telemetry_data)
    
    # Verify
    assert llm_interaction is not None
    assert llm_interaction.event_id == event.id
    assert llm_interaction.interaction_type == "finish"
    assert llm_interaction.vendor == "anthropic"
    assert llm_interaction.model == "claude-3-haiku-20240307"
    assert llm_interaction.request_timestamp is not None
    assert llm_interaction.response_timestamp is not None
    assert llm_interaction.duration_ms == 950
    assert llm_interaction.input_tokens == 10
    assert llm_interaction.output_tokens == 20
    assert llm_interaction.total_tokens == 30
    assert llm_interaction.response_content == {"type": "text", "text": "Hello, human!"}
    assert llm_interaction.response_id == "resp_12345"
    assert llm_interaction.stop_reason == "end_turn"


def test_get_cost_estimate(db_session, test_event):
    """Test calculating cost estimates for LLM interactions."""
    # Create an LLM interaction with token usage
    llm_interaction = LLMInteraction(
        event_id=test_event.id,
        interaction_type="finish",
        vendor="anthropic",
        model="claude-3-haiku-20240307",
        input_tokens=1000,
        output_tokens=500,
        total_tokens=1500
    )
    db_session.add(llm_interaction)
    db_session.commit()
    
    # Calculate cost with standard price
    cost = llm_interaction.get_cost_estimate(input_price_per_1k=1.0, output_price_per_1k=3.0)
    
    # Verify: (1000 * 1.0) / 1000 + (500 * 3.0) / 1000 = 1.0 + 1.5 = 2.5
    assert cost == 2.5


def test_get_request_content(db_session, test_event):
    """Test extracting user messages from request data."""
    # Create an LLM interaction with request data
    llm_interaction = LLMInteraction(
        event_id=test_event.id,
        interaction_type="start",
        vendor="anthropic",
        model="claude-3-haiku-20240307",
        request_data={
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Tell me about Python."},
                {"role": "assistant", "content": "Python is great!"},
                {"role": "user", "content": "And JavaScript?"}
            ]
        }
    )
    db_session.add(llm_interaction)
    db_session.commit()
    
    # Get user messages
    user_messages = llm_interaction.get_request_content()
    
    # Verify
    assert len(user_messages) == 2
    assert "Tell me about Python." in user_messages
    assert "And JavaScript?" in user_messages


def test_get_request_content_with_structured_content(db_session, test_event):
    """Test extracting user messages from structured content."""
    # Create an LLM interaction with structured content
    llm_interaction = LLMInteraction(
        event_id=test_event.id,
        interaction_type="start",
        vendor="anthropic",
        model="claude-3-haiku-20240307",
        request_data={
            "messages": [
                {"role": "user", "content": [
                    {"type": "text", "text": "Hello!"},
                    {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": "..."}},
                    {"type": "text", "text": "What's in this image?"}
                ]}
            ]
        }
    )
    db_session.add(llm_interaction)
    db_session.commit()
    
    # Get user messages
    user_messages = llm_interaction.get_request_content()
    
    # Verify
    assert len(user_messages) == 2
    assert "Hello!" in user_messages
    assert "What's in this image?" in user_messages


def test_get_response_content(db_session, test_event):
    """Test extracting assistant responses from response content."""
    # Create an LLM interaction with response content
    llm_interaction = LLMInteraction(
        event_id=test_event.id,
        interaction_type="finish",
        vendor="anthropic",
        model="claude-3-haiku-20240307",
        response_content=[
            {"type": "text", "text": "Python is a popular programming language."},
            {"type": "text", "text": "It's known for its readability and versatility."}
        ]
    )
    db_session.add(llm_interaction)
    db_session.commit()
    
    # Get response content
    response_text = llm_interaction.get_response_content()
    
    # Verify
    assert len(response_text) == 2
    assert "Python is a popular programming language." in response_text
    assert "It's known for its readability and versatility." in response_text 