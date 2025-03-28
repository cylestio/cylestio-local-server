"""
Framework Event model and related functionality.

This module defines the FrameworkEvent model for storing framework-specific events
such as system lifecycle events, configuration changes, and other internal events.
"""
import json
from datetime import datetime
from typing import Dict, Any, Optional

from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime
from sqlalchemy.orm import relationship

from src.models.base import Base


class FrameworkEvent(Base):
    """
    Framework Event model for storing framework-specific events.
    
    This model captures information about system lifecycle events, configuration changes,
    and other internal events from the agent framework.
    """
    __tablename__ = "framework_events"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, unique=True, index=True)
    
    category = Column(String, nullable=False, index=True)  # 'lifecycle', 'config', 'error', etc.
    subcategory = Column(String, index=True)
    component = Column(String, index=True)  # 'agent', 'server', 'monitor', etc.
    
    lifecycle_state = Column(String, index=True)  # 'started', 'stopped', 'paused', 'resumed', etc.
    config_parameter = Column(String, index=True)
    config_value_before = Column(Text)
    config_value_after = Column(Text)
    
    message = Column(Text)
    details = Column(Text)  # JSON field for additional details
    
    # Relationships
    event = relationship("Event", back_populates="framework_event")
    
    def __repr__(self) -> str:
        return f"<FrameworkEvent {self.id} ({self.category}/{self.subcategory})>"
    
    @classmethod
    def from_event(cls, db_session, event, telemetry_data: Dict[str, Any]) -> "FrameworkEvent":
        """
        Create a FrameworkEvent from an event and telemetry data.
        
        Args:
            db_session: Database session
            event: The parent Event object
            telemetry_data: The telemetry data dictionary
            
        Returns:
            FrameworkEvent: The created framework event
        """
        data = telemetry_data.get("data", {})
        
        # Create framework event
        framework_event = cls(
            event_id=event.id,
            category=data.get("category", "unknown"),
            subcategory=data.get("subcategory"),
            component=data.get("component"),
            lifecycle_state=data.get("lifecycle_state"),
            config_parameter=data.get("config_parameter"),
            config_value_before=cls._serialize_config_value(data.get("config_value_before")),
            config_value_after=cls._serialize_config_value(data.get("config_value_after")),
            message=data.get("message"),
            details=json.dumps(data.get("details")) if data.get("details") else None
        )
        
        db_session.add(framework_event)
        return framework_event
    
    @staticmethod
    def _serialize_config_value(value) -> Optional[str]:
        """
        Serialize a config value to a string representation.
        
        Args:
            value: The value to serialize
            
        Returns:
            str or None: The serialized value
        """
        if value is None:
            return None
            
        if isinstance(value, (dict, list)):
            return json.dumps(value)
            
        return str(value)
    
    def get_details(self) -> Optional[Dict]:
        """
        Get the details as a dictionary.
        
        Returns:
            Dict or None: The details as a dictionary or None if not available
        """
        if not self.details:
            return None
            
        try:
            return json.loads(self.details)
        except (json.JSONDecodeError, TypeError):
            return None
    
    def get_config_values(self) -> Dict[str, Any]:
        """
        Get the configuration values before and after the change.
        
        Returns:
            Dict: Dictionary with 'before' and 'after' keys
        """
        before = None
        after = None
        
        if self.config_value_before:
            try:
                before = json.loads(self.config_value_before)
            except (json.JSONDecodeError, TypeError):
                before = self.config_value_before
                
        if self.config_value_after:
            try:
                after = json.loads(self.config_value_after)
            except (json.JSONDecodeError, TypeError):
                after = self.config_value_after
                
        return {
            "before": before,
            "after": after
        } 