"""
Tool Interaction model and related functionality.

This module defines the ToolInteraction model for storing details about tool calls
made by agents, including request, response, and other metadata.
"""
import json
from datetime import datetime
from typing import Dict, Any, Optional

from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, Text, DateTime
from sqlalchemy.orm import relationship

from src.models.base import Base


class ToolInteraction(Base):
    """
    Tool Interaction model for storing details about tool calls.
    
    This model captures information about tools being called by an agent,
    including the tool name, input parameters, output, status, and timing information.
    """
    __tablename__ = "tool_interactions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, unique=True, index=True)
    
    tool_name = Column(String, nullable=False, index=True)
    interaction_type = Column(String, index=True)  # 'start', 'finish', 'error'
    status = Column(String, index=True)  # 'success', 'error', 'pending'
    status_code = Column(Integer)
    response_time_ms = Column(Float)
    
    parameters = Column(Text)  # JSON string
    result = Column(Text)      # JSON string
    error = Column(Text)
    
    request_timestamp = Column(DateTime)
    response_timestamp = Column(DateTime)
    duration_ms = Column(Float)
    
    # Relationships
    event = relationship("Event", back_populates="tool_interaction")
    attributes = relationship("ToolAttribute", back_populates="tool_interaction", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<ToolInteraction {self.id} ({self.tool_name})>"
    
    @classmethod
    def from_event(cls, db_session, event) -> "ToolInteraction":
        """
        Create a ToolInteraction from an event.
        
        Args:
            db_session: Database session
            event: The parent Event object
            
        Returns:
            ToolInteraction: The created tool interaction
        """
        if not event.data:
            raise ValueError("Event data is required to create a tool interaction")
            
        try:
            event_data = json.loads(event.data)
        except json.JSONDecodeError:
            raise ValueError("Event data must be valid JSON")
            
        payload = event_data.get("payload", {})
        interaction_type = "start"
        
        if "tool.call.finish" in event.name:
            interaction_type = "finish"
        elif "tool.call.error" in event.name:
            interaction_type = "error"
            
        # Create tool interaction
        tool_interaction = cls(
            event_id=event.id,
            tool_name=payload.get("tool_name", "unknown"),
            interaction_type=interaction_type,
            parameters=json.dumps(payload.get("parameters")) if payload.get("parameters") else None,
            result=json.dumps(payload.get("result")) if payload.get("result") else None,
            error=payload.get("error"),
            status_code=payload.get("status_code"),
            response_time_ms=payload.get("response_time_ms")
        )
        
        db_session.add(tool_interaction)
        return tool_interaction
        
    # For backward compatibility    
    @classmethod
    def from_event_with_telemetry(cls, db_session, event, telemetry_data: Dict[str, Any]) -> "ToolInteraction":
        """
        Create a ToolInteraction from an event and telemetry data.
        
        Args:
            db_session: Database session
            event: The parent Event object
            telemetry_data: The telemetry data dictionary
            
        Returns:
            ToolInteraction: The created tool interaction
        """
        data = telemetry_data.get("data", {})
        
        # Extract timestamps
        request_timestamp = data.get("timestamp") or event.timestamp
        if isinstance(request_timestamp, str):
            request_timestamp = datetime.fromisoformat(request_timestamp.replace('Z', '+00:00'))
        
        response_timestamp = data.get("response_timestamp")
        if isinstance(response_timestamp, str):
            response_timestamp = datetime.fromisoformat(response_timestamp.replace('Z', '+00:00'))
        
        # Calculate duration if both timestamps are available
        duration_ms = None
        if request_timestamp and response_timestamp:
            duration_ms = (response_timestamp - request_timestamp).total_seconds() * 1000
        
        # Create tool interaction
        tool_interaction = cls(
            event_id=event.id,
            tool_name=data.get("tool_name", "unknown"),
            status=data.get("status", "unknown"),
            request_timestamp=request_timestamp,
            response_timestamp=response_timestamp,
            duration_ms=duration_ms,
            parameters=json.dumps(data.get("input_params")) if data.get("input_params") else None,
            result=json.dumps(data.get("output")) if data.get("output") else None,
            error=data.get("error")
        )
        
        db_session.add(tool_interaction)
        return tool_interaction
    
    def get_parameters_dict(self) -> Optional[Dict]:
        """
        Get the parameters as a dictionary.
        
        Returns:
            Dict or None: The parameters as a dictionary or None if not available
        """
        if not self.parameters:
            return None
            
        try:
            return json.loads(self.parameters)
        except (json.JSONDecodeError, TypeError):
            return None
    
    def get_result_dict(self) -> Optional[Any]:
        """
        Get the result in its parsed form.
        
        Returns:
            Any or None: The parsed result or None if not available
        """
        if not self.result:
            return None
            
        try:
            return json.loads(self.result)
        except (json.JSONDecodeError, TypeError):
            return None
            
    # For backward compatibility
    get_input_params = get_parameters_dict
    get_output_content = get_result_dict 