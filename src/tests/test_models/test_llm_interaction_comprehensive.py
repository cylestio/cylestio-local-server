"""
Comprehensive tests for the LLMInteraction model.

These tests validate the LLMInteraction model's functionality,
including data extraction logic, field population, and relationships.
"""
import json
import datetime
import pytest
import random

from sqlalchemy import func
from models.llm_interaction import LLMInteraction
from tests.test_utils import (
    generate_agent, generate_event, generate_llm_interaction_data
)


class TestLLMInteractionBasic:
    """Basic tests for LLMInteraction model."""
    
    def test_llm_interaction_creation(self, db_session, test_event):
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
        saved_interaction = db_session.query(LLMInteraction).filter(
            LLMInteraction.id == llm_interaction.id
        ).first()
        
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


class TestLLMInteractionFromEvent:
    """Tests for creating LLMInteraction from event data."""
    
    def test_from_event_start(self, db_session, test_llm_events):
        """Test creating an LLM interaction from a start event."""
        start_event, _ = test_llm_events
        
        # Create telemetry data
        telemetry_data = generate_llm_interaction_data(interaction_type="start")
        
        # Create LLM interaction from event
        llm_interaction = LLMInteraction.from_event(db_session, start_event, telemetry_data)
        
        # Verify basic fields
        assert llm_interaction is not None
        assert llm_interaction.event_id == start_event.id
        assert llm_interaction.interaction_type == "start"
        assert llm_interaction.vendor == "anthropic"
        assert llm_interaction.model == "claude-3-haiku-20240307"
        assert llm_interaction.request_timestamp is not None
        assert llm_interaction.request_data is not None
        
        # Verify data extraction logic
        assert llm_interaction.request_data["messages"][0]["content"] == "Hello world"
        assert llm_interaction.temperature == 0.7
        assert llm_interaction.max_tokens == 1000
    
    def test_from_event_finish(self, db_session, test_llm_events):
        """Test creating an LLM interaction from a finish event."""
        _, finish_event = test_llm_events
        
        # Create telemetry data
        telemetry_data = generate_llm_interaction_data(interaction_type="finish")
        
        # Create LLM interaction from event
        llm_interaction = LLMInteraction.from_event(db_session, finish_event, telemetry_data)
        
        # Verify
        assert llm_interaction is not None
        assert llm_interaction.event_id == finish_event.id
        assert llm_interaction.interaction_type == "finish"
        assert llm_interaction.vendor == "anthropic"
        assert llm_interaction.model == "claude-3-haiku-20240307"
        assert llm_interaction.response_timestamp is not None
        assert llm_interaction.duration_ms == 450
        assert llm_interaction.input_tokens == 15
        assert llm_interaction.output_tokens == 45
        assert llm_interaction.total_tokens == 60
        assert llm_interaction.response_content == {"type": "text", "text": "Hello, human!"}
        assert llm_interaction.response_id is not None
        assert llm_interaction.stop_reason == "end_turn"
    
    def test_from_event_missing_fields(self, db_session, test_llm_events):
        """Test handling of missing fields in event data."""
        start_event, _ = test_llm_events
        
        # Create minimal telemetry data with missing fields
        telemetry_data = {
            "attributes": {
                "llm.vendor": "anthropic"
                # Missing model, request timestamp, etc.
            }
        }
        
        # Create LLM interaction from event
        llm_interaction = LLMInteraction.from_event(db_session, start_event, telemetry_data)
        
        # Verify it handles missing fields gracefully
        assert llm_interaction is not None
        assert llm_interaction.event_id == start_event.id
        assert llm_interaction.vendor == "anthropic"
        assert llm_interaction.model is None
        assert llm_interaction.request_timestamp is None
        assert llm_interaction.request_data is None


