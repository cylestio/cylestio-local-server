"""
End-to-end tests for the Cylestio Local Server.

These tests validate the complete event processing system using realistic
event sequences and complex workflows.
"""
import json
import datetime
import uuid
import pytest
import time
import os
from pathlib import Path
from sqlalchemy import create_engine, func
from sqlalchemy.orm import Session

from models.base import Base
from models.agent import Agent
from models.event import Event
from models.llm_interaction import LLMInteraction
from models.security_alert import SecurityAlert
from models.framework_event import FrameworkEvent
from models.tool_interaction import ToolInteraction
from models.session import Session as SessionModel
from models.span import Span
from models.trace import Trace

from processing.simple_processor import SimpleProcessor


class TestRealisticEventSequences:
    """Test realistic event sequences through the entire processing pipeline."""
    
    @pytest.fixture(scope="function")
    def setup_e2e_test(self, temp_db_path):
        """Set up an end-to-end test environment with a temporary database."""
        # Create a temporary database
        db_url = f"sqlite:///{temp_db_path}"
        engine = create_engine(db_url, echo=False)
        
        # Create all tables
        Base.metadata.create_all(engine)
        
        # Create a session factory
        def session_factory():
            session = Session(bind=engine)
            try:
                yield session
            finally:
                session.close()
        
        # Create a processor
        processor = SimpleProcessor(session_factory)
        
        # Return test fixtures
        return engine, session_factory, processor
    
    def test_conversation_flow(self, setup_e2e_test):
        """
        Test a realistic conversation flow with multiple components:
        1. Session start
        2. LLM interaction (user asks a question)
        3. LLM responds
        4. Tool execution (triggered by LLM)
        5. Tool result
        6. LLM uses tool result for final response
        7. Session end
        """
        engine, session_factory, processor = setup_e2e_test
        session = next(session_factory())
        
        # Create test agent
        agent_id = "e2e-test-agent"
        agent = Agent(
            agent_id=agent_id,
            name="E2E Test Agent",
            first_seen=datetime.datetime.utcnow(),
            last_seen=datetime.datetime.utcnow(),
            is_active=True
        )
        session.add(agent)
        session.commit()
        agent_db_id = agent.id
        
        # Create test data - unique IDs for tracing
        session_id = str(uuid.uuid4())
        trace_id = str(uuid.uuid4())
        conversation_span_id = str(uuid.uuid4())
        first_llm_span_id = str(uuid.uuid4())
        tool_span_id = str(uuid.uuid4())
        second_llm_span_id = str(uuid.uuid4())
        base_time = datetime.datetime.utcnow()
        
        # 1. Create and process session start event
        session_start_event = {
            "name": "session.start",
            "timestamp": base_time.isoformat() + "Z",
            "agent_id": agent_id,
            "trace_id": trace_id,
            "event_type": "session",
            "level": "INFO",
            "schema_version": "1.0",
            "attributes": {
                "session.id": session_id,
                "session.name": "Test Conversation",
                "session.start_time": base_time.isoformat() + "Z"
            }
        }
        result1 = processor.process_event(session_start_event)
        assert result1["success"] is True
        
        # 2. Create and process conversation span start
        conversation_span_event = {
            "name": "span.start",
            "timestamp": (base_time + datetime.timedelta(milliseconds=10)).isoformat() + "Z",
            "agent_id": agent_id,
            "trace_id": trace_id,
            "event_type": "span",
            "level": "INFO",
            "schema_version": "1.0",
            "attributes": {
                "span.id": conversation_span_id,
                "span.name": "conversation",
                "span.start_time": (base_time + datetime.timedelta(milliseconds=10)).isoformat() + "Z",
                "session.id": session_id
            }
        }
        result2 = processor.process_event(conversation_span_event)
        assert result2["success"] is True
        
        # 3. Create and process first LLM span start (nested in conversation)
        first_llm_span_event = {
            "name": "span.start",
            "timestamp": (base_time + datetime.timedelta(milliseconds=20)).isoformat() + "Z",
            "agent_id": agent_id,
            "trace_id": trace_id,
            "event_type": "span",
            "level": "INFO",
            "schema_version": "1.0",
            "attributes": {
                "span.id": first_llm_span_id,
                "span.name": "llm_call_1",
                "span.start_time": (base_time + datetime.timedelta(milliseconds=20)).isoformat() + "Z",
                "span.parent_id": conversation_span_id,
                "session.id": session_id
            }
        }
        result3 = processor.process_event(first_llm_span_event)
        assert result3["success"] is True
        
        # 4. Create and process first LLM call start
        first_llm_start_event = {
            "name": "llm.call.start",
            "timestamp": (base_time + datetime.timedelta(milliseconds=30)).isoformat() + "Z",
            "agent_id": agent_id,
            "trace_id": trace_id,
            "event_type": "llm",
            "level": "INFO",
            "schema_version": "1.0",
            "span_id": first_llm_span_id,
            "attributes": {
                "llm.vendor": "anthropic",
                "llm.model": "claude-3-haiku-20240307",
                "llm.request.timestamp": (base_time + datetime.timedelta(milliseconds=30)).isoformat() + "Z",
                "llm.request.data": {
                    "messages": [
                        {"role": "user", "content": "What's the weather in San Francisco?"}
                    ]
                },
                "llm.config.temperature": 0.7,
                "llm.config.max_tokens": 1000,
                "session.id": session_id
            }
        }
        result4 = processor.process_event(first_llm_start_event)
        assert result4["success"] is True
        
        # 5. Create and process first LLM call finish
        first_llm_finish_event = {
            "name": "llm.call.finish",
            "timestamp": (base_time + datetime.timedelta(milliseconds=230)).isoformat() + "Z",
            "agent_id": agent_id,
            "trace_id": trace_id,
            "event_type": "llm",
            "level": "INFO",
            "schema_version": "1.0",
            "span_id": first_llm_span_id,
            "attributes": {
                "llm.vendor": "anthropic",
                "llm.model": "claude-3-haiku-20240307",
                "llm.request.timestamp": (base_time + datetime.timedelta(milliseconds=30)).isoformat() + "Z",
                "llm.response.timestamp": (base_time + datetime.timedelta(milliseconds=230)).isoformat() + "Z",
                "llm.response.duration_ms": 200,
                "llm.usage.input_tokens": 12,
                "llm.usage.output_tokens": 48,
                "llm.usage.total_tokens": 60,
                "llm.response.content": {
                    "type": "text", 
                    "text": "I need to check the current weather in San Francisco. Let me use a tool to look that up for you."
                },
                "llm.response.id": f"resp_{uuid.uuid4()}",
                "llm.response.stop_reason": "end_turn",
                "session.id": session_id
            }
        }
        result5 = processor.process_event(first_llm_finish_event)
        assert result5["success"] is True
        
        # 6. Create and process first LLM span end
        first_llm_span_end_event = {
            "name": "span.end",
            "timestamp": (base_time + datetime.timedelta(milliseconds=240)).isoformat() + "Z",
            "agent_id": agent_id,
            "trace_id": trace_id,
            "event_type": "span",
            "level": "INFO",
            "schema_version": "1.0",
            "attributes": {
                "span.id": first_llm_span_id,
                "span.end_time": (base_time + datetime.timedelta(milliseconds=240)).isoformat() + "Z",
                "session.id": session_id
            }
        }
        result6 = processor.process_event(first_llm_span_end_event)
        assert result6["success"] is True
        
        # 7. Create and process tool span start
        tool_span_event = {
            "name": "span.start",
            "timestamp": (base_time + datetime.timedelta(milliseconds=250)).isoformat() + "Z",
            "agent_id": agent_id,
            "trace_id": trace_id,
            "event_type": "span",
            "level": "INFO",
            "schema_version": "1.0",
            "attributes": {
                "span.id": tool_span_id,
                "span.name": "tool_execution",
                "span.start_time": (base_time + datetime.timedelta(milliseconds=250)).isoformat() + "Z",
                "span.parent_id": conversation_span_id,
                "session.id": session_id
            }
        }
        result7 = processor.process_event(tool_span_event)
        assert result7["success"] is True
        
        # 8. Create and process tool execution start
        tool_start_event = {
            "name": "tool.execution.start",
            "timestamp": (base_time + datetime.timedelta(milliseconds=260)).isoformat() + "Z",
            "agent_id": agent_id,
            "trace_id": trace_id,
            "event_type": "tool",
            "level": "INFO",
            "schema_version": "1.0",
            "span_id": tool_span_id,
            "attributes": {
                "tool.name": "weather_api",
                "tool.description": "Get current weather for a location",
                "tool.timestamp": (base_time + datetime.timedelta(milliseconds=260)).isoformat() + "Z",
                "tool.input": {"location": "San Francisco, CA"},
                "session.id": session_id
            }
        }
        result8 = processor.process_event(tool_start_event)
        assert result8["success"] is True
        
        # 9. Create and process tool execution finish
        tool_finish_event = {
            "name": "tool.execution.finish",
            "timestamp": (base_time + datetime.timedelta(milliseconds=560)).isoformat() + "Z",
            "agent_id": agent_id,
            "trace_id": trace_id,
            "event_type": "tool",
            "level": "INFO",
            "schema_version": "1.0",
            "span_id": tool_span_id,
            "attributes": {
                "tool.name": "weather_api",
                "tool.timestamp": (base_time + datetime.timedelta(milliseconds=560)).isoformat() + "Z",
                "tool.output": {"temperature": 72, "conditions": "partly cloudy", "humidity": 65},
                "tool.duration_ms": 300,
                "tool.status": "success",
                "session.id": session_id
            }
        }
        result9 = processor.process_event(tool_finish_event)
        assert result9["success"] is True
        
        # 10. Create and process tool span end
        tool_span_end_event = {
            "name": "span.end",
            "timestamp": (base_time + datetime.timedelta(milliseconds=570)).isoformat() + "Z",
            "agent_id": agent_id,
            "trace_id": trace_id,
            "event_type": "span",
            "level": "INFO",
            "schema_version": "1.0",
            "attributes": {
                "span.id": tool_span_id,
                "span.end_time": (base_time + datetime.timedelta(milliseconds=570)).isoformat() + "Z",
                "session.id": session_id
            }
        }
        result10 = processor.process_event(tool_span_end_event)
        assert result10["success"] is True
        
        # 11. Create and process second LLM span start
        second_llm_span_event = {
            "name": "span.start",
            "timestamp": (base_time + datetime.timedelta(milliseconds=580)).isoformat() + "Z",
            "agent_id": agent_id,
            "trace_id": trace_id,
            "event_type": "span",
            "level": "INFO",
            "schema_version": "1.0",
            "attributes": {
                "span.id": second_llm_span_id,
                "span.name": "llm_call_2",
                "span.start_time": (base_time + datetime.timedelta(milliseconds=580)).isoformat() + "Z",
                "span.parent_id": conversation_span_id,
                "session.id": session_id
            }
        }
        result11 = processor.process_event(second_llm_span_event)
        assert result11["success"] is True
        
        # 12. Create and process second LLM call start
        second_llm_start_event = {
            "name": "llm.call.start",
            "timestamp": (base_time + datetime.timedelta(milliseconds=590)).isoformat() + "Z",
            "agent_id": agent_id,
            "trace_id": trace_id,
            "event_type": "llm",
            "level": "INFO",
            "schema_version": "1.0",
            "span_id": second_llm_span_id,
            "attributes": {
                "llm.vendor": "anthropic",
                "llm.model": "claude-3-haiku-20240307",
                "llm.request.timestamp": (base_time + datetime.timedelta(milliseconds=590)).isoformat() + "Z",
                "llm.request.data": {
                    "messages": [
                        {"role": "user", "content": "What's the weather in San Francisco?"},
                        {"role": "assistant", "content": "I need to check the current weather in San Francisco. Let me use a tool to look that up for you."},
                        {"role": "user", "content": "Tool result: {\"temperature\": 72, \"conditions\": \"partly cloudy\", \"humidity\": 65}"}
                    ]
                },
                "llm.config.temperature": 0.7,
                "llm.config.max_tokens": 1000,
                "session.id": session_id
            }
        }
        result12 = processor.process_event(second_llm_start_event)
        assert result12["success"] is True
        
        # 13. Create and process second LLM call finish
        second_llm_finish_event = {
            "name": "llm.call.finish",
            "timestamp": (base_time + datetime.timedelta(milliseconds=790)).isoformat() + "Z",
            "agent_id": agent_id,
            "trace_id": trace_id,
            "event_type": "llm",
            "level": "INFO",
            "schema_version": "1.0",
            "span_id": second_llm_span_id,
            "attributes": {
                "llm.vendor": "anthropic",
                "llm.model": "claude-3-haiku-20240307",
                "llm.request.timestamp": (base_time + datetime.timedelta(milliseconds=590)).isoformat() + "Z",
                "llm.response.timestamp": (base_time + datetime.timedelta(milliseconds=790)).isoformat() + "Z",
                "llm.response.duration_ms": 200,
                "llm.usage.input_tokens": 65,
                "llm.usage.output_tokens": 42,
                "llm.usage.total_tokens": 107,
                "llm.response.content": {
                    "type": "text", 
                    "text": "The current weather in San Francisco is 72°F and partly cloudy with 65% humidity."
                },
                "llm.response.id": f"resp_{uuid.uuid4()}",
                "llm.response.stop_reason": "end_turn",
                "session.id": session_id
            }
        }
        result13 = processor.process_event(second_llm_finish_event)
        assert result13["success"] is True
        
        # 14. Create and process second LLM span end
        second_llm_span_end_event = {
            "name": "span.end",
            "timestamp": (base_time + datetime.timedelta(milliseconds=800)).isoformat() + "Z",
            "agent_id": agent_id,
            "trace_id": trace_id,
            "event_type": "span",
            "level": "INFO",
            "schema_version": "1.0",
            "attributes": {
                "span.id": second_llm_span_id,
                "span.end_time": (base_time + datetime.timedelta(milliseconds=800)).isoformat() + "Z",
                "session.id": session_id
            }
        }
        result14 = processor.process_event(second_llm_span_end_event)
        assert result14["success"] is True
        
        # 15. Create and process conversation span end
        conversation_span_end_event = {
            "name": "span.end",
            "timestamp": (base_time + datetime.timedelta(milliseconds=810)).isoformat() + "Z",
            "agent_id": agent_id,
            "trace_id": trace_id,
            "event_type": "span",
            "level": "INFO",
            "schema_version": "1.0",
            "attributes": {
                "span.id": conversation_span_id,
                "span.end_time": (base_time + datetime.timedelta(milliseconds=810)).isoformat() + "Z",
                "session.id": session_id
            }
        }
        result15 = processor.process_event(conversation_span_end_event)
        assert result15["success"] is True
        
        # 16. Create and process session end event
        session_end_event = {
            "name": "session.end",
            "timestamp": (base_time + datetime.timedelta(milliseconds=820)).isoformat() + "Z",
            "agent_id": agent_id,
            "trace_id": trace_id,
            "event_type": "session",
            "level": "INFO",
            "schema_version": "1.0",
            "attributes": {
                "session.id": session_id,
                "session.end_time": (base_time + datetime.timedelta(milliseconds=820)).isoformat() + "Z"
            }
        }
        result16 = processor.process_event(session_end_event)
        assert result16["success"] is True
        
        # Verify database state
        session = next(session_factory())
        
        # Event counts
        events_count = session.query(func.count(Event.id)).scalar()
        llm_interactions_count = session.query(func.count(LLMInteraction.id)).scalar()
        tool_interactions_count = session.query(func.count(ToolInteraction.id)).scalar()
        spans_count = session.query(func.count(Span.span_id)).scalar()
        sessions_count = session.query(func.count(SessionModel.id)).scalar()
        
        assert events_count == 16
        assert llm_interactions_count == 4
        assert tool_interactions_count == 2
        assert spans_count == 3
        assert sessions_count == 1
        
        # Verify session duration
        sess = session.query(SessionModel).filter(SessionModel.session_id == session_id).first()
        assert sess is not None
        assert sess.start_time is not None
        assert sess.end_time is not None
        assert sess.duration_ms is not None
        assert sess.duration_ms > 0
        
        # Verify span hierarchy
        parent_span = session.query(Span).filter(Span.span_id == conversation_span_id).first()
        assert parent_span is not None
        assert parent_span.start_time is not None
        assert parent_span.end_time is not None
        assert parent_span.duration_ms is not None
        assert parent_span.duration_ms > 0
        
        child_spans = session.query(Span).filter(Span.parent_id == conversation_span_id).all()
        assert len(child_spans) == 2
        
        # Verify LLM interactions
        llm_interactions = session.query(LLMInteraction).all()
        first_llm_start = next((i for i in llm_interactions if i.interaction_type == "start" and "What's the weather in San Francisco?" in str(i.request_data)), None)
        assert first_llm_start is not None
        
        first_llm_finish = next((i for i in llm_interactions if i.interaction_type == "finish" and "I need to check the current weather" in str(i.response_content)), None)
        assert first_llm_finish is not None
        
        second_llm_finish = next((i for i in llm_interactions if i.interaction_type == "finish" and "72°F and partly cloudy" in str(i.response_content)), None)
        assert second_llm_finish is not None
        
        # Verify tool interactions
        tool_interactions = session.query(ToolInteraction).all()
        tool_start = next((i for i in tool_interactions if "start" in i.event.name), None)
        assert tool_start is not None
        assert tool_start.tool_name == "weather_api"
        assert tool_start.tool_input == {"location": "San Francisco, CA"}
        
        tool_finish = next((i for i in tool_interactions if "finish" in i.event.name), None)
        assert tool_finish is not None
        assert tool_finish.tool_output == {"temperature": 72, "conditions": "partly cloudy", "humidity": 65}
        assert tool_finish.status == "success"
    
    def test_processing_out_of_order_events(self, setup_e2e_test):
        """
        Test processing events that arrive out of chronological order.
        The system should handle this correctly.
        """
        engine, session_factory, processor = setup_e2e_test
        session = next(session_factory())
        
        # Create test agent
        agent_id = "out-of-order-agent"
        agent = Agent(
            agent_id=agent_id,
            name="Out of Order Test Agent",
            first_seen=datetime.datetime.utcnow(),
            last_seen=datetime.datetime.utcnow(),
            is_active=True
        )
        session.add(agent)
        session.commit()
        
        # Create test data
        session_id = str(uuid.uuid4())
        span_id = str(uuid.uuid4())
        base_time = datetime.datetime.utcnow()
        
        # Create events in chronological order
        events = [
            # 1. Session start
            {
                "name": "session.start",
                "timestamp": base_time.isoformat() + "Z",
                "agent_id": agent_id,
                "event_type": "session",
                "level": "INFO",
                "schema_version": "1.0",
                "attributes": {
                    "session.id": session_id,
                    "session.name": "Out of Order Test",
                    "session.start_time": base_time.isoformat() + "Z"
                }
            },
            # 2. Span start
            {
                "name": "span.start",
                "timestamp": (base_time + datetime.timedelta(milliseconds=100)).isoformat() + "Z",
                "agent_id": agent_id,
                "event_type": "span",
                "level": "INFO",
                "schema_version": "1.0",
                "attributes": {
                    "span.id": span_id,
                    "span.name": "test_span",
                    "span.start_time": (base_time + datetime.timedelta(milliseconds=100)).isoformat() + "Z",
                    "session.id": session_id
                }
            },
            # 3. LLM call start
            {
                "name": "llm.call.start",
                "timestamp": (base_time + datetime.timedelta(milliseconds=200)).isoformat() + "Z",
                "agent_id": agent_id,
                "event_type": "llm",
                "level": "INFO",
                "schema_version": "1.0",
                "span_id": span_id,
                "attributes": {
                    "llm.vendor": "anthropic",
                    "llm.model": "claude-3-haiku-20240307",
                    "llm.request.timestamp": (base_time + datetime.timedelta(milliseconds=200)).isoformat() + "Z",
                    "llm.request.data": {
                        "messages": [{"role": "user", "content": "Hello world"}]
                    },
                    "session.id": session_id
                }
            },
            # 4. LLM call finish
            {
                "name": "llm.call.finish",
                "timestamp": (base_time + datetime.timedelta(milliseconds=400)).isoformat() + "Z",
                "agent_id": agent_id,
                "event_type": "llm",
                "level": "INFO",
                "schema_version": "1.0",
                "span_id": span_id,
                "attributes": {
                    "llm.vendor": "anthropic",
                    "llm.model": "claude-3-haiku-20240307",
                    "llm.request.timestamp": (base_time + datetime.timedelta(milliseconds=200)).isoformat() + "Z",
                    "llm.response.timestamp": (base_time + datetime.timedelta(milliseconds=400)).isoformat() + "Z",
                    "llm.response.duration_ms": 200,
                    "llm.usage.input_tokens": 3,
                    "llm.usage.output_tokens": 12,
                    "llm.usage.total_tokens": 15,
                    "llm.response.content": {"type": "text", "text": "Hello! How can I help you today?"},
                    "llm.response.id": f"resp_{uuid.uuid4()}",
                    "llm.response.stop_reason": "end_turn",
                    "session.id": session_id
                }
            },
            # 5. Span end
            {
                "name": "span.end",
                "timestamp": (base_time + datetime.timedelta(milliseconds=500)).isoformat() + "Z",
                "agent_id": agent_id,
                "event_type": "span",
                "level": "INFO",
                "schema_version": "1.0",
                "attributes": {
                    "span.id": span_id,
                    "span.end_time": (base_time + datetime.timedelta(milliseconds=500)).isoformat() + "Z",
                    "session.id": session_id
                }
            },
            # 6. Session end
            {
                "name": "session.end",
                "timestamp": (base_time + datetime.timedelta(milliseconds=600)).isoformat() + "Z",
                "agent_id": agent_id,
                "event_type": "session",
                "level": "INFO",
                "schema_version": "1.0",
                "attributes": {
                    "session.id": session_id,
                    "session.end_time": (base_time + datetime.timedelta(milliseconds=600)).isoformat() + "Z"
                }
            }
        ]
        
        # Process events in reverse order
        for event in reversed(events):
            result = processor.process_event(event)
            assert result["success"] is True
        
        # Verify database state
        session = next(session_factory())
        
        # Event counts
        events_count = session.query(func.count(Event.id)).scalar()
        llm_interactions_count = session.query(func.count(LLMInteraction.id)).scalar()
        spans_count = session.query(func.count(Span.span_id)).scalar()
        sessions_count = session.query(func.count(SessionModel.id)).scalar()
        
        assert events_count == 6
        assert llm_interactions_count == 2
        assert spans_count == 1
        assert sessions_count == 1
        
        # Verify session
        sess = session.query(SessionModel).filter(SessionModel.session_id == session_id).first()
        assert sess is not None
        assert sess.start_time is not None
        assert sess.end_time is not None
        assert sess.duration_ms is not None
        assert sess.duration_ms > 0
        
        # Verify span
        span = session.query(Span).filter(Span.span_id == span_id).first()
        assert span is not None
        assert span.start_time is not None
        assert span.end_time is not None
        assert span.duration_ms is not None
        assert span.duration_ms > 0
        
        # Verify LLM interactions
        llm_start = session.query(LLMInteraction).filter(
            LLMInteraction.interaction_type == "start"
        ).first()
        assert llm_start is not None
        
        llm_finish = session.query(LLMInteraction).filter(
            LLMInteraction.interaction_type == "finish"
        ).first()
        assert llm_finish is not None
        assert llm_finish.duration_ms == 200
    
    def test_process_real_example_records(self, setup_e2e_test):
        """
        Test processing the example_records.json file if it exists.
        This tests the system with real-world data.
        """
        example_file = Path("example_records.json")
        if not example_file.exists():
            pytest.skip("example_records.json not found, skipping test")
        
        engine, session_factory, processor = setup_e2e_test
        session = next(session_factory())
        
        # Pre-create agents to avoid errors
        agents = ["chatbot-agent", "rag-agent", "weather-agent"]
        for agent_id in agents:
            agent = Agent(
                agent_id=agent_id,
                name=f"{agent_id.capitalize()} Agent",
                first_seen=datetime.datetime.utcnow(),
                last_seen=datetime.datetime.utcnow(),
                is_active=True
            )
            session.add(agent)
        session.commit()
        
        # Load events from example_records.json
        events = []
        with open(example_file, 'r') as f:
            for line in f:
                try:
                    event_data = json.loads(line)
                    events.append(event_data)
                except json.JSONDecodeError:
                    continue
        
        if not events:
            pytest.skip("No events found in example_records.json")
        
        # Process events in batch
        result = processor.process_batch(events)
        
        # Verify basic processing result
        assert result["total"] == len(events)
        assert result["successful"] > 0
        
        # Verify database state has records
        session = next(session_factory())
        
        events_count = session.query(func.count(Event.id)).scalar()
        assert events_count > 0
        
        # Check that we have some of each type of record
        llm_interactions_count = session.query(func.count(LLMInteraction.id)).scalar()
        security_alerts_count = session.query(func.count(SecurityAlert.id)).scalar()
        framework_events_count = session.query(func.count(FrameworkEvent.id)).scalar()
        tool_interactions_count = session.query(func.count(ToolInteraction.id)).scalar()
        sessions_count = session.query(func.count(SessionModel.id)).scalar()
        spans_count = session.query(func.count(Span.span_id)).scalar()
        
        print(f"\nProcessed {len(events)} events from example_records.json")
        print(f"Events: {events_count}")
        print(f"LLM Interactions: {llm_interactions_count}")
        print(f"Security Alerts: {security_alerts_count}")
        print(f"Framework Events: {framework_events_count}")
        print(f"Tool Interactions: {tool_interactions_count}")
        print(f"Sessions: {sessions_count}")
        print(f"Spans: {spans_count}")
        
        # The specific numbers will depend on the example_records.json content,
        # but we can assert that we have some records
        assert events_count > 0
        # We should have at least some spans for tracing
        assert spans_count > 0 