from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field
from datetime import datetime

# Event List Response Models
class EventItem(BaseModel):
    """Basic event information for listing"""
    event_id: str = Field(..., description="Event ID")
    timestamp: str = Field(..., description="Event timestamp in ISO format")
    agent_id: str = Field(..., description="Agent ID")
    agent_name: str = Field(..., description="Agent name")
    event_type: str = Field(..., description="Event type (llm, tool, security, etc.)")
    status: str = Field(..., description="Event status (success, error, etc.)")
    severity: str = Field(..., description="Event severity (info, warning, error, etc.)")
    summary: str = Field(..., description="Event summary")
    session_id: Optional[str] = Field(None, description="Session ID")
    trace_id: Optional[str] = Field(None, description="Trace ID")
    has_children: Optional[bool] = Field(None, description="Whether this event has child events")
    parent_span_id: Optional[str] = Field(None, description="Parent span ID")
    span_id: Optional[str] = Field(None, description="Span ID")

class PaginationInfo(BaseModel):
    """Pagination metadata"""
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Items per page")
    total: int = Field(..., description="Total number of items")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_prev: bool = Field(..., description="Whether there is a previous page")

class EventListMeta(BaseModel):
    """Metadata for event list response"""
    timestamp: str = Field(..., description="Response timestamp")
    time_period: str = Field(..., description="Time period for the query")
    filters_applied: Dict[str, Any] = Field(..., description="Filters applied to the query")

class EventListResponse(BaseModel):
    """Response model for listing events"""
    items: List[EventItem] = Field(..., description="List of events")
    pagination: PaginationInfo = Field(..., description="Pagination information")
    meta: EventListMeta = Field(..., description="Response metadata")

# Event Detail Response Models
class EventMetadata(BaseModel):
    """Metadata specific to event type"""
    class Config:
        extra = "allow"

class EventDetailResponse(BaseModel):
    """Detailed event information"""
    event_id: str = Field(..., description="Event ID")
    timestamp: str = Field(..., description="Event timestamp in ISO format")
    agent_id: str = Field(..., description="Agent ID")
    agent_name: str = Field(..., description="Agent name")
    event_type: str = Field(..., description="Event type (llm, tool, security, etc.)")
    status: str = Field(..., description="Event status (success, error, etc.)")
    severity: str = Field(..., description="Event severity (info, warning, error, etc.)")
    summary: str = Field(..., description="Event summary")
    detail: str = Field(..., description="Detailed event description")
    session_id: Optional[str] = Field(None, description="Session ID")
    trace_id: Optional[str] = Field(None, description="Trace ID")
    related_events: List[str] = Field([], description="Related event IDs")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Event type-specific metadata")
    tags: Optional[List[str]] = Field(None, description="Event tags")
    attributes: Optional[Dict[str, Any]] = Field(None, description="Event attributes")

# Event Timeline Response Models
class EventTypeCount(BaseModel):
    """Event counts by type"""
    llm: int = Field(0, description="LLM events count")
    tool: int = Field(0, description="Tool events count")
    security: int = Field(0, description="Security events count")
    framework: int = Field(0, description="Framework events count")

class EventStatusCount(BaseModel):
    """Event counts by status"""
    success: int = Field(0, description="Success events count")
    error: int = Field(0, description="Error events count")
    warning: int = Field(0, description="Warning events count")

class TimelineInterval(BaseModel):
    """Data for a single timeline interval"""
    timestamp: str = Field(..., description="Interval start timestamp")
    total: int = Field(0, description="Total events in interval")
    by_type: EventTypeCount = Field(..., description="Events by type")
    by_status: EventStatusCount = Field(..., description="Events by status")

class TimelineMeta(BaseModel):
    """Metadata for timeline response"""
    timestamp: str = Field(..., description="Response timestamp")
    time_period: str = Field(..., description="Time period for the query")
    interval: str = Field(..., description="Time interval used")
    filters_applied: Dict[str, Any] = Field(..., description="Filters applied to the query")

class EventTimelineResponse(BaseModel):
    """Response model for event timeline"""
    intervals: List[TimelineInterval] = Field(..., description="Timeline intervals")
    meta: TimelineMeta = Field(..., description="Response metadata") 