"""
Security Alert model and related functionality.

This module defines the SecurityAlert model for storing security-related events
and the SecurityAlertTrigger model for connecting events with the alerts they triggered.
"""
import json
from datetime import datetime
from typing import Dict, Any, List, Optional

from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, Text, DateTime, Table
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
    
    # Relationships
    event = relationship("Event", back_populates="security_alert")
    triggered_by = relationship("SecurityAlertTrigger", back_populates="alert")
    attributes = relationship("SecurityAttribute", back_populates="security_alert", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<SecurityAlert {self.id} ({self.alert_type}, {self.severity})>"
    
    @classmethod
    def from_event(cls, db_session, event) -> "SecurityAlert":
        """
        Create a SecurityAlert from an event.
        
        Args:
            db_session: Database session
            event: The parent Event object
            
        Returns:
            SecurityAlert: The created security alert
        """
        if not event.data:
            raise ValueError("Event data is required to create a security alert")
            
        try:
            event_data = json.loads(event.data)
        except json.JSONDecodeError:
            raise ValueError("Event data must be valid JSON")
            
        payload = event_data.get("payload", {})
        
        # Create security alert
        security_alert = cls(
            event_id=event.id,
            alert_type=payload.get("alert_type", "unknown"),
            severity=payload.get("severity", "MEDIUM"),
            description=payload.get("description", "No description provided"),
            timestamp=event.timestamp or datetime.utcnow(),
            status="OPEN",
            context=json.dumps(payload.get("context")) if payload.get("context") else None
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
    
    # For backward compatibility
    @classmethod
    def from_event_with_telemetry(cls, db_session, event, telemetry_data: Dict[str, Any]) -> "SecurityAlert":
        """
        Create a SecurityAlert from an event and telemetry data.
        
        Args:
            db_session: Database session
            event: The parent Event object
            telemetry_data: The telemetry data dictionary
            
        Returns:
            SecurityAlert: The created security alert
        """
        data = telemetry_data.get("data", {})
        
        # Extract timestamp
        timestamp = data.get("timestamp") or event.timestamp or datetime.utcnow()
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        
        # Create security alert
        security_alert = cls(
            event_id=event.id,
            alert_type=data.get("alert_type", "unknown"),
            severity=data.get("severity", "MEDIUM"),
            description=data.get("description", "No description provided"),
            timestamp=timestamp,
            status="OPEN",
            context=json.dumps(data.get("context")) if data.get("context") else None
        )
        
        db_session.add(security_alert)
        
        # Create SecurityAlertTrigger records if triggering events are specified
        if "triggering_events" in data and isinstance(data["triggering_events"], list):
            for triggering_event_id in data["triggering_events"]:
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