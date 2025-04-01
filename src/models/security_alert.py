"""
Security Alert model and related functionality.

This module defines the SecurityAlert model for storing security-related events
and the SecurityAlertTrigger model for connecting events with the alerts they triggered.
"""
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Set, Union, Tuple

from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, Text, DateTime, Table, JSON
from sqlalchemy.orm import relationship

from src.models.base import Base


class SecurityAlert(Base):
    """
    Security Alert model for storing security-related events.
    
    This model captures information about security events detected by the monitoring system,
    including alert type, severity, description, and metadata.
    """
    __tablename__ = "security_alerts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, unique=True, index=True)
    
    alert_type = Column(String, nullable=False, index=True)  # 'prompt_injection', 'data_leak', etc.
    severity = Column(String, nullable=False, index=True)  # 'low', 'medium', 'high', 'critical'
    description = Column(Text, nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    status = Column(String, index=True, default="OPEN")  # 'OPEN', 'INVESTIGATING', 'RESOLVED', 'FALSE_POSITIVE'
    resolved_at = Column(DateTime)
    resolution_notes = Column(Text)
    
    context = Column(Text)  # JSON field for context information
    
    # Extracted attribute fields for better querying
    detection_source = Column(String, index=True)
    confidence_score = Column(Float)
    risk_level = Column(String, index=True)
    affected_component = Column(String, index=True)
    detection_rule_id = Column(String, index=True)
    
    # Raw attributes JSON storage for complete data
    raw_attributes = Column(JSON)
    
    # Relationships
    event = relationship("Event", back_populates="security_alert")
    triggered_by = relationship("SecurityAlertTrigger", back_populates="alert")
    
    def __repr__(self) -> str:
        return f"<SecurityAlert {self.id} ({self.alert_type}, {self.severity})>"
    
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
        # If telemetry_data is provided, use the method with telemetry support
        if telemetry_data:
            return cls.from_event_with_telemetry(db_session, event, telemetry_data)
            
        # Original implementation for backward compatibility
        if not event.data:
            raise ValueError("Event data is required to create a security alert")
            
        try:
            event_data = json.loads(event.data)
        except json.JSONDecodeError:
            raise ValueError("Event data must be valid JSON")
            
        payload = event_data.get("payload", {})
        
        # Use payload values directly instead of deriving from event name
        alert_type = payload.get("alert_type", "unknown")
        alert_severity = payload.get("severity", "unknown")
            
        # Extract attributes
        attributes = payload.get("attributes", {})
        
        # Create security alert
        security_alert = cls(
            event_id=event.id,
            alert_type=alert_type,
            severity=alert_severity,
            description=payload.get("description", "No description provided"),
            context=json.dumps(payload.get("context")) if payload.get("context") else None,
            status="OPEN",  # Set default status to OPEN
            raw_attributes=attributes,  # Store raw attributes
            
            # Extract known attributes to dedicated columns
            detection_source=attributes.get("detection_source", payload.get("detection_source")),
            confidence_score=attributes.get("confidence_score", payload.get("confidence_score")),
            risk_level=attributes.get("risk_level", payload.get("risk_level")),
            affected_component=attributes.get("affected_component", payload.get("affected_component")),
            detection_rule_id=attributes.get("detection_rule_id", payload.get("detection_rule_id"))
        )
        
        db_session.add(security_alert)
        
        # Create SecurityAlertTrigger records if triggering events are specified
        if "triggering_events" in payload and isinstance(payload["triggering_events"], list):
            for triggering_event_id in payload["triggering_events"]:
                trigger = SecurityAlertTrigger(
                    alert_id=security_alert.id,
                    triggering_event_id=triggering_event_id
                )
                db_session.add(trigger)
        
        return security_alert
    
    @classmethod
    def from_event_with_telemetry(cls, db_session, event, telemetry_data: Dict[str, Any]) -> "SecurityAlert":
        """
        Create a SecurityAlert from an event with telemetry data.
        
        Args:
            db_session: Database session
            event: The parent Event object
            telemetry_data: Telemetry data dictionary
            
        Returns:
            SecurityAlert: The created security alert
        """
        attributes = telemetry_data.get('attributes', {})
        
        # Extract timestamp
        timestamp = attributes.get("timestamp") or event.timestamp or datetime.utcnow()
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        
        # Create security alert
        security_alert = cls(
            event_id=event.id,
            alert_type=attributes.get("alert_type", "unknown"),
            severity=attributes.get("severity", "MEDIUM"),
            description=attributes.get("description", "No description provided"),
            timestamp=timestamp,
            status="OPEN",
            context=json.dumps(attributes.get("context")) if attributes.get("context") else None,
            raw_attributes=attributes,  # Store raw attributes
            
            # Extract known attributes to dedicated columns
            detection_source=attributes.get("detection_source") or attributes.get("security.detection_source"),
            confidence_score=attributes.get("confidence_score") or attributes.get("security.confidence_score"),
            risk_level=attributes.get("risk_level") or attributes.get("security.risk_level"),
            affected_component=attributes.get("affected_component") or attributes.get("security.affected_component"),
            detection_rule_id=attributes.get("detection_rule_id") or attributes.get("security.detection_rule_id")
        )
        
        db_session.add(security_alert)
        
        # Create SecurityAlertTrigger records if triggering events are specified
        if "triggering_events" in attributes and isinstance(attributes["triggering_events"], list):
            for triggering_event_id in attributes["triggering_events"]:
                trigger = SecurityAlertTrigger(
                    alert_id=security_alert.id,
                    triggering_event_id=triggering_event_id
                )
                db_session.add(trigger)
        
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
    
    def get_context_dict(self) -> Optional[Dict[str, Any]]:
        """
        Get the context as a dictionary.
        
        Returns:
            Dict or None: The context as a dictionary or None if not available
        """
        if not self.context:
            return None
            
        try:
            return json.loads(self.context)
        except json.JSONDecodeError:
            return None
    
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
    
    def get_triggering_events(self, db_session) -> List["Event"]:
        """
        Get all events that triggered this alert.
        
        Args:
            db_session: Database session
            
        Returns:
            List[Event]: List of events that triggered this alert
        """
        from src.models.event import Event
        
        triggers = db_session.query(SecurityAlertTrigger).filter(
            SecurityAlertTrigger.alert_id == self.id
        ).all()
        
        event_ids = [trigger.triggering_event_id for trigger in triggers]
        
        return db_session.query(Event).filter(Event.id.in_(event_ids)).all()
    
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
        
        # Find all open alerts for events belonging to this agent
        return db_session.query(cls).join(
            Event, cls.event_id == Event.id
        ).filter(
            Event.agent_id == agent_id,
            cls.status == "OPEN"
        ).all()


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