"""
Tests for the conversation API endpoints.

This module contains tests for the LLM Explorer UI endpoints that were added
to the metrics routes.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from src.main import app
from src.models.event import Event
from src.models.llm_interaction import LLMInteraction
from src.models.agent import Agent
from src.models.trace import Trace

client = TestClient(app)

class TestConversationAPI:
    """Tests for the conversation API endpoints."""
    
    @pytest.fixture
    def setup_test_data(self, db_session):
        """Set up test data for conversation API tests."""
        # Create an agent
        agent = Agent(
            agent_id="test-agent-456",
            name="Test API Agent",
            first_seen=datetime.utcnow(),
            last_seen=datetime.utcnow(),
            is_active=True
        )
        db_session.add(agent)
        
        # Create a trace
        trace = Trace(
            trace_id="test-trace-456",
            agent_id="test-agent-456",
            start_timestamp=datetime.utcnow(),
            end_timestamp=datetime.utcnow() + timedelta(minutes=5)
        )
        db_session.add(trace)
        
        # Create events and LLM interactions
        # User message
        event1 = Event(
            name="llm.call.start",
            timestamp=datetime.utcnow(),
            level="info",
            agent_id="test-agent-456",
            trace_id="test-trace-456",
            span_id="test-span-1",
            event_type="llm"
        )
        db_session.add(event1)
        
        llm1 = LLMInteraction(
            event_id=1,  # Will be assigned after flush
            interaction_type="finish",
            vendor="openai",
            model="gpt-4",
            request_timestamp=datetime.utcnow(),
            response_timestamp=datetime.utcnow() + timedelta(seconds=2),
            duration_ms=2000,
            input_tokens=10,
            output_tokens=0,
            total_tokens=10,
            request_data={"role": "user", "content": "What's the weather like?"}
        )
        
        # Assistant response
        event2 = Event(
            name="llm.call.finish",
            timestamp=datetime.utcnow() + timedelta(seconds=2),
            level="info",
            agent_id="test-agent-456",
            trace_id="test-trace-456",
            span_id="test-span-2",
            event_type="llm"
        )
        db_session.add(event2)
        
        llm2 = LLMInteraction(
            event_id=2,  # Will be assigned after flush
            interaction_type="finish",
            vendor="openai",
            model="gpt-4",
            request_timestamp=datetime.utcnow() + timedelta(seconds=2),
            response_timestamp=datetime.utcnow() + timedelta(seconds=4),
            duration_ms=2000,
            input_tokens=0,
            output_tokens=50,
            total_tokens=50,
            request_data={"role": "assistant"},
            response_content="I don't have access to real-time weather information."
        )
        
        # Flush to get IDs assigned
        db_session.flush()
        
        # Set the event IDs for LLM interactions
        llm1.event_id = event1.id
        llm2.event_id = event2.id
        
        db_session.add(llm1)
        db_session.add(llm2)
        
        db_session.commit()
        
        # Return the created objects for use in tests
        return {
            "agent": agent,
            "trace": trace,
            "events": [event1, event2],
            "llm_interactions": [llm1, llm2]
        }
    
    # We'll use dependency_override_provider to mock the DB dependency
    @pytest.fixture
    def mock_db_dependency(self, db_session):
        """Override the DB dependency in the FastAPI app."""
        from src.api.routes.metrics import get_db
        
        original_dependency = app.dependency_overrides.get(get_db)
        app.dependency_overrides[get_db] = lambda: db_session
        
        yield
        
        if original_dependency:
            app.dependency_overrides[get_db] = original_dependency
        else:
            del app.dependency_overrides[get_db]
    
    def test_get_llm_requests(self, mock_db_dependency, setup_test_data):
        """Test GET /metrics/llm/requests endpoint."""
        response = client.get("/metrics/llm/requests")
        
        # Check response
        assert response.status_code == 200
        data = response.json()
        
        # Check structure
        assert "items" in data
        assert "pagination" in data
        assert isinstance(data["items"], list)
        
        # There should be at least our test data
        assert len(data["items"]) >= 2
        
        # Check fields on an item
        item = next(item for item in data["items"] 
                   if item["agent_id"] == "test-agent-456" and item["trace_id"] == "test-trace-456")
        assert "id" in item
        assert "timestamp" in item
        assert "model" in item
        assert "agent_name" in item
        assert item["model"] == "gpt-4"
    
    def test_get_llm_request_details(self, mock_db_dependency, setup_test_data):
        """Test GET /metrics/llm/requests/{request_id} endpoint."""
        # First get a list of requests to find an ID
        response = client.get("/metrics/llm/requests")
        data = response.json()
        
        # Find our test request
        request = next(item for item in data["items"] 
                      if item["agent_id"] == "test-agent-456" and item["trace_id"] == "test-trace-456")
        request_id = request["id"]
        
        # Now get details for this request
        response = client.get(f"/metrics/llm/requests/{request_id}")
        
        # Check response
        assert response.status_code == 200
        detail_data = response.json()
        
        # Check fields
        assert detail_data["id"] == request_id
        assert detail_data["agent_id"] == "test-agent-456"
        assert detail_data["trace_id"] == "test-trace-456"
        assert detail_data["model"] == "gpt-4"
        
        # Test with invalid ID
        response = client.get("/metrics/llm/requests/invalid_id")
        assert response.status_code == 400  # Bad request for invalid format
        
        response = client.get("/metrics/llm/requests/999_999")
        assert response.status_code == 404  # Not found for valid format but non-existent ID
    
    def test_get_llm_conversations(self, mock_db_dependency, setup_test_data):
        """Test GET /metrics/llm/conversations endpoint."""
        response = client.get("/metrics/llm/conversations")
        
        # Check response
        assert response.status_code == 200
        data = response.json()
        
        # Check structure
        assert "items" in data
        assert "pagination" in data
        assert isinstance(data["items"], list)
        
        # There should be at least our test data
        assert len(data["items"]) >= 1
        
        # Check fields on the conversation
        conversation = next(c for c in data["items"] if c["trace_id"] == "test-trace-456")
        assert conversation["agent_id"] == "test-agent-456"
        assert conversation["agent_name"] == "Test API Agent"
        assert conversation["request_count"] >= 2
        assert conversation["total_tokens"] >= 60
        assert "What's the weather like?" in conversation["summary"]
        assert conversation["user_messages"] >= 1
        assert conversation["assistant_messages"] >= 1
        
        # Test filtering
        response = client.get("/metrics/llm/conversations?agent_id=test-agent-456")
        assert response.status_code == 200
        data = response.json()
        assert all(item["agent_id"] == "test-agent-456" for item in data["items"])
    
    def test_get_llm_conversation_detail(self, mock_db_dependency, setup_test_data):
        """Test GET /metrics/llm/conversations/{trace_id} endpoint."""
        response = client.get("/metrics/llm/conversations/test-trace-456")
        
        # Check response
        assert response.status_code == 200
        data = response.json()
        
        # Check structure
        assert "items" in data
        assert "pagination" in data
        assert isinstance(data["items"], list)
        
        # There should be at least 2 messages (user + assistant)
        assert len(data["items"]) >= 2
        
        # Check fields on messages
        user_message = next(m for m in data["items"] if m["role"] == "user")
        assert user_message["content"] == "What's the weather like?"
        assert user_message["trace_id"] == "test-trace-456"
        assert user_message["agent_id"] == "test-agent-456"
        
        assistant_message = next(m for m in data["items"] if m["role"] == "assistant")
        assert "weather information" in assistant_message["content"]
        assert assistant_message["trace_id"] == "test-trace-456"
        assert assistant_message["model"] == "gpt-4"
        
        # Test with invalid trace_id
        response = client.get("/metrics/llm/conversations/non-existent-trace")
        assert response.status_code == 404  # Not found
    
    def test_conversation_api_error_handling(self, mock_db_dependency):
        """Test that the conversation API endpoints handle errors gracefully."""
        # Test with invalid pagination parameters
        response = client.get("/metrics/llm/conversations?page=0")  # Invalid page (must be >= 1)
        assert response.status_code == 422  # Unprocessable entity
        
        # Test with invalid date format
        response = client.get("/metrics/llm/conversations?from_time=invalid-date")
        assert response.status_code == 422  # Unprocessable entity
        
        # Test with valid from_time but missing to_time (both required together)
        response = client.get("/metrics/llm/conversations?from_time=2023-01-01T00:00:00Z")
        assert response.status_code == 422  # Unprocessable entity 