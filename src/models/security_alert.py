"""
Security Alert model and related functionality.

This module defines the SecurityAlert model for storing security-related events
in the OpenTelemetry-compliant format with additional security metrics.
"""
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Set, Union, Tuple

from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, Text, DateTime, Table, JSON
from sqlalchemy.orm import relationship

from src.models.base import Base


class SecurityAlert(Base):
    """
    Security Alert model for storing security-related events in OpenTelemetry format.
    
    This model captures comprehensive information about security events detected by
    the monitoring system to enable detailed analysis and investigation.
    """
    __tablename__ = "security_alerts"
    
    # Core identification fields
    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, unique=True, index=True)
    
    # OpenTelemetry core fields
    schema_version = Column(String, nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True, default=datetime.utcnow)
    trace_id = Column(String, index=True)
    span_id = Column(String, index=True)
    parent_span_id = Column(String, nullable=True)
    event_name = Column(String, index=True)  # Format: security.content.<alert_level>
    log_level = Column(String, index=True)   # INFO, WARNING, SECURITY_ALERT, CRITICAL
    
    # Security-specific attributes
    alert_level = Column(String, nullable=False, index=True)  # none, suspicious, dangerous, critical
    category = Column(String, nullable=False, index=True)     # sensitive_data, prompt_injection, etc.
    severity = Column(String, nullable=False, index=True)     # low, medium, high, critical
    description = Column(Text, nullable=False)
    
    # Additional security context
    llm_vendor = Column(String, index=True)  # openai, anthropic, etc.
    content_sample = Column(Text)            # Masked sample of content
    detection_time = Column(DateTime, index=True)
    keywords = Column(JSON)                  # List of detected patterns with masked values
    
    # Status tracking fields (kept from original model)
    status = Column(String, index=True, default="OPEN")  # 'OPEN', 'INVESTIGATING', 'RESOLVED', 'FALSE_POSITIVE'
    resolved_at = Column(DateTime)
    resolution_notes = Column(Text)
    
    # Complete data storage
    raw_attributes = Column(JSON)  # Store full attributes for future analysis
    
    # Relationships
    event = relationship("Event", back_populates="security_alert")
    
    # Many-to-many relationship to connect events that triggered this alert
    triggered_by = relationship("SecurityAlertTrigger", back_populates="alert")
    
    def __repr__(self) -> str:
        return f"<SecurityAlert {self.id} ({self.category}, {self.severity}, {self.alert_level})>"
    
    @classmethod
    def from_event(cls, db_session, event, telemetry_data=None) -> "SecurityAlert":
        """
        Create a SecurityAlert from an event.
        
        Args:
            db_session: Database session
            event: The parent Event object
            telemetry_data: Optional telemetry data dictionary
            
        Returns:
            SecurityAlert: The created security alert
        """
        # Always use new telemetry format
        if not telemetry_data and event.raw_data:
            telemetry_data = event.raw_data
            
        if not telemetry_data:
            raise ValueError("Telemetry data is required to create a security alert")
        
        attributes = telemetry_data.get('attributes', {})
        
        # Extract timestamps
        detection_time = None
        if attributes.get("security.detection_time"):
            detection_time = attributes.get("security.detection_time")
            if isinstance(detection_time, str):
                detection_time = datetime.fromisoformat(detection_time.replace('Z', '+00:00'))
        
        event_timestamp = telemetry_data.get('timestamp') or event.timestamp or datetime.utcnow()
        if isinstance(event_timestamp, str):
            event_timestamp = datetime.fromisoformat(event_timestamp.replace('Z', '+00:00'))
        
        # Map OpenTelemetry fields to model fields
        security_alert = cls(
            event_id=event.id,
            
            # OpenTelemetry core fields
            schema_version=telemetry_data.get('schema_version', '1.0'),
            timestamp=event_timestamp,
            trace_id=telemetry_data.get('trace_id'),
            span_id=telemetry_data.get('span_id'),
            parent_span_id=telemetry_data.get('parent_span_id'),
            event_name=telemetry_data.get('name'),
            log_level=telemetry_data.get('level'),
            
            # Security-specific attributes
            alert_level=attributes.get('security.alert_level', 'none'),
            category=attributes.get('security.category', 'unknown'),
            severity=attributes.get('security.severity', 'low'),
            description=attributes.get('security.description', 'No description provided'),
            
            # Additional security context
            llm_vendor=attributes.get('llm.vendor'),
            content_sample=attributes.get('security.content_sample'),
            detection_time=detection_time or event_timestamp,
            keywords=attributes.get('security.keywords'),
            
            # Status tracking (defaults)
            status="OPEN",
            
            # Complete data storage
            raw_attributes=attributes
        )
        
        db_session.add(security_alert)
        return security_alert
    
    @classmethod
    def from_telemetry_event(cls, db_session, event, telemetry_data: Dict[str, Any]) -> "SecurityAlert":
        """
        Create a SecurityAlert from an OpenTelemetry security event.
        
        Args:
            db_session: Database session
            event: The parent Event object
            telemetry_data: OpenTelemetry event data
            
        Returns:
            SecurityAlert: The created security alert
        """
        # Extract core OpenTelemetry fields
        schema_version = telemetry_data.get("schema_version", "1.0")
        trace_id = telemetry_data.get("trace_id")
        span_id = telemetry_data.get("span_id")
        parent_span_id = telemetry_data.get("parent_span_id")
        event_name = telemetry_data.get("name")
        log_level = telemetry_data.get("level", "INFO")
        
        # Extract timestamp
        timestamp_str = telemetry_data.get("timestamp")
        timestamp = None
        if timestamp_str:
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            except (ValueError, TypeError):
                timestamp = datetime.utcnow()
        else:
            timestamp = event.timestamp or datetime.utcnow()
        
        # Extract security-specific attributes
        attributes = telemetry_data.get('attributes', {})
        
        alert_level = attributes.get("security.alert_level", "none")
        category = attributes.get("security.category", "unknown")
        severity = attributes.get("security.severity", "low")
        description = attributes.get("security.description", "No description provided")
        llm_vendor = attributes.get("llm.vendor")
        content_sample = attributes.get("security.content_sample")
        detection_time_str = attributes.get("security.detection_time")
        keywords = attributes.get("security.keywords", [])
        
        # Parse detection time
        detection_time = None
        if detection_time_str:
            try:
                detection_time = datetime.fromisoformat(detection_time_str.replace('Z', '+00:00'))
            except (ValueError, TypeError):
                detection_time = timestamp
        
        # Create security alert
        security_alert = cls(
            event_id=event.id,
            schema_version=schema_version,
            timestamp=timestamp,
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            event_name=event_name,
            log_level=log_level,
            alert_level=alert_level,
            category=category,
            severity=severity,
            description=description,
            llm_vendor=llm_vendor,
            content_sample=content_sample,
            detection_time=detection_time,
            keywords=keywords,
            raw_attributes=attributes
        )
        
        db_session.add(security_alert)
        db_session.flush()  # Ensure the ID is generated
        
        return security_alert
    
    def resolve(self, resolution_notes: str, resolved_at: Optional[datetime] = None) -> None:
        """
        Resolve the security alert.
        
        Args:
            resolution_notes: Notes about the resolution
            resolved_at: When the alert was resolved (default: current time)
        """
        self.status = "RESOLVED"
        self.resolved_at = resolved_at or datetime.utcnow()
        self.resolution_notes = resolution_notes
    
    def mark_as_false_positive(self, notes: str, resolved_at: Optional[datetime] = None) -> None:
        """
        Mark the security alert as a false positive.
        
        Args:
            notes: Notes about why this is a false positive
            resolved_at: When the alert was resolved (default: current time)
        """
        self.status = "FALSE_POSITIVE"
        self.resolved_at = resolved_at or datetime.utcnow()
        self.resolution_notes = notes
    
    def get_attribute(self, key: str, default: Any = None) -> Any:
        """
        Get an attribute value by key.
        
        Args:
            key: Attribute key
            default: Default value if attribute not found
            
        Returns:
            Attribute value or default
        """
        if not self.raw_attributes:
            return default
            
        return self.raw_attributes.get(key, default)
    
    @classmethod
    def find_by_trace(cls, db_session, trace_id: str) -> List["SecurityAlert"]:
        """
        Find all security alerts for a specific trace.
        
        Args:
            db_session: Database session
            trace_id: The trace ID to search for
            
        Returns:
            List[SecurityAlert]: List of security alerts for the trace
        """
        return db_session.query(cls).filter(cls.trace_id == trace_id).all()
    
    @classmethod
    def find_related_by_span(cls, db_session, span_id: str) -> List["SecurityAlert"]:
        """
        Find security alerts related to a specific span.
        
        This includes both alerts with the exact span_id and those where this span
        is the parent_span_id.
        
        Args:
            db_session: Database session
            span_id: The span ID to search for
            
        Returns:
            List[SecurityAlert]: List of related security alerts
        """
        return db_session.query(cls).filter(
            (cls.span_id == span_id) | (cls.parent_span_id == span_id)
        ).all()
    
    @classmethod
    def open_alerts_for_agent(cls, db_session, agent_id: str) -> List["SecurityAlert"]:
        """
        Get all open alerts for an agent.
        
        Args:
            db_session: Database session
            agent_id: ID of the agent
            
        Returns:
            List[SecurityAlert]: List of open alerts for the agent
        """
        from src.models.event import Event
        
        return db_session.query(cls).join(Event).filter(
            Event.agent_id == agent_id,
            cls.status == "OPEN"
        ).order_by(cls.timestamp.desc()).all()
    
    @classmethod
    def alerts_by_category(cls, db_session, timeframe_days: int = 7) -> Dict[str, int]:
        """
        Get counts of alerts by category within a specific timeframe.
        
        Args:
            db_session: Database session
            timeframe_days: Number of days to look back
            
        Returns:
            Dict[str, int]: Dictionary mapping categories to alert counts
        """
        from sqlalchemy import func
        from datetime import timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=timeframe_days)
        
        result = db_session.query(
            cls.category, func.count(cls.id)
        ).filter(
            cls.timestamp >= cutoff_date
        ).group_by(
            cls.category
        ).all()
        
        return {category: count for category, count in result}
    
    @classmethod
    def alerts_by_severity(cls, db_session, timeframe_days: int = 7) -> Dict[str, int]:
        """
        Get counts of alerts by severity within a specific timeframe.
        
        Args:
            db_session: Database session
            timeframe_days: Number of days to look back
            
        Returns:
            Dict[str, int]: Dictionary mapping severity levels to alert counts
        """
        from sqlalchemy import func
        from datetime import timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=timeframe_days)
        
        result = db_session.query(
            cls.severity, func.count(cls.id)
        ).filter(
            cls.timestamp >= cutoff_date
        ).group_by(
            cls.severity
        ).all()
        
        return {severity: count for severity, count in result}


