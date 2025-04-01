"""
Trace model for distributed tracing.

This module defines the Trace model, which represents a single trace in a
distributed tracing system. A trace contains multiple spans that together
represent a complete request or operation.
"""
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
import uuid

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship

from src.models.base import Base


class Trace(Base):
    """
    Trace model representing a group of related operations identified by trace_id.
    
    Traces connect events that are part of the same operation sequence.
    """
    __tablename__ = "traces"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    trace_id = Column(String, unique=True, nullable=False, index=True)
    agent_id = Column(String, ForeignKey("agents.agent_id"), nullable=False, index=True)
    start_timestamp = Column(DateTime, index=True)
    end_timestamp = Column(DateTime, index=True)
    
    # Relationships
    agent = relationship("Agent", back_populates="traces")
    events = relationship("Event", back_populates="trace", cascade="all, delete-orphan")
    spans = relationship("Span", back_populates="trace", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Trace {self.trace_id}>"
    
    @classmethod
    def get_or_create(cls, db_session, trace_id: str, agent_id: str) -> "Trace":
        """
        Get an existing trace or create a new one if it doesn't exist.
        
        Args:
            db_session: Database session
            trace_id: Unique identifier for the trace
            agent_id: ID of the agent associated with this trace
            
        Returns:
            Trace: The retrieved or newly created trace
        """
        trace = db_session.query(cls).filter(cls.trace_id == trace_id).first()
        
        if trace:
            return trace
        
        # Create new trace
        trace = cls(
            trace_id=trace_id,
            agent_id=agent_id,
            start_timestamp=datetime.now()
        )
        db_session.add(trace)
        return trace
    
    def update_timestamps(self, db_session, start_time: Optional[datetime] = None,
                        end_time: Optional[datetime] = None) -> None:
        """
        Update the start and/or end timestamps for this trace.
        
        Args:
            db_session: Database session
            start_time: Start timestamp (optional)
            end_time: End timestamp (optional)
        """
        if start_time and (not self.start_timestamp or start_time < self.start_timestamp):
            self.start_timestamp = start_time
            
        if end_time and (not self.end_timestamp or end_time > self.end_timestamp):
            self.end_timestamp = end_time
            
        db_session.add(self)
    
    def get_duration_seconds(self) -> Optional[float]:
        """
        Get the duration of this trace in seconds.
        
        Returns:
            float: Duration in seconds, or None if timestamps are not set
        """
        if not self.start_timestamp or not self.end_timestamp:
            return None
        
        delta = self.end_timestamp - self.start_timestamp
        return delta.total_seconds()
    
    def get_event_count(self, db_session) -> int:
        """
        Get the number of events associated with this trace.
        
        Args:
            db_session: Database session
            
        Returns:
            int: The number of events
        """
        from src.models.event import Event
        
        return db_session.query(func.count(Event.id)).filter(
            Event.trace_id == self.trace_id
        ).scalar() or 0
    
    def get_span_count(self, db_session) -> int:
        """
        Get the number of spans in this trace.
        
        Args:
            db_session: Database session
            
        Returns:
            int: The number of spans
        """
        from src.models.span import Span
        
        return db_session.query(func.count(Span.id)).filter(
            Span.trace_id == self.trace_id
        ).scalar() or 0
    
    def get_root_spans(self, db_session) -> List["Span"]:
        """
        Get the root spans (spans without parents) in this trace.
        
        Args:
            db_session: Database session
            
        Returns:
            List[Span]: The root spans
        """
        from src.models.span import Span
        
        return db_session.query(Span).filter(
            Span.trace_id == self.trace_id,
            Span.parent_span_id.is_(None)
        ).all() 