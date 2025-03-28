"""
Session model and related functionality.

This module defines the Session model for representing user interaction sessions
with agents, including session start/end and related telemetry.
"""
from datetime import datetime
from typing import Dict, Any, List, Optional
import uuid

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship

from src.models.base import Base


class Session(Base):
    """
    Session model representing a user interaction session with an agent.
    
    A session represents a continuous period of user interaction with an agent.
    Sessions have a start time, optional end time, and can contain many events.
    """
    __tablename__ = "sessions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(String, ForeignKey("agents.agent_id"), nullable=False, index=True)
    session_id = Column(String, unique=True, nullable=False, index=True)
    
    start_timestamp = Column(DateTime, nullable=False)
    end_timestamp = Column(DateTime)
    
    # Relationships
    agent = relationship("Agent", back_populates="sessions")
    events = relationship("Event", back_populates="session")
    
    def __repr__(self) -> str:
        return f"<Session {self.id} ({self.session_id})>"
    
    @classmethod
    def get_or_create(cls, db_session, session_id: str, agent_id: str) -> "Session":
        """
        Get an existing session or create a new one if it doesn't exist.
        
        Args:
            db_session: Database session
            session_id: Unique identifier for the session
            agent_id: ID of the parent agent
            
        Returns:
            Session: The retrieved or created session
        """
        session = db_session.query(cls).filter(cls.session_id == session_id).first()
        
        if session:
            return session
        
        # Create a new session if it doesn't exist
        session = cls(
            session_id=session_id,
            agent_id=agent_id,
            start_timestamp=datetime.utcnow()
        )
        
        db_session.add(session)
        return session
    
    @classmethod
    def generate_session_id(cls) -> str:
        """
        Generate a unique session ID.
        
        Returns:
            str: A unique session ID
        """
        return str(uuid.uuid4())
    
    def end_session(self, db_session, end_timestamp: Optional[datetime] = None) -> None:
        """
        End the session.
        
        Args:
            db_session: Database session
            end_timestamp: Optional end timestamp (default: current time)
        """
        if self.end_timestamp is None:
            self.end_timestamp = end_timestamp or datetime.utcnow()
            db_session.add(self)
    
    def get_duration_seconds(self) -> Optional[float]:
        """
        Get the duration of the session in seconds.
        
        Returns:
            float or None: The duration in seconds, or None if the session hasn't ended
        """
        if self.end_timestamp is None:
            return None
        
        return (self.end_timestamp - self.start_timestamp).total_seconds()
    
    def get_event_count(self, db_session) -> int:
        """
        Get the total number of events in the session.
        
        Args:
            db_session: Database session
            
        Returns:
            int: The total number of events
        """
        from src.models.event import Event
        
        return db_session.query(func.count(Event.id)).filter(
            Event.session_id == self.id
        ).scalar() or 0
    
    def get_events_by_type(self, db_session, event_type: str) -> List["Event"]:
        """
        Get events in the session of a specific type.
        
        Args:
            db_session: Database session
            event_type: The type of events to retrieve
            
        Returns:
            List[Event]: Events of the specified type
        """
        from src.models.event import Event
        
        return db_session.query(Event).filter(
            Event.session_id == self.id,
            Event.event_type == event_type
        ).order_by(Event.timestamp).all()
    
    def get_traces(self, db_session) -> List["Trace"]:
        """
        Get all traces that contain events from this session.
        
        Args:
            db_session: Database session
            
        Returns:
            List[Trace]: Traces containing events from this session
        """
        from src.models.trace import Trace
        from src.models.event import Event
        
        # Get unique trace_ids for this session
        trace_ids_query = db_session.query(Event.trace_id).filter(
            Event.session_id == self.id,
            Event.trace_id.isnot(None)
        ).distinct()
        
        trace_ids = [result[0] for result in trace_ids_query.all()]
        
        if not trace_ids:
            return []
            
        # Get all traces with those trace_ids
        return db_session.query(Trace).filter(
            Trace.trace_id.in_(trace_ids)
        ).all()
    
    def get_statistics(self, db_session) -> Dict[str, Any]:
        """
        Get statistics about the session.
        
        Args:
            db_session: Database session
            
        Returns:
            Dict: Statistics about the session
        """
        from src.models.event import Event
        
        event_count = self.get_event_count(db_session)
        
        # Get event counts by type
        event_types_query = db_session.query(
            Event.event_type, func.count(Event.id)
        ).filter(
            Event.session_id == self.id
        ).group_by(Event.event_type)
        
        event_types = {event_type: count for event_type, count in event_types_query.all()}
        
        # Get trace count
        traces = self.get_traces(db_session)
        
        return {
            "event_count": event_count,
            "event_types": event_types,
            "trace_count": len(traces),
            "start_timestamp": self.start_timestamp,
            "end_timestamp": self.end_timestamp,
            "duration_seconds": self.get_duration_seconds()
        } 