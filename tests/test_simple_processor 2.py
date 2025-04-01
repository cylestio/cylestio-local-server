"""
Tests for the SimpleProcessor class.
"""
import json
import datetime
import pytest
from unittest.mock import MagicMock, patch

import sqlalchemy
from sqlalchemy import text
from src.processing.simple_processor import SimpleProcessor, ProcessingError
from src.models.event import Event
from src.models.llm_interaction import LLMInteraction
from src.models.security_alert import SecurityAlert
from src.models.framework_event import FrameworkEvent
from tests.utils.mock_utils import NumericMock, create_mock_llm_interaction


class TestSimpleProcessor:
    """Tests for the SimpleProcessor class."""
    
    @pytest.fixture
    def db_session_factory(self):
        """Create a mock session factory with isolated session for each test."""
        session = MagicMock()
        # Ensure session's query doesn't retain state between tests
        session.query.return_value.filter_by.return_value.first.return_value = None
        factory = MagicMock(return_value=session)
        return factory
    
    @pytest.fixture
    def processor(self, db_session_factory):
        """Create a SimpleProcessor instance with a mock session factory."""
        processor = SimpleProcessor(db_session_factory)
        return processor
    
    @pytest.fixture
    def sample_event_data(self):
        """Sample event data for testing."""
        return {
            "timestamp": "2023-09-01T12:34:56Z",
            "name": "test.event",
            "level": "INFO",
            "agent_id": "test-agent-id",
            "trace_id": "test-trace-id",
            "span_id": "test-span-id",
            "schema_version": "1.0",
            "attributes": {
                "test_key": "test_value",
                "number_key": 123,
                "bool_key": True
            }
        }
    
    @pytest.fixture
    def sample_llm_event_data(self):
        """Sample LLM event data for testing."""
        return {
            "timestamp": "2023-09-01T12:34:56Z",
            "name": "llm.completion",
            "level": "INFO",
            "agent_id": "test-agent-id",
            "trace_id": "test-trace-id",
            "span_id": "test-span-id",
            "schema_version": "1.0",
            "model": "gpt-4",
            "prompt": "Test prompt",
            "completion": "Test completion",
            "attributes": {
                "tokens": 123,
                "prompt_tokens": 10,
                "completion_tokens": 113
            }
        }
    
    def test_validate_event_valid(self, processor, sample_event_data):
        """Test validating a valid event."""
        # Create a deep copy of the data to prevent test cross-contamination
        import copy
        event_data = copy.deepcopy(sample_event_data)
        result = processor._validate_event(event_data)
        assert result["valid"] is True
    
    def test_validate_event_missing_required_field(self, processor, sample_event_data):
        """Test validating an event with a missing required field."""
        # Create a deep copy of the data to prevent test cross-contamination
        import copy
        event_data = copy.deepcopy(sample_event_data)
        del event_data["name"]
        result = processor._validate_event(event_data)
        assert result["valid"] is False
        assert "Missing required field: name" in result["error"]
    
    def test_validate_event_invalid_schema_version(self, processor, sample_event_data):
        """Test validating an event with an invalid schema version."""
        # Create a deep copy of the data to prevent test cross-contamination
        import copy
        event_data = copy.deepcopy(sample_event_data)
        event_data["schema_version"] = "2.0"
        result = processor._validate_event(event_data)
        assert result["valid"] is False
        assert "Unsupported schema version: 2.0" in result["error"]
    
    def test_validate_event_invalid_type(self, processor, sample_event_data):
        """Test validating an event with invalid field type."""
        # Create a deep copy of the data to prevent test cross-contamination
        import copy
        event_data = copy.deepcopy(sample_event_data)
        event_data["timestamp"] = 123  # Should be a string
        result = processor._validate_event(event_data)
        assert result["valid"] is False
        assert "Field timestamp must be a string" in result["error"]
    
    def test_transform_event_generic(self, processor, sample_event_data, db_session_factory):
        """Test transforming a generic event."""
        # Create a deep copy of the data to prevent test cross-contamination
        import copy
        event_data = copy.deepcopy(sample_event_data)
        
        session = db_session_factory()
        
        # Mock Span.get_or_create to return a mock span
        mock_span = MagicMock()
        mock_span.span_id = event_data["span_id"]
        
        # Use patch context to isolate external dependencies
        with patch('src.models.span.Span.get_or_create', return_value=mock_span):
            event, related_models = processor._transform_event(event_data, session)
            
            assert isinstance(event, Event)
            assert event.name == event_data["name"]
            assert event.timestamp.isoformat().replace('+00:00', 'Z') == event_data["timestamp"]
            assert event.level == event_data["level"]
            assert event.agent_id == event_data["agent_id"]
            assert event.trace_id == event_data["trace_id"]
            assert event.span_id == event_data["span_id"]
            assert event.schema_version == event_data["schema_version"]
            assert event.event_type == "generic"
            
            # Check that agent is in related models
            assert any(hasattr(model, 'agent_id') and model.agent_id == event_data["agent_id"] for model in related_models)
            
            # Check that trace is in related models
            assert any(hasattr(model, 'trace_id') and model.trace_id == event_data["trace_id"] for model in related_models)
            
            # Check that span is in related models
            assert any(hasattr(model, 'span_id') and model.span_id == event_data["span_id"] for model in related_models)
    
    def test_transform_event_llm(self, processor, sample_llm_event_data, db_session_factory):
        """Test transforming an LLM event."""
        session = db_session_factory()
        
        # Mock Span.get_or_create to return a mock span
        mock_span = MagicMock()
        mock_span.span_id = sample_llm_event_data["span_id"]
        
        # Mock LLMInteraction.from_event to return a mock object with proper numeric fields
        with patch('src.models.llm_interaction.LLMInteraction.from_event') as mock_from_event, \
             patch('src.models.span.Span.get_or_create', return_value=mock_span):
            
            # Set up the mock LLM interaction with numeric properties
            input_tokens = 10
            output_tokens = 113
            total_tokens = 123
            duration_ms = 100
            
            mock_llm_interaction = MagicMock()
            mock_llm_interaction.input_tokens = input_tokens
            mock_llm_interaction.output_tokens = output_tokens
            mock_llm_interaction.total_tokens = total_tokens
            mock_llm_interaction.duration_ms = duration_ms
            
            mock_from_event.return_value = mock_llm_interaction
            
            event, related_models = processor._transform_event(sample_llm_event_data, session)
            
            assert isinstance(event, Event)
            assert event.name == sample_llm_event_data["name"]
            assert event.event_type == "llm"
            
            # Check that LLMInteraction.from_event was called
            mock_from_event.assert_called_once()
            
            # Check that the LLM interaction is in related models
            assert mock_llm_interaction in related_models
            
            # Test numeric comparisons
            assert mock_llm_interaction.input_tokens == input_tokens
            assert mock_llm_interaction.output_tokens == output_tokens
            assert mock_llm_interaction.total_tokens == total_tokens
            assert mock_llm_interaction.duration_ms == duration_ms
    
    def test_process_json_event(self, processor, sample_event_data):
        """Test processing an event from JSON."""
        # Mock process_event to return a success result
        with patch.object(processor, 'process_event') as mock_process_event:
            mock_process_event.return_value = {"success": True, "event_id": "test-id", "event_name": "test.event"}
            
            json_data = json.dumps(sample_event_data)
            result = processor.process_json_event(json_data)
            
            assert result["success"] is True
            assert result["event_id"] == "test-id"
            assert result["event_name"] == "test.event"
            
            # Check that process_event was called with the right data
            mock_process_event.assert_called_once_with(sample_event_data)
    
    def test_process_json_event_invalid_json(self, processor):
        """Test processing invalid JSON."""
        json_data = "invalid json"
        result = processor.process_json_event(json_data)
        
        assert result["success"] is False
        assert "Invalid JSON" in result["error"]
    
    def test_process_batch(self, processor, sample_event_data):
        """Test processing a batch of events."""
        # Create mock models
        mock_agent = MagicMock()
        mock_agent.agent_id = sample_event_data["agent_id"]
        
        mock_event = MagicMock()
        mock_event.id = 123
        mock_event.name = sample_event_data["name"]
        
        # Create a mock db session
        mock_session = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = mock_agent
        
        # Configure the processor to use our mock session
        processor.db_session_factory = lambda: iter([mock_session])
        
        # Mock _transform_event to return our mock event
        with patch.object(processor, '_transform_event') as mock_transform:
            mock_transform.return_value = (mock_event, [mock_agent])
            
            batch = [sample_event_data, sample_event_data]
            result = processor.process_batch(batch)
            
            # Check that the batch processing was successful
            assert result["total"] == 2
            assert result["successful"] == 2
            assert result["failed"] == 0
            assert len(result["results"]) == 2
            
            # Check each result in the batch
            for batch_result in result["results"]:
                assert batch_result["success"] is True
                assert batch_result["event_name"] == "test.event"
            
            # Check that _transform_event was called twice
            assert mock_transform.call_count == 2
            
            # Verify session was committed and closed
            mock_session.commit.assert_called_once()
            mock_session.close.assert_called_once()
    
    def test_process_json_batch(self, processor, sample_event_data):
        """Test processing a batch of events from JSON."""
        # Mock process_batch to return success
        with patch.object(processor, 'process_batch') as mock_process_batch:
            mock_process_batch.return_value = {
                "total": 2,
                "successful": 2,
                "failed": 0,
                "results": [
                    {"success": True, "event_id": "test-id-1", "event_name": "test.event"},
                    {"success": True, "event_id": "test-id-2", "event_name": "test.event"}
                ]
            }
            
            json_data = json.dumps([sample_event_data, sample_event_data])
            result = processor.process_json_batch(json_data)
            
            assert result["total"] == 2
            assert result["successful"] == 2
            assert result["failed"] == 0
            assert len(result["results"]) == 2
            
            # Check that process_batch was called with the right data
            mock_process_batch.assert_called_once()
    
    def test_process_json_batch_invalid_json(self, processor):
        """Test processing invalid JSON for a batch."""
        json_data = "invalid json"
        result = processor.process_json_batch(json_data)
        
        assert result["success"] is False
        assert "Invalid JSON" in result["error"]
    
    def test_process_json_batch_not_array(self, processor, sample_event_data):
        """Test processing non-array JSON for a batch."""
        json_data = json.dumps(sample_event_data)  # Single object, not an array
        result = processor.process_json_batch(json_data)
        
        assert result["success"] is False
        assert "JSON must contain an array of events" in result["error"]
    
    def test_process_event_integration(self, processor, sample_event_data):
        """Integration test for processing an event."""
        # Create mock models
        mock_agent = MagicMock()
        mock_agent.agent_id = sample_event_data["agent_id"]
        
        mock_event = MagicMock()
        mock_event.id = 123
        mock_event.name = sample_event_data["name"]
        
        # Create a mock db session
        mock_session = MagicMock()
        
        # Configure the processor to use our mock session
        processor.db_session_factory = lambda: iter([mock_session])
        
        # Mock _transform_event to return our mock event
        with patch.object(processor, '_transform_event') as mock_transform:
            mock_transform.return_value = (mock_event, [mock_agent])
            
            result = processor.process_event(sample_event_data)
            
            assert result["success"] is True
            assert result["event_id"] == mock_event.id
            assert result["event_name"] == mock_event.name
            
            # Check that _transform_event was called with correct arguments
            mock_transform.assert_called_once()
            
            # Verify session calls
            mock_session.add.assert_called()
            mock_session.commit.assert_called_once()
            mock_session.close.assert_called_once()
    
    def test_process_event_integration_exception(self, processor, sample_event_data):
        """Integration test for processing an event with an exception."""
        # Create a mock db session that raises an exception on commit
        mock_session = MagicMock()
        mock_session.commit.side_effect = Exception("Test exception")
        
        # Configure the processor to use our mock session
        processor.db_session_factory = lambda: iter([mock_session])
        
        # Create mock event and models
        mock_event = MagicMock()
        mock_event.name = sample_event_data["name"]
        
        # Mock _transform_event to return our mock event
        with patch.object(processor, '_transform_event') as mock_transform:
            mock_transform.return_value = (mock_event, [])
            
            result = processor.process_event(sample_event_data)
            
            assert result["success"] is False
            assert "error" in result
            assert "Test exception" in result["error"]
            
            # Check that rollback was called
            mock_session.rollback.assert_called_once()
            mock_session.close.assert_called_once()
    
    # Add a cleanup method to reset any class-level state if present
    @pytest.fixture(autouse=True)
    def reset_processor_state(self):
        """Reset any processor state before and after each test."""
        # Yield to allow the test to run
        yield
        # Any cleanup code if needed 