class SecurityAlertTrigger(Base):
    """
    Security Alert Trigger model for connecting events with the alerts they triggered.
    
    This model represents the many-to-many relationship between security alerts
    and the events that triggered them.
    """
    __tablename__ = "security_alert_triggers"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_id = Column(Integer, ForeignKey("security_alerts.id"), nullable=False, index=True)
    triggering_event_id = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)
    
    # Relationships
    alert = relationship("SecurityAlert", back_populates="triggered_by")
    triggering_event = relationship("Event", back_populates="triggered_alerts")
    
    def __repr__(self) -> str:
        return f"<SecurityAlertTrigger {self.id} (Alert: {self.alert_id}, Event: {self.triggering_event_id})>"
    
    @staticmethod
    def create_from_event_match(db_session, alert_event, triggering_event) -> "SecurityAlertTrigger":
        """
        Create a trigger relationship between an alert and an event that triggered it.
        
        Args:
            db_session: Database session
            alert_event: The security alert event
            triggering_event: The event that triggered the alert
            
        Returns:
            SecurityAlertTrigger: The created trigger relationship
        """
        from src.models.event import Event
        
        # Make sure we have an Event object for each
        if not isinstance(alert_event, Event):
            alert_event = db_session.query(Event).filter(Event.id == alert_event).first()
            
        if not isinstance(triggering_event, Event):
            triggering_event = db_session.query(Event).filter(Event.id == triggering_event).first()
            
        # Create and return the trigger
        trigger = SecurityAlertTrigger(
            alert_id=alert_event.id,
            triggering_event_id=triggering_event.id
        )
        
        db_session.add(trigger)
        return trigger
        
    @staticmethod
    def find_matching_events(db_session, alert: "SecurityAlert") -> List["Event"]:
        """
        Find events that match the conditions of a security alert.
        
        Args:
            db_session: Database session
            alert: The security alert to match against
            
        Returns:
            List[Event]: Events that match the alert conditions
        """
        from src.models.event import Event
        
        # Basic query for all events in the same trace
        query = db_session.query(Event).filter(
            Event.trace_id == alert.event.trace_id
        )
        
        # Add time range filter
        if alert.event.timestamp:
            # All events before the alert
            query = query.filter(Event.timestamp <= alert.event.timestamp)
            
        return query.all() 