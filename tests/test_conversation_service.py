"""
Tests for the conversation service.

This module contains tests for the conversation service that powers the LLM Explorer UI.
"""
import pytest
from datetime import datetime, timedelta
from sqlalchemy import and_
from unittest.mock import patch, MagicMock

from src.models.event import Event
from src.models.llm_interaction import LLMInteraction
from src.models.agent import Agent
from src.models.trace import Trace
from src.services.conversation_service import ConversationService, get_conversation_service
from src.api.schemas.metrics import ConversationSearchParams

class TestConversationService:
    """Tests for the ConversationService class."""
    
    @pytest.fixture
    def setup_test_data(self, db_session):
        """Set up test data for conversation service tests."""
        # Create an agent
        agent = Agent(
            agent_id="test-agent-123",
            name="Test Agent",
            first_seen=datetime.utcnow(),
            last_seen=datetime.utcnow(),
            is_active=True
        )
        db_session.add(agent)
        
        # Create a trace
        trace = Trace(
            trace_id="test-trace-123",
            agent_id="test-agent-123",
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
            agent_id="test-agent-123",
            trace_id="test-trace-123",
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
            request_data={"role": "user", "content": "Hello, how are you?"}
        )
        
        # Assistant response
        event2 = Event(
            name="llm.call.finish",
            timestamp=datetime.utcnow() + timedelta(seconds=2),
            level="info",
            agent_id="test-agent-123",
            trace_id="test-trace-123",
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
            response_content="I'm doing well, thank you for asking. How can I help you today?"
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
    
    def test_get_conversation_service(self, db_session):
        """Test that get_conversation_service returns a ConversationService instance."""
        service = get_conversation_service(db_session)
        assert isinstance(service, ConversationService)
        assert service.db_session == db_session
    
    def test_get_conversations(self, db_session, setup_test_data):
        """Test retrieving a list of conversations."""
        service = ConversationService(db_session)
        
        # Create search parameters
        search_params = ConversationSearchParams(
            page=1,
            page_size=10
        )
        
        # Get conversations
        conversations, pagination = service.get_conversations(search_params)
        
        # Verify results
        assert len(conversations) >= 1
        assert pagination["total"] >= 1
        assert pagination["page"] == 1
        assert pagination["page_size"] == 10
        
        # Check fields on the first conversation
        conversation = next(c for c in conversations if c.trace_id == "test-trace-123")
        assert conversation.agent_id == "test-agent-123"
        assert conversation.agent_name == "Test Agent"
        assert conversation.request_count >= 2
        assert conversation.total_tokens >= 60
        assert conversation.summary == "Hello, how are you?"
        assert conversation.user_messages >= 1
        assert conversation.assistant_messages >= 1
    
    def test_get_conversation_messages(self, db_session, setup_test_data):
        """Test retrieving messages for a specific conversation."""
        service = ConversationService(db_session)
        
        # Get messages for the test trace
        messages, pagination = service.get_conversation_messages("test-trace-123")
        
        # Verify results
        assert len(messages) >= 2
        assert pagination["total"] >= 2
        assert pagination["page"] == 1
        
        # Find the user message
        user_message = next(m for m in messages if m.role == "user")
        assert user_message.content == "Hello, how are you?"
        assert user_message.trace_id == "test-trace-123"
        assert user_message.agent_id == "test-agent-123"
        
        # Find the assistant message
        assistant_message = next(m for m in messages if m.role == "assistant")
        assert "I'm doing well" in assistant_message.content
        assert assistant_message.trace_id == "test-trace-123"
        assert assistant_message.model == "gpt-4"
    
    def test_get_llm_requests(self, db_session, setup_test_data):
        """Test retrieving LLM requests with agent information."""
        service = ConversationService(db_session)
        
        # Get LLM requests
        requests, pagination = service.get_llm_requests()
        
        # Verify results
        assert len(requests) >= 2
        assert pagination["total"] >= 2
        assert pagination["page"] == 1
        
        # Check fields on a request
        request = requests[0]  # Most recent request should be first due to desc ordering
        assert request.agent_id == "test-agent-123"
        assert request.agent_name == "Test Agent"
        assert request.model == "gpt-4"
        assert request.trace_id == "test-trace-123"
    
    def test_get_request_details(self, db_session, setup_test_data):
        """Test retrieving details for a specific LLM request."""
        service = ConversationService(db_session)
        
        # Get all requests first to find a valid ID
        requests, _ = service.get_llm_requests()
        request_id = requests[0].id
        
        # Get details for this request
        details = service.get_request_details(request_id)
        
        # Verify results
        assert details is not None
        assert details.id == request_id
        assert details.agent_id == "test-agent-123"
        assert details.agent_name == "Test Agent"
        assert details.model == "gpt-4"
        assert details.trace_id == "test-trace-123"
        
        # Content should be extracted
        assert details.content is not None or details.response is not None
    
    def test_apply_conversation_filters(self, db_session, setup_test_data):
        """Test applying filters to conversation queries."""
        service = ConversationService(db_session)
        
        # Create a base query
        from sqlalchemy import func, distinct
        base_query = (
            db_session.query(
                Event.trace_id,
                func.min(Event.timestamp).label('first_timestamp'),
                func.max(Event.timestamp).label('last_timestamp'),
                Event.agent_id,
                Agent.name.label('agent_name'),
                func.count(distinct(Event.id)).label('event_count')
            )
            .join(LLMInteraction, Event.id == LLMInteraction.event_id)
            .join(Agent, Event.agent_id == Agent.agent_id)
            .filter(Event.trace_id.isnot(None))
            .group_by(Event.trace_id, Event.agent_id, Agent.name)
        )
        
        # Test agent_id filter
        search_params = ConversationSearchParams(
            agent_id="test-agent-123"
        )
        filtered_query = service._apply_conversation_filters(base_query, search_params)
        results = filtered_query.all()
        assert len(results) >= 1
        assert all(r.agent_id == "test-agent-123" for r in results)
        
        # Test time range filter
        now = datetime.utcnow()
        search_params = ConversationSearchParams(
            from_time=now - timedelta(hours=1),
            to_time=now + timedelta(hours=1)
        )
        filtered_query = service._apply_conversation_filters(base_query, search_params)
        results = filtered_query.all()
        assert len(results) >= 1
    
    def test_get_conversation_summary(self, db_session, setup_test_data):
        """Test extracting a summary from conversation messages."""
        service = ConversationService(db_session)
        
        # Get summary for the test trace
        summary = service._get_conversation_summary("test-trace-123")
        
        # Verify it found the user's first message
        assert summary == "Hello, how are you?"
        
        # Test handling a non-existent trace
        summary = service._get_conversation_summary("non-existent-trace")
        assert summary == "No summary available" 