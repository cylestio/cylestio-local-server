"""
Span model for tracing.

This module defines the Span model for representing spans in distributed tracing.
Spans are part of a trace and represent a single operation within a trace.
"""
from datetime import datetime
from typing import Dict, Any, List, Optional, Union

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, JSON, func
from sqlalchemy.orm import relationship, Session

from src.models.base import Base


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
    root_span_id = Column(String, index=True)
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
                    parent_span_id: Optional[str] = None, name: Optional[str] = None,
                    event_name: Optional[str] = None) -> "Span":
        """
        Get an existing span or create a new one if it doesn't exist.
        
        Args:
            db_session: Database session
            span_id: Unique identifier for the span
            trace_id: ID of the trace this span belongs to
            parent_span_id: ID of the parent span (optional)
            name: Name of the span (optional)
            event_name: Name of the triggering event (optional, used to derive span name if not provided)
            
        Returns:
            Span: The retrieved or newly created span
        """
        # Ensure all IDs are strings
        span_id_str = str(span_id) if span_id is not None else None
        trace_id_str = str(trace_id) if trace_id is not None else None
        parent_span_id_str = str(parent_span_id) if parent_span_id is not None else None
        
        span = db_session.query(cls).filter(cls.span_id == span_id_str).first()
        
        if span:
            # Update name if provided and the current one is None
            if not span.name and name:
                span.name = name
                db_session.add(span)
            # Derive name from event name if no name provided
            elif not span.name and event_name:
                span.name = cls._derive_span_name_from_event(event_name)
                db_session.add(span)
            return span
        
        # Create new span
        # Derive name from event name if no name provided
        if not name and event_name:
            name = cls._derive_span_name_from_event(event_name)
        
        # Determine root_span_id
        root_span_id = None
        if parent_span_id_str:
            # If this span has a parent, find the parent's root or use parent as root
            parent_span = db_session.query(cls).filter(cls.span_id == parent_span_id_str).first()
            if parent_span:
                root_span_id = parent_span.root_span_id or parent_span.span_id
            else:
                # If parent span not found yet, use parent_span_id as root
                root_span_id = parent_span_id_str
        else:
            # If this span has no parent, it is its own root
            root_span_id = span_id_str
        
        span = cls(
            span_id=span_id_str,
            trace_id=trace_id_str,
            parent_span_id=parent_span_id_str,
            root_span_id=root_span_id,
            name=name,
            start_timestamp=datetime.now()
        )
        db_session.add(span)
        return span
    
    @staticmethod
    def _derive_span_name_from_event(event_name: str) -> str:
        """
        Derive a meaningful span name from an event name.
        
        Args:
            event_name: Name of the event
            
        Returns:
            str: Derived span name
        """
        if not event_name:
            return "unknown_span"
            
        # Extract meaningful span names from event patterns
        if "." in event_name:
            category, action = event_name.split(".", 1)
            if category == "llm" and action.startswith("call"):
                return "llm_interaction"
            elif category == "tool" and action.startswith("call"):
                return "tool_interaction"
            elif category == "framework" and action == "initialization":
                return "framework_initialization"
            elif category == "security":
                return f"security_{action}"
            else:
                return f"{category}_{action}"
        return event_name
    
    def update_timestamps(self, db_session, start_time: Optional[datetime] = None,
                        end_time: Optional[datetime] = None) -> None:
        """
        Update the start and/or end timestamps for this span.
        
        Args:
            db_session: Database session
            start_time: Start timestamp (optional)
            end_time: End timestamp (optional)
        """
        updated = False
        
        if start_time and (not self.start_timestamp or start_time < self.start_timestamp):
            self.start_timestamp = start_time
            updated = True
            
        if end_time and (not self.end_timestamp or end_time > self.end_timestamp):
            self.end_timestamp = end_time
            updated = True
            
        if updated:
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
        from src.models.event import Event
        return db_session.query(Event).filter(Event.span_id == self.span_id).count()
    
    def get_sibling_spans(self, db_session) -> List["Span"]:
        """
        Get all sibling spans (spans with the same parent).
        
        Args:
            db_session: Database session
            
        Returns:
            List[Span]: Sibling spans
        """
        if not self.parent_span_id:
            # For root spans, get other root spans in the same trace
            return db_session.query(Span).filter(
                Span.trace_id == self.trace_id,
                Span.parent_span_id == None,
                Span.span_id != self.span_id
            ).all()
        
        return db_session.query(Span).filter(
            Span.parent_span_id == self.parent_span_id,
            Span.span_id != self.span_id
        ).all()
    
    def get_all_descendants(self, db_session) -> List["Span"]:
        """
        Get all descendant spans (children, grandchildren, etc.).
        
        Args:
            db_session: Database session
            
        Returns:
            List[Span]: All descendant spans
        """
        result = []
        
        children = self.get_child_spans(db_session)
        result.extend(children)
        
        for child in children:
            result.extend(child.get_all_descendants(db_session))
            
        return result
    
    def get_span_tree(self, db_session) -> List["Span"]:
        """
        Get the entire span tree rooted at this span.
        
        Args:
            db_session: Database session
            
        Returns:
            List[Span]: All spans in the tree
        """
        return [self] + self.get_all_descendants(db_session)
    
    def get_first_event_timestamp(self, db_session) -> Optional[datetime]:
        """
        Get the timestamp of the first event in this span.
        
        Args:
            db_session: Database session
            
        Returns:
            datetime: Timestamp of the first event, or None if no events
        """
        from src.models.event import Event
        event = db_session.query(Event).filter(
            Event.span_id == self.span_id
        ).order_by(Event.timestamp.asc()).first()
        
        return event.timestamp if event else None
    
    def get_last_event_timestamp(self, db_session) -> Optional[datetime]:
        """
        Get the timestamp of the last event in this span.
        
        Args:
            db_session: Database session
            
        Returns:
            datetime: Timestamp of the last event, or None if no events
        """
        from src.models.event import Event
        event = db_session.query(Event).filter(
            Event.span_id == self.span_id
        ).order_by(Event.timestamp.desc()).first()
        
        return event.timestamp if event else None
    
    def update_timestamps_from_events(self, db_session) -> None:
        """
        Update span timestamps based on the first and last events in the span.
        
        Args:
            db_session: Database session
        """
        first_timestamp = self.get_first_event_timestamp(db_session)
        last_timestamp = self.get_last_event_timestamp(db_session)
        
        if first_timestamp:
            self.update_timestamps(db_session, start_time=first_timestamp)
            
        if last_timestamp:
            self.update_timestamps(db_session, end_time=last_timestamp)
    
    @staticmethod
    def _get_span_name_from_events(db_session: Session, span_id: str) -> Optional[str]:
        """
        Get the span name from associated events.
        
        Args:
            db_session: Database session
            span_id: The span ID
            
        Returns:
            str or None: The derived span name, if available
        """
        from src.models.event import Event
        
        # Find the earliest event with this span_id
        event = db_session.query(Event).filter(
            Event.span_id == span_id
        ).order_by(Event.timestamp).first()
        
        if not event:
            return None
            
        # Split event name to get a cleaner span name
        event_name = event.name
        
        # Remove any "start", "begin", "end", "finish" suffixes
        suffixes = [".start", ".begin", ".end", ".finish", ".complete", ".stop"]
        for suffix in suffixes:
            if event_name.endswith(suffix):
                return event_name[:-len(suffix)]
                
        return event_name
        
    @staticmethod
    def _get_span_timestamps(db_session: Session, span_id: str) -> Dict[str, Optional[datetime]]:
        """
        Get the earliest and latest timestamp for a span from its events.
        
        Args:
            db_session: Database session
            span_id: The span ID
            
        Returns:
            Dict: The start and end timestamps
        """
        from src.models.event import Event
        
        # Find the earliest and latest events for this span
        earliest_query = db_session.query(func.min(Event.timestamp)).filter(
            Event.span_id == span_id
        )
        
        latest_query = db_session.query(func.max(Event.timestamp)).filter(
            Event.span_id == span_id
        )
        
        earliest = earliest_query.scalar()
        latest = latest_query.scalar()
        
        return {
            "start_time": earliest,
            "end_time": latest
        }
        
    def update_from_events(self, db_session: Session) -> None:
        """
        Update span information from its associated events.
        
        This method updates the span's name, timestamps, and status based on
        the events associated with it.
        
        Args:
            db_session: Database session
        """
        from src.models.event import Event
        
        # ... existing code ... 