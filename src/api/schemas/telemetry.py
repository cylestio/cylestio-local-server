from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, validator
from datetime import datetime
import json

class TelemetryEventBase(BaseModel):
    """Base model for telemetry events"""
    schema_version: str = Field(..., description="Schema version")
    timestamp: str = Field(..., description="Event timestamp in ISO format")
    trace_id: Optional[str] = Field(None, description="Trace identifier")
    span_id: Optional[str] = Field(None, description="Span identifier")
    parent_span_id: Optional[str] = Field(None, description="Parent span identifier")
    name: str = Field(..., description="Event name")
    level: str = Field(..., description="Log level")
    agent_id: Optional[str] = Field(None, description="Agent identifier")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="Event attributes")

    @validator('timestamp')
    def validate_timestamp(cls, v):
        """Ensure timestamp is in ISO format"""
        try:
            # Validate timestamp format by parsing and then returning the original string
            datetime.fromisoformat(v.replace('Z', '+00:00'))
            return v
        except (ValueError, TypeError):
            raise ValueError("Invalid timestamp format. Must be ISO format (YYYY-MM-DDTHH:MM:SS.mmmmmm)")
    
    @validator('agent_id', pre=True, always=True)
    def validate_agent_id(cls, v, values):
        """
        Validate agent_id field.
        If agent_id is not provided, attempt to extract it from:
        1. session.id in attributes (for framework events)
        2. host.name in attributes
        3. Default to "unknown-agent" as fallback
        """
        if v:
            return v
            
        # Try to extract from attributes if available
        attributes = values.get('attributes', {})
        
        # Check for session.id in attributes (common for framework events)
        if 'session.id' in attributes:
            return attributes['session.id']
            
        # Check for host.name in attributes
        if 'host.name' in attributes:
            return attributes['host.name']
            
        # Generate a default agent_id
        return "unknown-agent"
    
    @validator('trace_id', pre=True)
    def validate_trace_id(cls, v):
        """
        Validate trace_id field.
        If trace_id is null, convert to a string "null-trace"
        """
        if v is None:
            return "null-trace"
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "schema_version": "1.0",
                "timestamp": "2024-03-27T15:31:40.622017",
                "trace_id": "2a8ec755032d4e2ab0db888ab84ef595",
                "span_id": "96d8c2be667e4c78",
                "parent_span_id": "f1490a668d69d1dc",
                "name": "llm.request",
                "level": "INFO",
                "agent_id": "weather-agent",
                "attributes": {
                    "llm.request.model": "claude-3-haiku-20240307",
                    "llm.request.max_tokens": 1000,
                    "llm.request.temperature": 0.7,
                    "caller.file": "weather_client.py",
                    "caller.line": 117,
                    "caller.function": "process_query"
                }
            }
        }
        from_attributes = True

class TelemetryEventCreate(TelemetryEventBase):
    """Schema for creating a new telemetry event"""
    pass

class TelemetryEventBatchCreate(BaseModel):
    """Schema for creating multiple telemetry events"""
    events: List[TelemetryEventCreate] = Field(..., description="List of telemetry events")
    
    @validator('events')
    def validate_batch_size(cls, events):
        if len(events) > 1000:
            raise ValueError("Batch size exceeds maximum of 1000 events")
        return events

class TelemetryEvent(TelemetryEventBase):
    """Schema for telemetry event response"""
    id: str = Field(..., description="Event ID")
    
    class Config:
        from_attributes = True

class TelemetryEventResponse(BaseModel):
    """Schema for telemetry event submission response"""
    success: bool = Field(..., description="Success status")
    event_id: Optional[str] = Field(None, description="Event ID if successful")
    error: Optional[str] = Field(None, description="Error message if unsuccessful")

class TelemetryEventBatchResponse(BaseModel):
    """Schema for batch telemetry event submission response"""
    success: bool = Field(..., description="Overall success status")
    total: int = Field(..., description="Total number of events in batch")
    processed: int = Field(..., description="Number of events successfully processed")
    failed: int = Field(..., description="Number of events that failed processing")
    details: Optional[List[Dict[str, Any]]] = Field(None, description="Details of failures if any") 