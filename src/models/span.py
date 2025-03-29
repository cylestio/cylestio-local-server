"""
Span model and related functionality.

This module defines the Span model representing individual operations within a trace.
"""
from datetime import datetime
from typing import Optional, List

from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from models.base import Base


class Span(Base):
    """
    Span model representing individual operations within a trace.
    
    Spans represent discrete operations that can have parent-child relationships,
    forming a tree of operations within a trace.
    """
    __tablename__ = "spans"
    
    span_id = Column(String, primary_key=True, index=True)
    trace_id = Column(String, ForeignKey("traces.trace_id"), nullable=False, index=True)
    parent_span_id = Column(String, index=True)
    name = Column(String)
    start_timestamp = Column(DateTime, index=True)
    end_timestamp = Column(DateTime, index=True)
    
    # Relationships
    trace = relationship("Trace", back_populates="spans")
    events = relationship("Event", back_populates="span", foreign_keys="Event.span_id")
    
    def __repr__(self) -> str:
        return f"<Span {self.span_id}>"
    
    @classmethod
    def get_or_create(cls, db_session, span_id: str, trace_id: str, 
                    parent_span_id: Optional[str] = None, name: Optional[str] = None) -> "Span":
        """
        Get an existing span or create a new one if it doesn't exist.
        
        Args:
            db_session: Database session
            span_id: Unique identifier for the span
            trace_id: ID of the trace this span belongs to
            parent_span_id: ID of the parent span (optional)
            name: Name of the span (optional)
            
        Returns:
            Span: The retrieved or newly created span
        """
        span = db_session.query(cls).filter(cls.span_id == span_id).first()
        
        if span:
            return span
        
        # Create new span
        span = cls(
            span_id=span_id,
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            name=name,
            start_timestamp=datetime.now()
        )
        db_session.add(span)
        return span
    
    def update_timestamps(self, db_session, start_time: Optional[datetime] = None,
                        end_time: Optional[datetime] = None) -> None:
        """
        Update the start and/or end timestamps for this span.
        
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
        Get the duration of this span in seconds.
        
        Returns:
            float: Duration in seconds, or None if timestamps are not set
        """
        if not self.start_timestamp or not self.end_timestamp:
            return None
        
        delta = self.end_timestamp - self.start_timestamp
        return delta.total_seconds()
    
    def get_child_spans(self, db_session) -> List["Span"]:
        """
        Get all child spans of this span.
        
        Args:
            db_session: Database session
            
        Returns:
            List[Span]: Child spans
        """
        return db_session.query(Span).filter(
            Span.parent_span_id == self.span_id
        ).all()
    
    def get_event_count(self, db_session) -> int:
        """
        Get the total number of events associated with this span.
        
        Args:
            db_session: Database session
            
        Returns:
            int: Number of events
        """
        from models.event import Event
        return db_session.query(Event).filter(Event.span_id == self.span_id).count()
    
    def get_span_tree(self, db_session) -> List["Span"]:
        """
        Get the entire span tree rooted at this span.
        
        Args:
            db_session: Database session
            
        Returns:
            List[Span]: All spans in the tree
        """
        def get_descendants(span_id):
            children = db_session.query(Span).filter(Span.parent_span_id == span_id).all()
            result = list(children)
            for child in children:
                result.extend(get_descendants(child.span_id))
            return result
        
        return [self] + get_descendants(self.span_id) 