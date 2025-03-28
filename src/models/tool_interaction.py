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
    status = Column(String, nullable=False, index=True)  # 'success', 'error', 'pending'
    request_timestamp = Column(DateTime, nullable=False)
    response_timestamp = Column(DateTime)
    duration_ms = Column(Float)
    
    input_params = Column(Text)
    output_content = Column(Text)
    error_message = Column(Text)
    
    # Relationships
    event = relationship("Event", back_populates="tool_interaction")
    
    def __repr__(self) -> str:
        return f"<ToolInteraction {self.id} ({self.tool_name})>"
    
    @classmethod
    def from_event(cls, db_session, event, telemetry_data: Dict[str, Any]) -> "ToolInteraction":
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
            input_params=json.dumps(data.get("input_params")) if data.get("input_params") else None,
            output_content=json.dumps(data.get("output")) if data.get("output") else None,
            error_message=data.get("error")
        )
        
        db_session.add(tool_interaction)
        return tool_interaction
    
    def get_input_params(self) -> Optional[Dict]:
        """
        Get the input parameters as a dictionary.
        
        Returns:
            Dict or None: The input parameters as a dictionary or None if not available
        """
        if not self.input_params:
            return None
            
        try:
            return json.loads(self.input_params)
        except (json.JSONDecodeError, TypeError):
            return None
    
    def get_output_content(self) -> Optional[Any]:
        """
        Get the output content in its parsed form.
        
        Returns:
            Any or None: The parsed output content or None if not available
        """
        if not self.output_content:
            return None
            
        try:
            return json.loads(self.output_content)
        except (json.JSONDecodeError, TypeError):
            return None 