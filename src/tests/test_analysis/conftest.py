"""
Pytest fixtures for analysis tests.
"""
import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import uuid
import re
import sqlite3
from sqlalchemy import event
from sqlalchemy.engine import Engine

from models.event import Event
from models.llm_interaction import LLMInteraction
from models.security_alert import SecurityAlert
from models.tool_interaction import ToolInteraction


# SQLite date_format implementation
def sqlite_date_format(timestamp_str, format_str):
    """Implement MySQL-like date_format for SQLite."""
    try:
        # Convert format strings from MySQL to SQLite format
        format_str = format_str.replace('%Y', '%Y')  # Year (4 digits)
        format_str = format_str.replace('%y', '%y')  # Year (2 digits)
        format_str = format_str.replace('%m', '%m')  # Month (01-12)
        format_str = format_str.replace('%d', '%d')  # Day (01-31)
        format_str = format_str.replace('%H', '%H')  # Hour (00-23)
        format_str = format_str.replace('%h', '%I')  # Hour (01-12)
        format_str = format_str.replace('%i', '%M')  # Minute (00-59)
        format_str = format_str.replace('%s', '%S')  # Second (00-59)
        
        # Parse the timestamp (handle various formats)
        if isinstance(timestamp_str, str):
            dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        else:
            dt = timestamp_str
            
        return dt.strftime(format_str)
    except Exception as e:
        return str(e)


# Register function with SQLite connection
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Register custom functions for SQLite connections."""
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        
        # Register custom functions for SQLite
        dbapi_connection.create_function("date_format", 2, sqlite_date_format)
        cursor.close()


@pytest.fixture
def mock_data(db_session: Session):
    """
    Create mock data for testing analysis functions.
    
    Generates various event types with predictable patterns suitable for testing
    analytics queries. Includes events, LLM interactions, tool events, and security alerts.
    
    Args:
        db_session: SQLAlchemy database session
    
    Returns:
        Dictionary with created entities grouped by type
    """
    now = datetime.utcnow()
    
    # Create test agents and sessions
    agent_ids = [f"agent-{i}" for i in range(3)]
    session_ids = [f"session-{i}" for i in range(3)]
    trace_ids = [f"trace-{i}" for i in range(3)]
    
    events = []
    llm_interactions = []
    tool_interactions = []
    security_alerts = []
    
    # Create basic events for each agent/session
    for i, agent_id in enumerate(agent_ids):
        for j, session_id in enumerate(session_ids):
            for k, trace_id in enumerate(trace_ids):
                # Create an event
                event = Event(
                    agent_id=agent_id,
                    session_id=session_id,
                    trace_id=trace_id,
                    timestamp=now - timedelta(hours=i+j),
                    schema_version="1.0",
                    name=f"test_event_{i}_{j}_{k}",
                    level="INFO",
                    event_type="test_event"
                )
                events.append(event)
    
    # Create LLM interactions
    model_names = ["gpt-4", "gpt-3.5-turbo", "claude-3"]
    for i, agent_id in enumerate(agent_ids):
        for j, model_name in enumerate(model_names):
            # Create an event for the LLM interaction
            llm_event = Event(
                agent_id=agent_id,
                session_id=session_ids[i % len(session_ids)],
                trace_id=trace_ids[i % len(trace_ids)],
                timestamp=now - timedelta(hours=i+j),
                schema_version="1.0",
                name="llm.interaction",
                level="INFO",
                event_type="llm"
            )
            events.append(llm_event)
            
            db_session.add(llm_event)
            db_session.flush()  # Generate ID for the event
            
            # Create the LLM interaction
            llm_interaction = LLMInteraction(
                event_id=llm_event.id,
                interaction_type="finish",
                vendor="openai" if model_name.startswith("gpt") else "anthropic",
                model=model_name,
                request_timestamp=now - timedelta(hours=i+j, minutes=5),
                response_timestamp=now - timedelta(hours=i+j),
                duration_ms=5000,
                input_tokens=100 * (i+1),
                output_tokens=50 * (j+1),
                total_tokens=100 * (i+1) + 50 * (j+1)
            )
            llm_interactions.append(llm_interaction)
    
    # Create tool interactions
    tool_names = ["search", "calculator", "file_reader"]
    for i, agent_id in enumerate(agent_ids):
        for j, tool_name in enumerate(tool_names):
            # Create an event for the tool interaction
            tool_event = Event(
                agent_id=agent_id,
                session_id=session_ids[i % len(session_ids)],
                trace_id=trace_ids[i % len(trace_ids)],
                timestamp=now - timedelta(hours=i+j),
                schema_version="1.0",
                name="tool.call",
                level="INFO",
                event_type="tool"
            )
            events.append(tool_event)
            
            db_session.add(tool_event)
            db_session.flush()  # Generate ID for the event
            
            # Create the tool interaction
            tool_interaction = ToolInteraction(
                event_id=tool_event.id,
                tool_name=tool_name,
                interaction_type="result",
                status="success" if (i + j) % 2 == 0 else "error",
                duration_ms=(i+1) * 100,
                error="Test error message" if (i + j) % 2 != 0 else None,
                request_timestamp=now - timedelta(hours=i+j, minutes=5),
                response_timestamp=now - timedelta(hours=i+j)
            )
            tool_interactions.append(tool_interaction)
    
    # Create security alerts
    alert_types = ["prompt_injection", "data_leak", "suspicious_activity"]
    severities = ["low", "medium", "high"]
    for i, agent_id in enumerate(agent_ids):
        for j, (alert_type, severity) in enumerate(zip(alert_types, severities)):
            # Create an event for the security alert
            security_event = Event(
                agent_id=agent_id,
                session_id=session_ids[i % len(session_ids)],
                trace_id=trace_ids[i % len(trace_ids)],
                timestamp=now - timedelta(hours=i+j),
                schema_version="1.0",
                name="security.alert",
                level="WARNING",
                event_type="security"
            )
            events.append(security_event)
            
            db_session.add(security_event)
            db_session.flush()  # Generate ID for the event
            
            # Create the security alert
            security_alert = SecurityAlert(
                event_id=security_event.id,
                alert_type=alert_type,
                severity=severity,
                description=f"Test security alert for {alert_type}",
                timestamp=now - timedelta(hours=i+j),
                status="OPEN",
                raw_attributes={"keywords": ["test", "security", alert_type]},
                detection_source="test",
                confidence_score=0.8,
                risk_level=severity
            )
            security_alerts.append(security_alert)
    
    # Add all objects to the database
    db_session.add_all(events)
    db_session.add_all(llm_interactions)
    db_session.add_all(tool_interactions)
    db_session.add_all(security_alerts)
    db_session.commit()
    
    return {
        "events": events,
        "llm_interactions": llm_interactions,
        "tool_interactions": tool_interactions,
        "security_alerts": security_alerts,
        "agent_ids": agent_ids,
        "session_ids": session_ids,
        "trace_ids": trace_ids
    } 