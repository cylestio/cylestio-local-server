"""
Session model and related functionality.

This module defines the Session model for representing user interaction sessions
with agents, including session start/end and related telemetry.
"""
from datetime import datetime, timedelta
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
    
    def __init__(self, **kwargs):
        """
        Initialize a new Session instance.
        
        This custom initializer ensures that start_timestamp and end_timestamp
        maintain proper chronology.
        """
        # Call the parent initializer with kwargs
        super().__init__(**kwargs)
        
        # Check for timestamp inversion and fix if needed
        if (self.start_timestamp is not None and self.end_timestamp is not None and 
                self.start_timestamp > self.end_timestamp):
            # Fix the inversion - set both to the same value (the latest timestamp)
            latest_timestamp = max(self.start_timestamp, self.end_timestamp)
            self.start_timestamp = latest_timestamp
            self.end_timestamp = latest_timestamp
    
    @classmethod
    def get_or_create(cls, db_session, session_id: str, agent_id: str, initialize_end_timestamp: bool = False) -> "Session":
        """
        Get an existing session or create a new one if it doesn't exist.
        
        Args:
            db_session: Database session
            session_id: Unique identifier for the session
            agent_id: ID of the parent agent
            initialize_end_timestamp: Whether to initialize end_timestamp to the same value as start_timestamp
            
        Returns:
            Session: The retrieved or created session
        """
        session = db_session.query(cls).filter(cls.session_id == session_id).first()
        
        if session:
            return session
        
        # Create a new session if it doesn't exist
        current_time = datetime.utcnow()
        
        # Create the session with or without initializing end_timestamp
        if initialize_end_timestamp:
            session = cls(
                session_id=session_id,
                agent_id=agent_id,
                start_timestamp=current_time,
                end_timestamp=None  # Initialize as None, will be set by event timestamps
            )
        else:
            # Original behavior for backward compatibility
            session = cls(
                session_id=session_id,
                agent_id=agent_id,
                start_timestamp=current_time
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
            self.end_timestamp = end_timestamp or datetime.utcnow() + timedelta(hours=2)
            db_session.add(self)
    
    @property
    def duration_seconds(self) -> Optional[float]:
        """
        Get the duration of the session in seconds.
        
        Returns:
            float or None: The duration in seconds, or None if the session hasn't ended
        """
        if self.end_timestamp is None or self.start_timestamp is None:
            return None
        
        if self.start_timestamp > self.end_timestamp:
            # This should not happen with the fixes in place, but just in case
            return 0.0
            
        return (self.end_timestamp - self.start_timestamp).total_seconds()
    
    def update_end_timestamp(self, db_session, timestamp: datetime) -> None:
        """
        Update the session's end timestamp if the provided timestamp is more recent.
        
        Args:
            db_session: Database session
            timestamp: The timestamp to update to
        """
        # Make timestamps comparable (both naive or both aware)
        session_end = self.end_timestamp
        
        # Make timestamps timezone-naive for comparison if needed
        if hasattr(timestamp, 'tzinfo') and timestamp.tzinfo is not None:
            # Timestamp is timezone-aware, make it naive for comparison
            compare_timestamp = timestamp.replace(tzinfo=None)
        else:
            compare_timestamp = timestamp
            
        # Set the end timestamp if it doesn't exist or if the new timestamp is later
        if session_end is None or compare_timestamp > session_end:
            self.end_timestamp = timestamp
            db_session.add(self)
    
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
            "duration_seconds": self.duration_seconds
        }
    
    def get_events_sorted(self, db_session) -> List["Event"]:
        """
        Get all events in the session sorted by timestamp.
        
        Args:
            db_session: Database session
            
        Returns:
            List[Event]: Events sorted by timestamp
        """
        from src.models.event import Event
        
        return db_session.query(Event).filter(
            Event.session_id == self.session_id
        ).order_by(Event.timestamp).all()
    
    def get_status(self, inactive_threshold_minutes: int = 30) -> str:
        """
        Get the session status based on how recent the last activity was.
        
        Args:
            inactive_threshold_minutes: Number of minutes after which a session is considered inactive
            
        Returns:
            str: 'active' if the session has recent activity, 'closed' otherwise
        """
        if self.end_timestamp is None:
            return "active"
            
        # Calculate the difference between now and the last activity
        time_since_last_activity = datetime.utcnow() - self.end_timestamp
        
        # Convert to minutes
        minutes_since_last_activity = time_since_last_activity.total_seconds() / 60
        
        # Return status based on threshold
        if minutes_since_last_activity <= inactive_threshold_minutes:
            return "active"
        else:
            return "closed" 