#!/usr/bin/env python3
"""
Test script to validate the LLM parameter extraction capability.
This script tests the extraction of configuration parameters from LLM events, 
particularly temperature and max_tokens, across different vendor formats.
"""
import sys
import os
import json
from pathlib import Path
from datetime import datetime
import unittest
from unittest.mock import MagicMock

# Add the src directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.base import Base, init_db
from models.event import Event
from models.llm_interaction import LLMInteraction

# Configure a test database
TEST_DB_URL = "sqlite:///:memory:"

class TestLLMParameterExtraction(unittest.TestCase):
    """Test suite for LLM parameter extraction functionality."""
    
    def setUp(self):
        """Set up test environment."""
        # Initialize in-memory test database
        self.engine = init_db(TEST_DB_URL, echo=False)
        Base.metadata.create_all(self.engine)
        
        # Create a mock db_session
        self.db_session = MagicMock()
        
    def test_anthropic_parameter_extraction(self):
        """Test extraction of parameters from Anthropic format."""
        # Create a test event
        event = Event(
            id=1,
            agent_id="test-agent",
            timestamp=datetime.now(),
            schema_version="1.0",
            name="llm.call.start",
            level="INFO",
            event_type="llm"
        )
        
        # Create telemetry data with Anthropic format
        telemetry_data = {
            "attributes": {
                "llm.vendor": "anthropic",
                "llm.model": "claude-3-haiku",
                "llm.request.timestamp": "2025-03-27T19:05:08.253167",
                "llm.request.temperature": 0.7,
                "llm.request.max_tokens": 1024,
                "llm.request.data": {
                    "messages": [{"role": "user", "content": "Hello"}],
                    "model": "claude-3-haiku",
                    "temperature": 0.7,
                    "max_tokens": 1024
                }
            }
        }
        
        # Call the from_event_with_telemetry method
        llm_interaction = LLMInteraction.from_event_with_telemetry(
            self.db_session, event, telemetry_data
        )
        
        # Assertions
        self.assertEqual(llm_interaction.temperature, 0.7)
        self.assertEqual(llm_interaction.max_tokens, 1024)
        self.assertEqual(llm_interaction.vendor, "anthropic")
        
    def test_anthropic_max_tokens_to_sample(self):
        """Test extraction of max_tokens from Anthropic's max_tokens_to_sample."""
        # Create a test event
        event = Event(
            id=2,
            agent_id="test-agent",
            timestamp=datetime.now(),
            schema_version="1.0",
            name="llm.call.start",
            level="INFO",
            event_type="llm"
        )
        
        # Create telemetry data with Anthropic format using max_tokens_to_sample
        telemetry_data = {
            "attributes": {
                "llm.vendor": "anthropic",
                "llm.model": "claude-3-haiku",
                "llm.request.timestamp": "2025-03-27T19:05:08.253167",
                "llm.request.temperature": 0.7,
                "llm.request.data": {
                    "messages": [{"role": "user", "content": "Hello"}],
                    "model": "claude-3-haiku",
                    "temperature": 0.7,
                    "max_tokens_to_sample": 1024
                }
            }
        }
        
        # Call the from_event_with_telemetry method
        llm_interaction = LLMInteraction.from_event_with_telemetry(
            self.db_session, event, telemetry_data
        )
        
        # Assertions
        self.assertEqual(llm_interaction.temperature, 0.7)
        self.assertEqual(llm_interaction.max_tokens, 1024)
        self.assertEqual(llm_interaction.vendor, "anthropic")
        
    def test_openai_parameter_extraction(self):
        """Test extraction of parameters from OpenAI format."""
        # Create a test event
        event = Event(
            id=3,
            agent_id="test-agent",
            timestamp=datetime.now(),
            schema_version="1.0",
            name="llm.call.start",
            level="INFO",
            event_type="llm"
        )
        
        # Create telemetry data with OpenAI format
        telemetry_data = {
            "attributes": {
                "llm.vendor": "openai",
                "llm.model": "gpt-4",
                "llm.request.timestamp": "2025-03-27T19:05:08.253167",
                "llm.request.data": {
                    "messages": [{"role": "user", "content": "Hello"}],
                    "model": "gpt-4",
                    "temperature": 0.5,
                    "max_tokens": 2048,
                    "top_p": 0.9,
                    "frequency_penalty": 0.1,
                    "presence_penalty": 0.0
                }
            }
        }
        
        # Call the from_event_with_telemetry method
        llm_interaction = LLMInteraction.from_event_with_telemetry(
            self.db_session, event, telemetry_data
        )
        
        # Assertions
        self.assertEqual(llm_interaction.temperature, 0.5)
        self.assertEqual(llm_interaction.max_tokens, 2048)
        self.assertEqual(llm_interaction.top_p, 0.9)
        self.assertEqual(llm_interaction.frequency_penalty, 0.1)
        self.assertEqual(llm_interaction.presence_penalty, 0.0)
        self.assertEqual(llm_interaction.vendor, "openai")
        
    def test_camelcase_parameter_extraction(self):
        """Test extraction of parameters with camelCase format."""
        # Create a test event
        event = Event(
            id=4,
            agent_id="test-agent",
            timestamp=datetime.now(),
            schema_version="1.0",
            name="llm.call.start",
            level="INFO",
            event_type="llm"
        )
        
        # Create telemetry data with camelCase format (e.g., for Cohere or other vendors)
        telemetry_data = {
            "attributes": {
                "llm.vendor": "cohere",
                "llm.model": "command",
                "llm.request.timestamp": "2025-03-27T19:05:08.253167",
                "llm.request.data": {
                    "message": "Hello",
                    "model": "command",
                    "temperature": 0.8,
                    "maxTokens": 1500,
                    "topP": 0.95,
                    "frequencyPenalty": 0.2,
                    "presencePenalty": 0.1
                }
            }
        }
        
        # Call the from_event_with_telemetry method
        llm_interaction = LLMInteraction.from_event_with_telemetry(
            self.db_session, event, telemetry_data
        )
        
        # Assertions
        self.assertEqual(llm_interaction.temperature, 0.8)
        self.assertEqual(llm_interaction.max_tokens, 1500)
        self.assertEqual(llm_interaction.top_p, 0.95)
        self.assertEqual(llm_interaction.frequency_penalty, 0.2)
        self.assertEqual(llm_interaction.presence_penalty, 0.1)
        self.assertEqual(llm_interaction.vendor, "cohere")
        
    def test_with_raw_event_data(self):
        """Test extraction of parameters using raw event data format."""
        # Create a test event
        event = Event(
            id=5,
            agent_id="test-agent",
            timestamp=datetime.now(),
            schema_version="1.0",
            name="llm.call.start",
            level="INFO",
            event_type="llm"
        )
        
        # Mock the event.data with raw format
        event_data = {
            "payload": {
                "vendor": "anthropic",
                "model": "claude-3-haiku",
                "attributes": {
                    "temperature": 0.7,
                    "max_tokens": 1024,
                    "top_p": 0.9
                }
            }
        }
        event.data = json.dumps(event_data)
        
        # Call the from_event method
        llm_interaction = LLMInteraction.from_event(
            self.db_session, event
        )
        
        # Assertions
        self.assertEqual(llm_interaction.temperature, 0.7)
        self.assertEqual(llm_interaction.max_tokens, 1024)
        self.assertEqual(llm_interaction.top_p, 0.9)
        self.assertEqual(llm_interaction.vendor, "anthropic")

if __name__ == "__main__":
    unittest.main() 