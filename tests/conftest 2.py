"""
Test fixtures for Cylestio Local Server.

This module contains pytest fixtures for setting up test databases and sessions.
"""
import os
import json
import tempfile
import pytest
import datetime
import psutil
from pathlib import Path
from contextlib import contextmanager

# Import entrypoint to apply patches before importing SQLAlchemy
try:
    import src.entrypoint as entrypoint
except ImportError:
    # Create a fallback entrypoint if the real one doesn't exist
    class DummyEntrypoint:
        @staticmethod
        def initialize():
            pass
    entrypoint = DummyEntrypoint

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from datetime import timezone

from src.models.base import Base
from src.models.agent import Agent
from src.models.event import Event
from src.models.llm_interaction import LLMInteraction
from src.models.security_alert import SecurityAlert
from src.models.framework_event import FrameworkEvent
from src.models.tool_interaction import ToolInteraction
from src.models.session import Session as SessionModel
from src.models.span import Span
from src.models.trace import Trace
from src.processing.simple_processor import SimpleProcessor

from tests.utils.test_utils import (
    generate_agent, generate_event, generate_llm_interaction_data,
    generate_security_alert_data, generate_framework_event_data,
    generate_tool_interaction_data, generate_span_data, generate_session_data
)


@pytest.fixture(scope="session")
def db_engine():
    """
    Create a SQLite in-memory database engine for testing.
    """
    engine = create_engine("sqlite:///:memory:", echo=False)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def db_tables(db_engine):
    """
    Create all database tables for testing.
    """
    Base.metadata.create_all(db_engine)
    yield
    Base.metadata.drop_all(db_engine)


@pytest.fixture(scope="function")
def db_session(db_engine, db_tables):
    """
    Create a new database session for a test with transaction isolation.
    
    This fixture ensures each test runs in its own transaction which is
    rolled back after the test completes, preventing test cross-contamination.
    """
    # Connect to the database and begin a transaction
    connection = db_engine.connect()
    # Begin a SAVEPOINT transaction that can be rolled back
    transaction = connection.begin()
    
    # Create a session bound to the connection
    session = Session(bind=connection)
    
    yield session
    
    # After the test completes, roll back the transaction to reset the database state
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def db_session_factory(db_engine, db_tables):
    """
    Create a new database session factory for tests that need multiple sessions.
    
    Ensures each session is properly closed and doesn't affect other tests.
    """
    connection = db_engine.connect()
    transaction = connection.begin()
    
    session_factory = sessionmaker(bind=connection)
    
    @contextmanager
    def get_session():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()
    
    yield get_session
    
    # Clean up after the test
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def temp_db_path():
    """
    Create a temporary file path for a SQLite database.
    Ensures the database file is removed after the test.
    """
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture(scope="function")
def temp_db_engine(temp_db_path):
    """
    Create a SQLite database engine with a temporary file.
    Ensures proper cleanup after test completion.
    """
    engine = create_engine(f"sqlite:///{temp_db_path}", echo=False)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()
    Base.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def temp_db_session(temp_db_engine):
    """
    Create a new database session for a test with a temporary file database.
    Uses transaction isolation to prevent test cross-contamination.
    """
    connection = temp_db_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def simple_processor(db_session_factory):
    """
    Create a SimpleProcessor for testing.
    """
    return SimpleProcessor(db_session_factory)


@pytest.fixture(scope="function")
def test_agent(db_session):
    """Create a test agent for use in tests. Clean up after test."""
    agent = generate_agent(db_session)
    db_session.flush()  # Ensure the agent is saved but not committed
    return agent


@pytest.fixture(scope="function")
def test_event(db_session, test_agent):
    """Create a test event for use in tests."""
    event = generate_event(db_session, test_agent)
    db_session.flush()  # Ensure the event is saved but not committed
    return event


@pytest.fixture(scope="function")
def test_llm_events(db_session, test_agent):
    """Create test events for LLM interactions."""
    start_event = generate_event(
        db_session, test_agent, 
        event_name="llm.call.start", 
        event_type="llm"
    )
    
    finish_event = generate_event(
        db_session, test_agent,
        event_name="llm.call.finish",
        event_type="llm"
    )
    
    return start_event, finish_event


