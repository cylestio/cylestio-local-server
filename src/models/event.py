"""
Event model for telemetry events.

This module defines the Event model for storing telemetry events received
from agents.
"""
from datetime import datetime
from typing import Dict, Any, List, Optional, Type, Union

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index, JSON
from sqlalchemy.orm import relationship

from src.models.base import Base

# Type aliases
EventDict = Dict[str, Any]

class Event(Base):
    """
    Event model for telemetry events.
    
    An event represents a single telemetry event received from an agent. Events
    can be associated with an agent, trace, span, and session, and can have
    specialized event types like LLM interactions, tool interactions, security alerts,
    or framework events.
    """
    __tablename__ = "events"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Basic event properties
    name = Column(String, nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    level = Column(String, nullable=False, index=True)
    
    # Identifiers
    agent_id = Column(String, ForeignKey("agents.agent_id"), nullable=False, index=True)
    trace_id = Column(String, ForeignKey("traces.trace_id"), nullable=True, index=True)
    span_id = Column(String, ForeignKey("spans.span_id"), nullable=True, index=True)
    parent_span_id = Column(String, nullable=True)
    session_id = Column(String, ForeignKey("sessions.session_id"), nullable=True, index=True)
    
    # Schema versioning
    schema_version = Column(String, default="1.0")
    
    # Event type for polymorphic dispatch
    event_type = Column(String, nullable=False, index=True)
    
    # Raw event data
    raw_data = Column(JSON, nullable=True)
    
    # Relationships
    agent = relationship("Agent", back_populates="events")
    trace = relationship("Trace", back_populates="events")
    span = relationship("Span", back_populates="events")
    session = relationship("Session", back_populates="events")
    
    # Specialized event relationships
    llm_interaction = relationship("LLMInteraction", back_populates="event", uselist=False)
    tool_interaction = relationship("ToolInteraction", back_populates="event", uselist=False)
    security_alert = relationship("SecurityAlert", back_populates="event", uselist=False)
    framework_event = relationship("FrameworkEvent", back_populates="event", uselist=False)
    
    # Many-to-many relationship to connect events that trigger security alerts
    triggered_alerts = relationship("SecurityAlertTrigger", back_populates="triggering_event")
    
    # Add indexes for common queries
    __table_args__ = (
        Index("ix_events_timestamp_desc", timestamp.desc()),
        Index("ix_events_agent_timestamp", agent_id, timestamp.desc()),
        Index("ix_events_trace_timestamp", trace_id, timestamp.desc()),
        Index("ix_events_span_timestamp", span_id, timestamp.desc()),
        Index("ix_events_session_timestamp", session_id, timestamp.desc()),
        Index("ix_events_type_timestamp", event_type, timestamp.desc()),
        {"extend_existing": True}
    )
    
    def __repr__(self) -> str:
        return f"<Event {self.id} ({self.name})>"
    
    @property
    def specialized_event(self) -> Optional[Union["LLMInteraction", "ToolInteraction", "SecurityAlert", "FrameworkEvent"]]:
        """
        Get the specialized event associated with this event, if any.
        
        Returns:
            LLMInteraction, ToolInteraction, SecurityAlert, or FrameworkEvent: The specialized event, if any
        """
        if self.event_type == "llm" and self.llm_interaction:
            return self.llm_interaction
        elif self.event_type == "tool" and self.tool_interaction:
            return self.tool_interaction
        elif self.event_type == "security" and self.security_alert:
            return self.security_alert
        elif self.event_type == "framework" and self.framework_event:
            return self.framework_event
        return None
    
    @classmethod
    def from_dict(cls, event_data: EventDict, db_session=None) -> "Event":
        """
        Create an Event from a dictionary of event data.
        
        Args:
            event_data: Dictionary containing event data
            db_session: Optional database session for relationship lookups
            
        Returns:
            Event: The created event
        """
        # Parse timestamp if it's a string
        timestamp = event_data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        
        # Determine event type
        event_name = event_data.get("name", "")
        if event_name.startswith("llm."):
            event_type = "llm"
        elif event_name.startswith("security."):
            event_type = "security"
        elif event_name.startswith("framework."):
            event_type = "framework"
        elif event_name.startswith("tool."):
            event_type = "tool"
        else:
            event_type = "generic"
        
        # Create the base event
        event = cls(
            name=event_data.get("name"),
            timestamp=timestamp,
            level=event_data.get("level"),
            agent_id=event_data.get("agent_id"),
            trace_id=event_data.get("trace_id"),
            span_id=event_data.get("span_id"),
            parent_span_id=event_data.get("parent_span_id"),
            session_id=event_data.get("session_id"),
            schema_version=event_data.get("schema_version", "1.0"),
            event_type=event_type,
            raw_data=event_data
        )
        
        # If db_session is provided, set up relationships
        if db_session:
            from src.models.agent import Agent
            from src.models.session import Session
            from src.models.trace import Trace
            from src.models.span import Span
            
            # Agent (required)
            agent = db_session.query(Agent).filter(Agent.agent_id == event_data.get("agent_id")).first()
            if agent:
                event.agent = agent
            
            # Session (optional)
            if event_data.get("session_id"):
                session = db_session.query(Session).filter(Session.session_id == event_data.get("session_id")).first()
                if session:
                    event.session = session
            
            # Trace (optional)
            if event_data.get("trace_id"):
                trace = db_session.query(Trace).filter(Trace.trace_id == event_data.get("trace_id")).first()
                if trace:
                    event.trace = trace
            
            # Span (optional)
            if event_data.get("span_id"):
                span = db_session.query(Span).filter(Span.span_id == event_data.get("span_id")).first()
                if span:
                    event.span = span
            
            # Create specialized event if needed
            cls._create_specialized_event(event, event_data, db_session)
        
        return event
    
    @staticmethod
    def _create_specialized_event(event: "Event", event_data: EventDict, db_session) -> None:
        """
        Create a specialized event based on the event type.
        
        Args:
            event: The base event
            event_data: Dictionary containing event data
            db_session: Database session
        """
        if event.event_type == "llm":
            from src.models.llm_interaction import LLMInteraction
            specialized = LLMInteraction.from_event(db_session, event, event_data)
            if specialized:
                event.llm_interaction = specialized
        
        elif event.event_type == "tool":
            from src.models.tool_interaction import ToolInteraction
            specialized = ToolInteraction.from_event(db_session, event, event_data)
            if specialized:
                event.tool_interaction = specialized
        
        elif event.event_type == "security":
            from src.models.security_alert import SecurityAlert
            specialized = SecurityAlert.from_event(db_session, event, event_data)
            if specialized:
                event.security_alert = specialized
        
        elif event.event_type == "framework":
            from src.models.framework_event import FrameworkEvent
            specialized = FrameworkEvent.from_event(db_session, event, event_data)
            if specialized:
                event.framework_event = specialized 