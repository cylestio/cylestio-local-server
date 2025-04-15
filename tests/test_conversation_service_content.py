"""
Tests for the conversation service content extraction and null handling.

This module contains tests for the conversation service focusing on:
- Handling null token counts
- Extracting content from various data structures
- Ensuring content fields are never null
"""
import pytest
from datetime import datetime, timedelta
from sqlalchemy import and_
from unittest.mock import patch, MagicMock, create_autospec
import json

from src.models.event import Event
from src.models.llm_interaction import LLMInteraction
from src.models.agent import Agent
from src.models.trace import Trace
from src.services.conversation_service import ConversationService, get_conversation_service
from src.api.schemas.metrics import ConversationSearchParams

class TestConversationServiceContent:
    """Tests for the content extraction and null handling in ConversationService."""
    
    def test_extract_message_content(self):
        """Test the message content extraction from various data structures."""
        service = ConversationService(None)  # No DB needed for this test
        
        # Test string content
        assert service._extract_message_content("Hello") == "Hello"
        
        # Test dict with content key
        assert service._extract_message_content({"content": "Hello"}) == "Hello"
        
        # Test dict with messages array
        messages_data = {
            "messages": [
                {"role": "system", "content": "You are a helpful assistant"},
                {"role": "user", "content": "Hello"}
            ]
        }
        assert service._extract_message_content(messages_data) == "Hello"
        
        # Test empty data
        assert service._extract_message_content(None) == ""
        assert service._extract_message_content({}) == ""
        
        # Test OpenAI response format
        openai_response = {
            "choices": [
                {
                    "message": {
                        "content": "Hello back!"
                    }
                }
            ]
        }
        assert service._extract_message_content(openai_response) == "Hello back!"
        
        # Test messages as string representation
        string_messages = {
            "messages": "[{'role': 'user', 'content': 'Help me'}]"
        }
        assert "Help me" in service._extract_message_content(string_messages)
    
    def test_estimate_token_count(self):
        """Test token count estimation based on content length."""
        service = ConversationService(None)  # No DB needed for this test
        
        # Test empty content
        assert service._estimate_token_count("") == 0
        assert service._estimate_token_count(None) == 0
        
        # Test very short content (should have minimum token count)
        assert service._estimate_token_count("Hi") == 5
        
        # Test normal content (~4 chars per token)
        text = "This is a normal length sentence that should be around 15 tokens."
        assert service._estimate_token_count(text) == len(text) // 4
        
        # Test long content
        long_text = "a" * 1000
        assert service._estimate_token_count(long_text) == 250  # 1000 / 4
    
    def test_conversation_messages_null_handling(self):
        """Test that conversation messages never have null values for duration or tokens."""
        # Create a mock DB session
        mock_session = MagicMock()
        service = ConversationService(mock_session)
        
        # Create mock query results with null values
        mock_row_request = MagicMock()
        mock_row_request.event_id = 1
        mock_row_request.interaction_id = 1
        mock_row_request.timestamp = datetime.utcnow()
        mock_row_request.trace_id = "test-trace"
        mock_row_request.span_id = "test-span"
        mock_row_request.model = "gpt-4"
        mock_row_request.interaction_type = "start"
        mock_row_request.agent_id = "test-agent"
        mock_row_request.agent_name = "Test Agent"
        mock_row_request.request_data = {"content": "Hello"}
        mock_row_request.duration_ms = None  # Null duration
        mock_row_request.input_tokens = None  # Null input tokens
        mock_row_request.output_tokens = None
        mock_row_request.total_tokens = None
        
        mock_row_response = MagicMock()
        mock_row_response.event_id = 2
        mock_row_response.interaction_id = 2
        mock_row_response.timestamp = datetime.utcnow()
        mock_row_response.trace_id = "test-trace"
        mock_row_response.span_id = "test-span"
        mock_row_response.model = "gpt-4"
        mock_row_response.interaction_type = "finish"
        mock_row_response.agent_id = "test-agent"
        mock_row_response.agent_name = "Test Agent"
        mock_row_response.response_content = "I'm fine, thanks"
        mock_row_response.duration_ms = 1000
        mock_row_response.input_tokens = 3
        mock_row_response.output_tokens = None  # Null output tokens
        mock_row_response.total_tokens = 10  # Total tokens available
        mock_row_response.stop_reason = "end_turn"
        
        # Mock the query to return our mock results
        mock_query = MagicMock()
        mock_query.all.return_value = [mock_row_request, mock_row_response]
        mock_session.query.return_value.join.return_value.join.return_value.filter.return_value.order_by.return_value = mock_query
        
        # Call the method
        messages, _ = service.get_conversation_messages("test-trace")
        
        # Verify no null values for duration or tokens
        for message in messages:
            assert message.duration_ms is not None
            assert message.input_tokens is not None
            assert message.output_tokens is not None
            assert message.content is not None
            
        # Verify request message has tokens from response
        request_message = next(m for m in messages if m.message_type == "request")
        assert request_message.input_tokens == 3  # Should use input_tokens from response
        assert request_message.duration_ms == 0  # Default for null
        
        # Verify response message calculated output tokens correctly
        response_message = next(m for m in messages if m.message_type == "response")
        assert response_message.output_tokens == 7  # Should be total_tokens - input_tokens = 10 - 3 = 7
    
    def test_llm_requests_content_extraction(self):
        """Test that LLM requests never have null content fields."""
        # Create a mock DB session
        mock_session = MagicMock()
        service = ConversationService(mock_session)
        
        # Create a mock query result with null content
        mock_row = MagicMock()
        mock_row.event_id = 1
        mock_row.interaction_id = 1
        mock_row.timestamp = datetime.utcnow()
        mock_row.trace_id = "test-trace"
        mock_row.span_id = "test-span"
        mock_row.model = "gpt-4"
        mock_row.agent_id = "test-agent"
        mock_row.agent_name = "Test Agent"
        mock_row.request_data = None  # Null request data
        mock_row.response_content = None  # Null response content
        mock_row.duration_ms = None  # Null duration
        mock_row.input_tokens = None  # Null tokens
        mock_row.output_tokens = None
        mock_row.total_tokens = 100  # Total tokens available
        mock_row.stop_reason = None
        mock_row.related_interaction_id = None
        mock_row.interaction_type = "finish"
        
        # Mock the query to return our mock result
        mock_query = MagicMock()
        mock_query.all.return_value = [mock_row]
        mock_count = MagicMock()
        mock_count.return_value = 1
        mock_query.count = mock_count
        mock_session.query.return_value.join.return_value.join.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value = mock_query
        mock_session.query.return_value.join.return_value.join.return_value.filter.return_value.count = mock_count
        
        # Call the method
        requests, _ = service.get_llm_requests()
        
        # Verify no null values for content, duration, or tokens
        for request in requests:
            assert request.duration_ms is not None
            assert request.input_tokens is not None
            assert request.output_tokens is not None
            assert request.content is not None
            assert request.response is not None
            
        # Verify default values were used
        assert requests[0].duration_ms == 0  # Default for null
        assert requests[0].input_tokens >= 0  # Should at least be 0, not null
        assert requests[0].output_tokens >= 0  # Should at least be 0, not null
        assert requests[0].content == "<Request data not available>"
        assert requests[0].response == "<Response data not available>"
    
    def test_get_llm_requests_with_related_interaction(self):
        """Test that LLM requests use related interactions for content when available."""
        # Create a mock DB session
        mock_session = MagicMock()
        service = ConversationService(mock_session)
        
        # Create a mock finish interaction with empty request data
        mock_row = MagicMock()
        mock_row.event_id = 1
        mock_row.interaction_id = 2
        mock_row.timestamp = datetime.utcnow()
        mock_row.trace_id = "test-trace"
        mock_row.span_id = "test-span"
        mock_row.model = "gpt-4"
        mock_row.agent_id = "test-agent"
        mock_row.agent_name = "Test Agent"
        mock_row.request_data = {}  # Empty request data
        mock_row.response_content = "I can help with that"
        mock_row.duration_ms = 1000
        mock_row.input_tokens = 5
        mock_row.output_tokens = 5
        mock_row.total_tokens = 10
        mock_row.stop_reason = "end_turn"
        mock_row.related_interaction_id = 1  # References a start interaction
        mock_row.interaction_type = "finish"
        
        # Create a mock for the related start interaction query
        mock_start_row = MagicMock()
        mock_start_row.request_data = {"content": "Hello from start"}
        
        # Set up the session to return the mock_start_row when querying for related interaction
        mock_start_query = MagicMock()
        mock_start_query.first.return_value = mock_start_row
        mock_session.query.return_value.filter.return_value = mock_start_query
        
        # Set up the main query to return mock_row
        mock_query = MagicMock()
        mock_query.all.return_value = [mock_row]
        mock_count = MagicMock()
        mock_count.return_value = 1
        mock_query.count = mock_count
        
        # Configure the chain of query calls
        mock_session.query.return_value.join.return_value.join.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value = mock_query
        mock_session.query.return_value.join.return_value.join.return_value.filter.return_value.count = mock_count
        
        # Call the method
        requests, _ = service.get_llm_requests()
        
        # Verify that content from the related start interaction was used
        assert requests[0].content == "Hello from start"
        assert requests[0].response == "I can help with that"
        
    def test_get_request_details_with_content_extraction(self):
        """Test that request details correctly extract and populate content fields."""
        # Create a mock DB session
        mock_session = MagicMock()
        service = ConversationService(mock_session)
        
        # Create a mock row with complex data structures
        mock_row = MagicMock()
        mock_row.event_id = 1
        mock_row.interaction_id = 1
        mock_row.timestamp = datetime.utcnow()
        mock_row.trace_id = "test-trace"
        mock_row.span_id = "test-span"
        mock_row.model = "gpt-4"
        mock_row.agent_id = "test-agent"
        mock_row.agent_name = "Test Agent"
        # Complex nested request data
        mock_row.request_data = {
            "messages": [
                {"role": "system", "content": "You are a helpful assistant"},
                {"role": "user", "content": "Tell me about token handling"}
            ]
        }
        # OpenAI-style response
        mock_row.response_content = {
            "choices": [
                {
                    "message": {
                        "content": "Token handling is important for LLM applications..."
                    }
                }
            ]
        }
        mock_row.duration_ms = 1500
        mock_row.input_tokens = 20
        mock_row.output_tokens = 50
        mock_row.total_tokens = 70
        mock_row.stop_reason = "end_turn"
        mock_row.related_interaction_id = None
        mock_row.interaction_type = "finish"
        
        # Set up the session to return the mock_row
        mock_query = MagicMock()
        mock_query.first.return_value = mock_row
        mock_session.query.return_value.join.return_value.join.return_value.filter.return_value = mock_query
        
        # Call the method
        result = service.get_request_details("1_1")
        
        # Verify content extraction worked correctly
        assert result is not None
        # The content should contain both messages from the messages array
        assert "You are a helpful assistant" in result.content
        assert "Tell me about token handling" in result.content
        assert result.response == "Token handling is important for LLM applications..."  # Should extract from choices
        assert result.input_tokens == 20
        assert result.output_tokens == 50 