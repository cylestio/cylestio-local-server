"""
Tests for the LLMAttribute model.
"""
import json
import datetime
import pytest

from src.models.agent import Agent
from src.models.event import Event
from src.models.llm_interaction import LLMInteraction
from src.models.llm_attribute import LLMAttribute


@pytest.fixture
def test_agent(db_session):
    """Create a test agent for use in LLM attribute tests."""
    agent = Agent(
        agent_id="test-attr-agent",
        name="Test Attr Agent",
        first_seen=datetime.datetime.utcnow(),
        last_seen=datetime.datetime.utcnow()
    )
    db_session.add(agent)
    db_session.commit()
    return agent


@pytest.fixture
def test_event(db_session, test_agent):
    """Create a test event for use in LLM attribute tests."""
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


@pytest.fixture
def test_llm_interaction(db_session, test_event):
    """Create a test LLM interaction for use in LLM attribute tests."""
    llm_interaction = LLMInteraction(
        event_id=test_event.id,
        interaction_type="start",
        vendor="anthropic",
        model="claude-3-haiku-20240307"
    )
    db_session.add(llm_interaction)
    db_session.commit()
    return llm_interaction


def test_llm_attribute_creation(db_session, test_llm_interaction):
    """Test creating a new LLM attribute."""
    # Create a new LLM attribute
    llm_attribute = LLMAttribute(
        llm_interaction_id=test_llm_interaction.id,
        key="temperature",
        value_numeric=0.7,
        value_text=None,
        value_boolean=None,
        value_type="numeric"
    )
    
    db_session.add(llm_attribute)
    db_session.commit()
    
    # Query the LLM attribute
    saved_attribute = db_session.query(LLMAttribute).filter(
        LLMAttribute.llm_interaction_id == test_llm_interaction.id,
        LLMAttribute.key == "temperature"
    ).first()
    
    # Verify
    assert saved_attribute is not None
    assert saved_attribute.llm_interaction_id == test_llm_interaction.id
    assert saved_attribute.key == "temperature"
    assert saved_attribute.value_numeric == 0.7
    assert saved_attribute.value_text is None
    assert saved_attribute.value_boolean is None
    assert saved_attribute.value_type == "numeric"


def test_llm_attribute_relationships(db_session, test_llm_interaction):
    """Test LLM attribute relationships."""
    # Create a new LLM attribute
    llm_attribute = LLMAttribute(
        llm_interaction_id=test_llm_interaction.id,
        key="max_tokens",
        value_numeric=1024,
        value_type="numeric"
    )
    
    db_session.add(llm_attribute)
    db_session.commit()
    
    # Query the LLM attribute
    saved_attribute = db_session.query(LLMAttribute).filter(
        LLMAttribute.llm_interaction_id == test_llm_interaction.id,
        LLMAttribute.key == "max_tokens"
    ).first()
    
    # Verify relationships
    assert saved_attribute.llm_interaction.id == test_llm_interaction.id
    
    # Verify from the other direction
    assert test_llm_interaction.attributes[0].id == saved_attribute.id
    assert test_llm_interaction.attributes[0].key == "max_tokens"


def test_create_from_value_text(db_session, test_llm_interaction):
    """Test creating an LLM attribute from a text value."""
    # Create an attribute from a text value
    attr = LLMAttribute.create_from_value(
        db_session,
        test_llm_interaction.id,
        "system_prompt",
        "You are a helpful assistant."
    )
    
    db_session.commit()
    
    # Verify
    assert attr is not None
    assert attr.key == "system_prompt"
    assert attr.value_type == "text"
    assert attr.value_text == "You are a helpful assistant."
    assert attr.value_numeric is None
    assert attr.value_boolean is None
    
    # Check the value property
    assert attr.value == "You are a helpful assistant."


def test_create_from_value_numeric(db_session, test_llm_interaction):
    """Test creating an LLM attribute from a numeric value."""
    # Create attributes from different numeric values
    int_attr = LLMAttribute.create_from_value(
        db_session,
        test_llm_interaction.id,
        "max_tokens",
        1024
    )
    
    float_attr = LLMAttribute.create_from_value(
        db_session,
        test_llm_interaction.id,
        "temperature",
        0.7
    )
    
    db_session.commit()
    
    # Verify integer attribute
    assert int_attr.value_type == "numeric"
    assert int_attr.value_numeric == 1024.0
    assert int_attr.value == 1024.0
    
    # Verify float attribute
    assert float_attr.value_type == "numeric"
    assert float_attr.value_numeric == 0.7
    assert float_attr.value == 0.7


def test_create_from_value_boolean(db_session, test_llm_interaction):
    """Test creating an LLM attribute from a boolean value."""
    # Create attributes from boolean values
    true_attr = LLMAttribute.create_from_value(
        db_session,
        test_llm_interaction.id,
        "stream",
        True
    )
    
    false_attr = LLMAttribute.create_from_value(
        db_session,
        test_llm_interaction.id,
        "cache",
        False
    )
    
    db_session.commit()
    
    # Verify true attribute
    assert true_attr.value_type == "boolean"
    assert true_attr.value_boolean is True
    assert true_attr.value is True
    
    # Verify false attribute
    assert false_attr.value_type == "boolean"
    assert false_attr.value_boolean is False
    assert false_attr.value is False


def test_create_from_value_json(db_session, test_llm_interaction):
    """Test creating an LLM attribute from a JSON value."""
    # Create an attribute from a dict
    dict_attr = LLMAttribute.create_from_value(
        db_session,
        test_llm_interaction.id,
        "user_metadata",
        {"user_id": "12345", "role": "admin"}
    )
    
    # Create an attribute from a list
    list_attr = LLMAttribute.create_from_value(
        db_session,
        test_llm_interaction.id,
        "tags",
        ["important", "urgent", "customer"]
    )
    
    db_session.commit()
    
    # Verify dict attribute
    assert dict_attr.value_type == "json"
    assert dict_attr.value_text == json.dumps({"user_id": "12345", "role": "admin"})
    assert dict_attr.value == {"user_id": "12345", "role": "admin"}
    
    # Verify list attribute
    assert list_attr.value_type == "json"
    assert list_attr.value_text == json.dumps(["important", "urgent", "customer"])
    assert list_attr.value == ["important", "urgent", "customer"]


def test_create_from_value_none(db_session, test_llm_interaction):
    """Test creating an LLM attribute from a None value."""
    # Create an attribute from None
    attr = LLMAttribute.create_from_value(
        db_session,
        test_llm_interaction.id,
        "optional_param",
        None
    )
    
    db_session.commit()
    
    # Verify
    assert attr.value_type == "text"
    assert attr.value_text is None
    assert attr.value is None


def test_value_property_invalid_json(db_session, test_llm_interaction):
    """Test the value property with invalid JSON."""
    # Create an attribute with invalid JSON
    attr = LLMAttribute(
        llm_interaction_id=test_llm_interaction.id,
        key="invalid_json",
        value_text="{not valid json}",
        value_type="json"
    )
    
    db_session.add(attr)
    db_session.commit()
    
    # Verify that value returns None for invalid JSON
    assert attr.value is None 