@pytest.fixture(scope="function")
def test_security_alert_event(db_session, test_agent):
    """Create a test event for security alerts."""
    return generate_event(
        db_session, test_agent,
        event_name="security.alert.detected",
        event_type="security"
    )


@pytest.fixture(scope="function")
def test_framework_event(db_session, test_agent):
    """Create a test event for framework events."""
    return generate_event(
        db_session, test_agent,
        event_name="framework.component.start",
        event_type="framework"
    )


@pytest.fixture(scope="function")
def test_tool_events(db_session, test_agent):
    """Create test events for tool interactions."""
    start_event = generate_event(
        db_session, test_agent,
        event_name="tool.execution.start",
        event_type="tool"
    )
    
    finish_event = generate_event(
        db_session, test_agent,
        event_name="tool.execution.finish",
        event_type="tool"
    )
    
    return start_event, finish_event


@pytest.fixture(scope="function")
def test_span_event(db_session, test_agent):
    """Create a test event for spans."""
    return generate_event(
        db_session, test_agent,
        event_name="span.start",
        event_type="span"
    )


@pytest.fixture(scope="function")
def test_session_event(db_session, test_agent):
    """Create a test event for sessions."""
    return generate_event(
        db_session, test_agent,
        event_name="session.start",
        event_type="session"
    )


@pytest.fixture(scope="function")
def example_records():
    """
    Load example records from the example_records.json file.
    """
    example_file = Path("example_records.json")
    if not example_file.exists():
        return []
    
    records = []
    with open(example_file, 'r') as f:
        for line in f:
            try:
                event_data = json.loads(line)
                records.append(event_data)
            except json.JSONDecodeError:
                continue
    
    return records


@pytest.fixture(scope="function")
def performance_test_data(n=50):
    """
    Generate a large dataset for performance testing.
    """
    vendors = ["anthropic", "openai", "cohere", "mistral"]
    models = [
        "claude-3-haiku-20240307", "claude-3-sonnet-20240229", 
        "gpt-4-turbo", "gpt-3.5-turbo", "cohere-command", "mixtral-8x7b"
    ]
    event_types = ["llm", "security", "framework", "tool", "span", "session"]
    
    events = []
    for i in range(n):
        event_type = event_types[i % len(event_types)]
        
        if event_type == "llm":
            event_data = {
                "name": "llm.call.start" if i % 2 == 0 else "llm.call.finish",
                "timestamp": datetime.datetime.now(timezone.utc).isoformat() + "Z",
                "agent_id": f"perf-agent-{i % 5}",
                "event_type": "llm",
                "level": "INFO",
                "schema_version": "1.0",
                "attributes": {
                    "llm.vendor": vendors[i % len(vendors)],
                    "llm.model": models[i % len(models)],
                    "llm.request.timestamp": datetime.datetime.now(timezone.utc).isoformat() + "Z",
                }
            }
            
            if i % 2 == 0:  # start event
                event_data["attributes"]["llm.request.data"] = {
                    "messages": [{"role": "user", "content": f"Test message {i}"}]
                }
            else:  # finish event
                event_data["attributes"]["llm.response.timestamp"] = datetime.datetime.now(timezone.utc).isoformat() + "Z"
                event_data["attributes"]["llm.response.duration_ms"] = 100 + (i * 10)
                event_data["attributes"]["llm.usage.input_tokens"] = 10 + i
                event_data["attributes"]["llm.usage.output_tokens"] = 20 + i
                event_data["attributes"]["llm.usage.total_tokens"] = 30 + (2 * i)
                event_data["attributes"]["llm.response.content"] = {"type": "text", "text": f"Response {i}"}
        
        elif event_type == "security":
            event_data = {
                "name": "security.alert.detected",
                "timestamp": datetime.datetime.now(timezone.utc).isoformat() + "Z",
                "agent_id": f"perf-agent-{i % 5}",
                "event_type": "security",
                "level": "WARN",
                "schema_version": "1.0",
                "attributes": {
                    "security.alert.type": "content_policy_violation",
                    "security.alert.severity": "medium",
                    "security.alert.details": {
                        "policy": "harmful_content",
                        "score": 0.7 + (i * 0.01),
                        "flagged_content": f"Potentially harmful content {i}"
                    }
                }
            }
        
        elif event_type == "framework":
            event_data = {
                "name": "framework.component.start",
                "timestamp": datetime.datetime.now(timezone.utc).isoformat() + "Z",
                "agent_id": f"perf-agent-{i % 5}",
                "event_type": "framework",
                "level": "INFO",
                "schema_version": "1.0",
                "attributes": {
                    "framework.type": "langchain" if i % 2 == 0 else "llamaindex",
                    "framework.version": f"0.{i % 10}.0",
                }
            }
        
        elif event_type == "tool":
            event_data = {
                "name": "tool.execution.start" if i % 2 == 0 else "tool.execution.finish",
                "timestamp": datetime.datetime.now(timezone.utc).isoformat() + "Z",
                "agent_id": f"perf-agent-{i % 5}",
                "event_type": "tool",
                "level": "INFO",
                "schema_version": "1.0",
                "attributes": {
                    "tool.name": f"tool_{i % 10}",
                    "tool.timestamp": datetime.datetime.now(timezone.utc).isoformat() + "Z",
                }
            }
        
        elif event_type == "span":
            event_data = {
                "name": "span.start",
                "timestamp": datetime.datetime.now(timezone.utc).isoformat() + "Z",
                "agent_id": f"perf-agent-{i % 5}",
                "event_type": "span",
                "level": "INFO",
                "schema_version": "1.0",
                "attributes": {
                    "span.id": f"span-{i}",
                    "span.name": f"span_{i}",
                    "span.start_time": datetime.datetime.now(timezone.utc).isoformat() + "Z",
                }
            }
            
            if i % 3 != 0:  # Not a root span
                event_data["attributes"]["span.parent_id"] = f"span-{i-1}"
        
        else:  # session
            event_data = {
                "name": "session.start",
                "timestamp": datetime.datetime.now(timezone.utc).isoformat() + "Z",
                "agent_id": f"perf-agent-{i % 5}",
                "event_type": "session",
                "level": "INFO",
                "schema_version": "1.0",
                "attributes": {
                    "session.id": f"session-{i % 10}",
                    "session.name": f"Session {i % 10}",
                    "session.start_time": datetime.datetime.now(timezone.utc).isoformat() + "Z",
                }
            }
        
        events.append(event_data)
    
    return events


