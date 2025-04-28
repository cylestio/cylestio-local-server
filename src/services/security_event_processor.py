"""
Security event processing service.

This module provides specialized processing for security events in the
OpenTelemetry-compliant format.
"""
import json
import logging
from typing import Dict, Any, Tuple, Optional
from datetime import datetime

from sqlalchemy.orm import Session

from src.models.event import Event
from src.models.security_alert import SecurityAlert
from src.models.agent import Agent
from src.utils.logging import get_logger

# Set up logger
logger = get_logger(__name__)

def process_security_event(db_session: Session, event_data: Dict[str, Any]) -> Tuple[Event, SecurityAlert]:
    """
    Process a security event and create a SecurityAlert instance.
    
    Args:
        db_session: Database session
        event_data: The event data from the telemetry API
        
    Returns:
        Event, SecurityAlert: The created event and security alert
    """
    logger.info(f"Processing security event: {event_data.get('name')}")
    
    try:
        # Parse timestamp if needed
        timestamp = event_data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        elif timestamp is None:
            timestamp = datetime.utcnow()
        
        # Get or create the agent first to avoid foreign key constraint issues
        agent_id = event_data.get("agent_id")
        if not agent_id:
            logger.error("Missing agent_id in security event data")
            raise ValueError("Missing agent_id in security event data")
            
        # Check if agent exists - IMPORTANT: use agent_id, not id
        agent = db_session.query(Agent).filter(Agent.agent_id == agent_id).first()
        
        # Create agent if it doesn't exist
        if not agent:
            logger.info(f"Creating new agent with ID: {agent_id}")
            current_time = datetime.utcnow()
            agent = Agent(
                agent_id=agent_id,  # This is the string identifier that will be referenced
                name=agent_id,  # Use agent_id as the name for consistency
                first_seen=current_time,
                last_seen=current_time,
                is_active=True
            )
            db_session.add(agent)
            db_session.flush()  # Flush to generate ID but don't commit yet
            logger.debug(f"Successfully created agent with agent_id={agent_id}, db id={agent.id}")
        else:
            # Update last_seen time
            agent.last_seen = datetime.utcnow()
            # Ensure name matches agent_id for consistency
            if agent.name != agent_id:
                agent.name = agent_id
            db_session.add(agent)
            logger.debug(f"Using existing agent with agent_id={agent_id}, db id={agent.id}")
        
        # Create or find Trace and Span if they exist - CRITICAL to do this BEFORE creating the Event
        trace_id = event_data.get("trace_id")
        span_id = event_data.get("span_id")
        parent_span_id = event_data.get("parent_span_id")
        event_name = event_data.get("name")
        
        if trace_id:
            from src.models.trace import Trace
            trace = db_session.query(Trace).filter(Trace.trace_id == trace_id).first()
            if not trace:
                # Create a new trace
                logger.info(f"Creating new trace with ID: {trace_id}")
                trace = Trace(
                    trace_id=trace_id,
                    agent_id=agent_id,
                    start_timestamp=timestamp,
                    is_complete=False
                )
                db_session.add(trace)
                db_session.flush()
                logger.debug(f"Successfully created trace with trace_id={trace_id}")
        
        if span_id and trace_id:
            from src.models.span import Span
            span = db_session.query(Span).filter(Span.span_id == span_id).first()
            if not span:
                # Create a new span
                logger.info(f"Creating new span with ID: {span_id}")
                span = Span(
                    span_id=span_id,
                    trace_id=trace_id,
                    parent_span_id=parent_span_id,
                    name=event_name,
                    start_timestamp=timestamp
                )
                db_session.add(span)
                db_session.flush()
                logger.debug(f"Successfully created span with span_id={span_id}")
        
        # Create base Event record
        event = Event(
            name=event_data.get("name", "security.unknown"),
            timestamp=timestamp,
            level=event_data.get("level", "SECURITY_ALERT"),
            agent_id=agent_id,
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            schema_version=event_data.get("schema_version", "1.0"),
            event_type="security",
            raw_data=event_data
        )
        
        db_session.add(event)
        db_session.flush()  # Ensure ID is generated
        
        # Create SecurityAlert using the new method
        security_alert = SecurityAlert.from_telemetry_event(db_session, event, event_data)
        
        return event, security_alert
        
    except Exception as e:
        logger.error(f"Error processing security event: {str(e)}", exc_info=True)
        raise ValueError(f"Failed to process security event: {str(e)}")

def verify_security_event(event_data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Verify that the event data is a valid security event.
    
    Args:
        event_data: The event data to verify
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check required fields
    if "name" not in event_data:
        return False, "Missing required field: name"
    
    if "level" not in event_data:
        return False, "Missing required field: level"
    
    if "agent_id" not in event_data:
        return False, "Missing required field: agent_id"
    
    # Check that this is a security event
    event_name = event_data.get("name", "")
    if not event_name.startswith("security.content"):
        return False, f"Not a security event: {event_name}"
    
    # Check for required security attributes
    attributes = event_data.get("attributes", {})
    if not attributes:
        return False, "Missing required field: attributes"
    
    # Verify required security attributes
    if "security.alert_level" not in attributes:
        return False, "Missing required attribute: security.alert_level"
    
    if "security.category" not in attributes:
        return False, "Missing required attribute: security.category"
    
    if "security.severity" not in attributes:
        return False, "Missing required attribute: security.severity"
    
    return True, None 