class TestLLMInteractionRelationships:
    """Tests for LLM interaction relationships."""
    
    def test_llm_interaction_event_relationship(self, db_session, test_llm_events):
        """Test relationship between LLM interaction and Event."""
        start_event, _ = test_llm_events
        
        # Create an LLM interaction
        llm_interaction = LLMInteraction(
            event_id=start_event.id,
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
        assert saved_interaction.event.id == start_event.id
        assert start_event.llm_interaction.id == saved_interaction.id


class TestLLMInteractionUtilityMethods:
    """Tests for LLMInteraction utility methods."""
    
    def test_get_cost_estimate(self, db_session, test_event):
        """Test calculating cost estimates for different models."""
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
    
    def test_get_request_content(self, db_session, test_event):
        """Test extracting user messages from request data for different formats."""
        # Test with Anthropic format
        anthropic_interaction = LLMInteraction(
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
        db_session.add(anthropic_interaction)
        
        # Test with OpenAI format
        openai_interaction = LLMInteraction(
            event_id=test_event.id,
            interaction_type="start",
            vendor="openai",
            model="gpt-4-turbo",
            request_data={
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Tell me about Python."}
                ]
            }
        )
        db_session.add(openai_interaction)
        
        db_session.commit()
        
        # Get user messages from Anthropic
        anthropic_messages = anthropic_interaction.get_request_content()
        
        # Verify - messages from all roles are included
        assert len(anthropic_messages) == 4
        assert "You are a helpful assistant." in anthropic_messages
        assert "Tell me about Python." in anthropic_messages
        assert "Python is great!" in anthropic_messages
        assert "And JavaScript?" in anthropic_messages
        
        # Get user messages from OpenAI
        openai_messages = openai_interaction.get_request_content()
        
        # Verify
        assert len(openai_messages) == 2
        assert "You are a helpful assistant." in openai_messages
        assert "Tell me about Python." in openai_messages


class TestLLMInteractionVendorSpecific:
    """Tests for vendor-specific LLM interaction behavior."""
    
    def test_anthropic_specific_fields(self, db_session, test_event):
        """Test Anthropic-specific fields in LLM interactions."""
        # Create telemetry data with Anthropic-specific fields
        telemetry_data = {
            "attributes": {
                "llm.vendor": "anthropic",
                "llm.model": "claude-3-haiku-20240307",
                "llm.request.timestamp": datetime.datetime.utcnow().isoformat() + "Z",
                "llm.request.data": {"messages": [{"role": "user", "content": "Hello"}]},
                "llm.config.temperature": 0.7,
                "llm.config.max_tokens": 1000,
                "llm.config.anthropic.system": "You are a helpful AI assistant.",
                "llm.config.anthropic.top_k": 10,
                "llm.config.anthropic.top_p": 0.95
            }
        }
        
        # Create LLM interaction from event
        llm_interaction = LLMInteraction.from_event(db_session, test_event, telemetry_data)
        db_session.add(llm_interaction)
        db_session.commit()
        
        # Verify Anthropic-specific fields are stored in raw_attributes
        assert llm_interaction.raw_attributes is not None
        assert "llm.config.anthropic.system" in llm_interaction.raw_attributes
        assert "llm.config.anthropic.top_k" in llm_interaction.raw_attributes
        assert "llm.config.anthropic.top_p" in llm_interaction.raw_attributes
        
    def test_openai_specific_fields(self, db_session, test_event):
        """Test OpenAI-specific fields in LLM interactions."""
        # Create telemetry data with OpenAI-specific fields
        telemetry_data = {
            "attributes": {
                "llm.vendor": "openai",
                "llm.model": "gpt-4-turbo",
                "llm.request.timestamp": datetime.datetime.utcnow().isoformat() + "Z",
                "llm.request.data": {"messages": [{"role": "user", "content": "Hello"}]},
                "llm.config.temperature": 0.7,
                "llm.config.max_tokens": 1000,
                "llm.config.openai.presence_penalty": 0.1,
                "llm.config.openai.frequency_penalty": 0.2,
                "llm.config.openai.logit_bias": {"50256": -100}
            }
        }
        
        # Create LLM interaction from event
        llm_interaction = LLMInteraction.from_event(db_session, test_event, telemetry_data)
        db_session.add(llm_interaction)
        db_session.commit()
        
        # Verify OpenAI-specific fields
        assert llm_interaction.presence_penalty == 0.1
        assert llm_interaction.frequency_penalty == 0.2
        assert "llm.config.openai.logit_bias" in llm_interaction.raw_attributes


class TestLLMInteractionEdgeCases:
    """Tests for LLM interaction edge cases."""
    
    def test_unexpected_attribute_format(self, db_session, test_event):
        """Test handling of unexpected attribute formats."""
        # Create telemetry data with unexpected formats
        telemetry_data = {
            "attributes": {
                "llm.vendor": ["anthropic"],  # List instead of string
                "llm.model": 12345,  # Number instead of string
                "llm.request.timestamp": True,  # Boolean instead of string
                "llm.request.data": "not_a_dict"  # String instead of dict
            }
        }
        
        # Create LLM interaction from event
        llm_interaction = LLMInteraction.from_event(db_session, test_event, telemetry_data)
        db_session.add(llm_interaction)
        db_session.commit()
        
        # Verify it handles unexpected formats
        assert llm_interaction is not None
        # The model should handle type conversions or use defaults
        assert llm_interaction.vendor == "['anthropic']"  # Converted to string
        assert llm_interaction.model == "12345"  # Converted to string
        # Complex conversions might fail and return None
        assert llm_interaction.request_data == "not_a_dict"  # Stored as is
    
    def test_nested_complex_data(self, db_session, test_event):
        """Test handling of deeply nested complex data structures."""
        # Create complex nested data structure
        complex_data = {
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": [
                    {"type": "text", "text": "Hello"},
                    {"type": "image", "image_url": "http://example.com/image.jpg"}
                ]}
            ],
            "tools": [
                {"name": "search", "description": "Search the web", "parameters": {"query": "string"}},
                {"name": "calculator", "description": "Perform calculations"}
            ],
            "metadata": {
                "user_id": "test_user",
                "session_id": "test_session",
                "tags": ["test", "complex", "data"]
            }
        }
        
        # Create telemetry data with complex nested structure
        telemetry_data = {
            "attributes": {
                "llm.vendor": "anthropic",
                "llm.model": "claude-3-haiku-20240307",
                "llm.request.timestamp": datetime.datetime.utcnow().isoformat() + "Z",
                "llm.request.data": complex_data
            }
        }
        
        # Create LLM interaction from event
        llm_interaction = LLMInteraction.from_event(db_session, test_event, telemetry_data)
        db_session.add(llm_interaction)
        db_session.commit()
        
        # Verify it handles complex data properly
        assert llm_interaction is not None
        assert llm_interaction.request_data == complex_data
        
        # Test getting user message from complex structure
        content = llm_interaction.get_request_content()
        assert "You are a helpful assistant." in content
        assert "Hello" in content  # Should extract text from complex message


@pytest.mark.parametrize("vendor,model", [
    ("anthropic", "claude-3-haiku-20240307"),
    ("anthropic", "claude-3-sonnet-20240229"),
    ("anthropic", "claude-3-opus-20240229"),
    ("openai", "gpt-4-turbo"),
    ("openai", "gpt-3.5-turbo"),
    ("cohere", "command"),
    ("mistral", "mistral-large")
])
class TestLLMInteractionParameterized:
    """Parameterized tests for different LLM vendors and models."""
    
    def test_vendor_model_combinations(self, db_session, test_event, vendor, model):
        """Test various vendor and model combinations."""
        # Create LLM interaction with specific vendor/model
        llm_interaction = LLMInteraction(
            event_id=test_event.id,
            interaction_type="start",
            vendor=vendor,
            model=model,
            request_timestamp=datetime.datetime.utcnow()
        )
        
        db_session.add(llm_interaction)
        db_session.commit()
        
        # Verify
        saved_interaction = db_session.query(LLMInteraction).filter(
            LLMInteraction.id == llm_interaction.id
        ).first()
        
        assert saved_interaction is not None
        assert saved_interaction.vendor == vendor
        assert saved_interaction.model == model 