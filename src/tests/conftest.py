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
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

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

from tests.test_utils import (
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
    Create a new database session for a test.
    """
    connection = db_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def db_session_factory(db_engine, db_tables):
    """
    Create a new database session factory for tests that need multiple sessions.
    """
    session_factory = sessionmaker(bind=db_engine)
    
    @contextmanager
    def get_session():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()
    
    return get_session


@pytest.fixture(scope="function")
def temp_db_path():
    """
    Create a temporary file path for a SQLite database.
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
    """Create a test agent for use in tests."""
    return generate_agent(db_session)


@pytest.fixture(scope="function")
def test_event(db_session, test_agent):
    """Create a test event for use in tests."""
    return generate_event(db_session, test_agent)


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
                "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
                "agent_id": f"perf-agent-{i % 5}",
                "event_type": "llm",
                "level": "INFO",
                "schema_version": "1.0",
                "attributes": {
                    "llm.vendor": vendors[i % len(vendors)],
                    "llm.model": models[i % len(models)],
                    "llm.request.timestamp": datetime.datetime.utcnow().isoformat() + "Z",
                }
            }
            
            if i % 2 == 0:  # start event
                event_data["attributes"]["llm.request.data"] = {
                    "messages": [{"role": "user", "content": f"Test message {i}"}]
                }
            else:  # finish event
                event_data["attributes"]["llm.response.timestamp"] = datetime.datetime.utcnow().isoformat() + "Z"
                event_data["attributes"]["llm.response.duration_ms"] = 100 + (i * 10)
                event_data["attributes"]["llm.usage.input_tokens"] = 10 + i
                event_data["attributes"]["llm.usage.output_tokens"] = 20 + i
                event_data["attributes"]["llm.usage.total_tokens"] = 30 + (2 * i)
                event_data["attributes"]["llm.response.content"] = {"type": "text", "text": f"Response {i}"}
        
        elif event_type == "security":
            event_data = {
                "name": "security.alert.detected",
                "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
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
                "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
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
                "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
                "agent_id": f"perf-agent-{i % 5}",
                "event_type": "tool",
                "level": "INFO",
                "schema_version": "1.0",
                "attributes": {
                    "tool.name": f"tool_{i % 10}",
                    "tool.timestamp": datetime.datetime.utcnow().isoformat() + "Z",
                }
            }
        
        elif event_type == "span":
            event_data = {
                "name": "span.start",
                "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
                "agent_id": f"perf-agent-{i % 5}",
                "event_type": "span",
                "level": "INFO",
                "schema_version": "1.0",
                "attributes": {
                    "span.id": f"span-{i}",
                    "span.name": f"span_{i}",
                    "span.start_time": datetime.datetime.utcnow().isoformat() + "Z",
                }
            }
            
            if i % 3 != 0:  # Not a root span
                event_data["attributes"]["span.parent_id"] = f"span-{i-1}"
        
        else:  # session
            event_data = {
                "name": "session.start",
                "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
                "agent_id": f"perf-agent-{i % 5}",
                "event_type": "session",
                "level": "INFO",
                "schema_version": "1.0",
                "attributes": {
                    "session.id": f"session-{i % 10}",
                    "session.name": f"Session {i % 10}",
                    "session.start_time": datetime.datetime.utcnow().isoformat() + "Z",
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