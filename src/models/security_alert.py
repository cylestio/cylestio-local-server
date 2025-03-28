"""
Security Alert model and related functionality.

This module defines the SecurityAlert model for storing security-related events
and the SecurityAlertTrigger model for connecting events with the alerts they triggered.
"""
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
    timestamp = Column(DateTime, nullable=False)
    resolution_status = Column(String, index=True, default="open")  # 'open', 'investigating', 'resolved', 'false_positive'
    resolution_timestamp = Column(DateTime)
    resolution_notes = Column(Text)
    
    alert_metadata = Column(Text)  # JSON field for additional metadata - renamed from 'metadata'
    
    # Relationships
    event = relationship("Event", back_populates="security_alert")
    triggered_by = relationship("SecurityAlertTrigger", back_populates="alert")
    
    def __repr__(self) -> str:
        return f"<SecurityAlert {self.id} ({self.alert_type}, {self.severity})>"
    
    @classmethod
    def from_event(cls, db_session, event, telemetry_data: Dict[str, Any]) -> "SecurityAlert":
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
        timestamp = data.get("timestamp") or event.timestamp
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        
        # Create security alert
        security_alert = cls(
            event_id=event.id,
            alert_type=data.get("alert_type", "unknown"),
            severity=data.get("severity", "medium"),
            description=data.get("description", "No description provided"),
            timestamp=timestamp,
            resolution_status=data.get("resolution_status", "open"),
            alert_metadata=data.get("metadata")  # Use renamed field
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
    
    def resolve(self, db_session, resolution_status: str, resolution_notes: Optional[str] = None) -> None:
        """
        Resolve the security alert.
        
        Args:
            db_session: Database session
            resolution_status: The resolution status ('resolved', 'false_positive', etc.)
            resolution_notes: Optional notes about the resolution
        """
        self.resolution_status = resolution_status
        self.resolution_timestamp = datetime.utcnow()
        if resolution_notes:
            self.resolution_notes = resolution_notes
        
        db_session.add(self)
    
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