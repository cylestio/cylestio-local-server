"""
Framework event model for framework-specific events.

This module defines the FrameworkEvent model for storing events related to
framework instrumentation and integration.
"""
import json
from datetime import datetime
from typing import Dict, Any, Optional, List

from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime, JSON, Float
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
    
    event_type = Column(String, index=True)  # 'startup', 'shutdown', 'config_change', etc.
    framework_name = Column(String, index=True)  # 'langchain', 'llama_index', etc.
    framework_version = Column(String)
    
    # For backward compatibility
    category = Column(String, index=True)  # 'lifecycle', 'config', 'error', etc.
    subcategory = Column(String, index=True)
    component = Column(String, index=True)  # 'agent', 'server', 'monitor', etc.
    
    lifecycle_state = Column(String, index=True)  # 'started', 'stopped', 'paused', 'resumed', etc.
    config_parameter = Column(String, index=True)
    config_value_before = Column(Text)
    config_value_after = Column(Text)
    
    message = Column(Text)
    details = Column(Text)  # JSON field for additional details
    
    # Extracted attribute fields for better querying
    app_version = Column(String, index=True)
    os_type = Column(String, index=True)
    memory_usage_mb = Column(Float)
    cpu_usage_percent = Column(Float)
    environment = Column(String, index=True)
    
    # Raw attributes JSON storage for complete data
    raw_attributes = Column(JSON)
    
    # Relationships
    event = relationship("Event", back_populates="framework_event")
    
    def __repr__(self) -> str:
        return f"<FrameworkEvent {self.id} ({self.event_type})>"
    
    @classmethod
    def from_event(cls, db_session, event, telemetry_data=None) -> "FrameworkEvent":
        """
        Create a FrameworkEvent from an event.
        
        Args:
            db_session: Database session
            event: The parent Event object
            telemetry_data: Optional telemetry data dictionary
            
        Returns:
            FrameworkEvent: The created framework event
        """
        # If telemetry_data is provided, use the method with telemetry support
        if telemetry_data:
            return cls.from_event_with_telemetry(db_session, event, telemetry_data)
            
        # Original implementation for backward compatibility
        if not event.data:
            raise ValueError("Event data is required to create a framework event")
            
        try:
            event_data = json.loads(event.data)
        except json.JSONDecodeError:
            raise ValueError("Event data must be valid JSON")
            
        payload = event_data.get("payload", {})
        
        # Extract event type from event name
        event_type = "unknown"
        if "startup" in event.name:
            event_type = "startup"
        elif "shutdown" in event.name:
            event_type = "shutdown"
        elif "config_change" in event.name:
            event_type = "config_change"
        elif "error" in event.name:
            event_type = "error"
        elif "patch" in event.name:
            event_type = "patch"
        elif "initialization" in event.name:
            event_type = "initialization"
        elif "unpatch" in event.name:
            event_type = "unpatch"
        
        # If payload is just a string, don't serialize it as details
        details = None
        if isinstance(payload, dict) and len(payload) > 1:
            # Only create details if there's more than the framework_name
            details_dict = {k: v for k, v in payload.items() if k != "framework_name"}
            if details_dict:
                details = json.dumps(details_dict)
        
        # Extract attributes
        attributes = payload.get("attributes", {})
        
        # Extract framework data
        # Legacy: directly in payload
        framework_name = payload.get("framework_name")
        framework_version = payload.get("framework_version")
        
        # New approach: from attributes
        if not framework_name:
            # Check if framework.name exists in attributes
            framework_name = attributes.get("framework.name")
            
            # Alternative format: framework directly without dots
            if not framework_name and "framework" in attributes:
                framework_name = attributes.get("framework")
        
        # Extract version
        if not framework_version:
            framework_version = attributes.get("framework.version")
            if not framework_version and "version" in attributes:
                framework_version = attributes.get("version")
        
        # Extract category and subcategory from attributes
        category = None
        subcategory = None
        
        # Extract category from framework.type or type
        if "framework.type" in attributes:
            category = attributes.get("framework.type")
        elif "type" in attributes:
            category = attributes.get("type")
        
        # Extract subcategory from patch.type or subcategory attributes
        if "patch.type" in attributes:
            subcategory = attributes.get("patch.type")
        elif "method" in attributes:
            subcategory = attributes.get("method")
            
        # Extract component information
        component = None
        if "component" in attributes:
            component = attributes.get("component")
        elif "patch.components" in attributes:
            components = attributes.get("patch.components")
            if isinstance(components, list):
                component = ", ".join(components)
            else:
                component = str(components)
                
        # Extract lifecycle state
        lifecycle_state = None
        if "lifecycle_state" in attributes:
            lifecycle_state = attributes.get("lifecycle_state")
        elif "framework.initialization_time" in attributes:
            lifecycle_state = "initialized"
        elif "patch_time" in attributes:
            lifecycle_state = "patched"
        elif "unpatch" in event.name.lower():
            lifecycle_state = "unpatched"
        elif "patch" in event.name.lower():
            lifecycle_state = "patched"
            
        # Extract message
        message = None
        if "message" in attributes:
            message = attributes.get("message")
        elif "note" in attributes:
            message = attributes.get("note")
        
        # Create framework event
        framework_event = cls(
            event_id=event.id,
            event_type=event_type,
            framework_name=framework_name,
            framework_version=framework_version,
            category=category,
            subcategory=subcategory,
            component=component,
            lifecycle_state=lifecycle_state,
            message=message,
            details=details,
            raw_attributes=attributes,  # Store raw attributes
            
            # Extract known attributes to dedicated columns
            app_version=attributes.get("app_version", payload.get("app_version")),
            os_type=attributes.get("os_type", payload.get("os_type")),
            memory_usage_mb=attributes.get("memory_usage_mb", payload.get("memory_usage_mb")),
            cpu_usage_percent=attributes.get("cpu_usage_percent", payload.get("cpu_usage_percent")),
            environment=attributes.get("environment", payload.get("environment"))
        )
        
        db_session.add(framework_event)
        return framework_event
    
    @classmethod
    def from_event_with_telemetry(cls, db_session, event, telemetry_data: Dict[str, Any]) -> "FrameworkEvent":
        """
        Create a FrameworkEvent from an event and telemetry data.
        
        Args:
            db_session: Database session
            event: The parent Event object
            telemetry_data: Telemetry data dictionary
            
        Returns:
            FrameworkEvent: The created framework event
        """
        attributes = telemetry_data.get('attributes', {})
        
        # Extract event type from event name
        event_type = "unknown"
        if "startup" in event.name:
            event_type = "startup"
        elif "shutdown" in event.name:
            event_type = "shutdown"
        elif "config_change" in event.name:
            event_type = "config_change"
        elif "error" in event.name:
            event_type = "error"
        elif "patch" in event.name:
            event_type = "patch"
        elif "initialization" in event.name:
            event_type = "initialization"
        elif "unpatch" in event.name:
            event_type = "unpatch"
            
        # Extract framework data
        framework_name = attributes.get('framework.name')
        if not framework_name and "framework" in attributes:
            framework_name = attributes.get("framework")
            
        framework_version = attributes.get('framework.version')
        if not framework_version and "version" in attributes:
            framework_version = attributes.get("version")
            
        # Extract category and subcategory
        category = None
        subcategory = None
        
        # Extract category from framework.type or type attributes
        if "framework.type" in attributes:
            category = attributes.get("framework.type")
        elif "type" in attributes:
            category = attributes.get("type")
        
        # Extract subcategory from patch.type, method, or similar attributes
        if "patch.type" in attributes:
            subcategory = attributes.get("patch.type")
        elif "method" in attributes:
            subcategory = attributes.get("method")
            
        # Extract component information
        component = None
        if "component" in attributes:
            component = attributes.get("component")
        elif "patch.components" in attributes:
            components = attributes.get("patch.components")
            if isinstance(components, list):
                component = ", ".join(components)
            else:
                component = str(components)
                
        # Extract lifecycle state
        lifecycle_state = None
        if "lifecycle_state" in attributes:
            lifecycle_state = attributes.get("lifecycle_state")
        elif "framework.initialization_time" in attributes:
            lifecycle_state = "initialized"
        elif "patch_time" in attributes:
            lifecycle_state = "patched"
        elif "unpatch" in event.name.lower():
            lifecycle_state = "unpatched"
        elif "patch" in event.name.lower():
            lifecycle_state = "patched"
            
        # Extract message
        message = None
        if "message" in attributes:
            message = attributes.get("message")
        elif "note" in attributes:
            message = attributes.get("note")
        
        # Create framework event
        framework_event = cls(
            event_id=event.id,
            event_type=event_type,
            framework_name=framework_name,
            framework_version=framework_version,
            category=category,
            subcategory=subcategory,
            component=component,
            lifecycle_state=lifecycle_state,
            message=message,
            details=json.dumps(attributes) if attributes else None,
            raw_attributes=attributes,  # Store raw attributes
            
            # Extract known attributes to dedicated columns
            app_version=attributes.get("app_version") or attributes.get("framework.app_version"),
            os_type=attributes.get("os_type") or attributes.get("framework.os_type") or attributes.get("env.os.type"),
            memory_usage_mb=attributes.get("memory_usage_mb") or attributes.get("framework.memory_usage_mb"),
            cpu_usage_percent=attributes.get("cpu_usage_percent") or attributes.get("framework.cpu_usage_percent"),
            environment=attributes.get("environment") or attributes.get("framework.environment")
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
    
    def get_details_dict(self) -> Optional[Dict]:
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
    
    # For backward compatibility
    get_details = get_details_dict
    
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
    def events_by_framework(cls, db_session, framework_name: str) -> List["FrameworkEvent"]:
        """
        Get all events for a specific framework.
        
        Args:
            db_session: Database session
            framework_name: Name of the framework
            
        Returns:
            List[FrameworkEvent]: List of events for the framework
        """
        return db_session.query(cls).filter(
            cls.framework_name == framework_name
        ).order_by(cls.id.desc()).all() 