@pytest.fixture(scope="function")
def memory_profile():
    """
    Profile memory usage during a test.
    """
    process = psutil.Process(os.getpid())
    mem_before = process.memory_info().rss / 1024 / 1024  # MB
    
    yield
    
    mem_after = process.memory_info().rss / 1024 / 1024  # MB
    memory_used = mem_after - mem_before
    
    print(f"\nMemory used: {memory_used:.2f} MB")
    return memory_used


@pytest.fixture
def event_data():
    """Return sample event data for testing."""
    return {
        "event_id": "test-event-1",
        "event_type": "test.event",
        "agent_id": "test-agent-1",
        "session_id": "test-session-1",
        "attributes": {
            "timestamp": datetime.datetime.now(timezone.utc).isoformat() + "Z",
            "key1": "value1",
            "key2": "value2"
        }
    }


@pytest.fixture
def llm_request_event_data():
    """Return sample LLM request event data for testing."""
    return {
        "event_id": "llm-request-1",
        "event_type": "llm.request",
        "agent_id": "test-agent-1",
        "session_id": "test-session-1",
        "parent_id": None,
        "trace_id": "test-trace-1",
        "attributes": {
            "llm.request.timestamp": datetime.datetime.now(timezone.utc).isoformat() + "Z",
            "llm.request.model": "gpt-4",
            "llm.request.messages": json.dumps([{"role": "user", "content": "Hello"}]),
            "llm.request.temperature": 0.7
        }
    }


@pytest.fixture
def llm_response_event_data(llm_request_event_data):
    """Return sample LLM response event data for testing."""
    event_data = {
        "event_id": "llm-response-1",
        "event_type": "llm.response",
        "agent_id": "test-agent-1",
        "session_id": "test-session-1",
        "parent_id": "llm-request-1",
        "trace_id": "test-trace-1",
        "attributes": {
            "llm.response.content": "Hi there! How can I help you today?",
            "llm.response.tokens": 10,
            "llm.response.model": "gpt-4"
        }
    }
    event_data["attributes"]["llm.response.timestamp"] = datetime.datetime.now(timezone.utc).isoformat() + "Z"
    return event_data 