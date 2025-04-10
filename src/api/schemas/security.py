"""
Security API schemas.

This module defines the Pydantic models for security API request and response validation.
"""
from datetime import datetime
from typing import List, Dict, Any, Optional

from pydantic import BaseModel


class SecurityAlertBase(BaseModel):
    """Base schema for security alerts."""
    id: int
    timestamp: str
    schema_version: str
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    parent_span_id: Optional[str] = None
    event_name: str
    log_level: str
    alert_level: str
    category: str
    severity: str
    description: str
    llm_vendor: Optional[str] = None
    content_sample: Optional[str] = None
    detection_time: Optional[str] = None
    keywords: Optional[List[str]] = None
    event_id: int
    agent_id: Optional[str] = None
    
    class Config:
        orm_mode = True


class SecurityAlertDetail(SecurityAlertBase):
    """Detailed security alert with raw attributes."""
    related_events: Optional[List[Dict[str, Any]]] = None


class TimeSeriesDataPoint(BaseModel):
    """Time series data point."""
    timestamp: str
    count: int


class MetricBreakdown(BaseModel):
    """Metric breakdown by dimension."""
    by_severity: Dict[str, int]
    by_category: Dict[str, int]
    by_alert_level: Dict[str, int]
    by_llm_vendor: Dict[str, int]
    total_count: int


class TimeRange(BaseModel):
    """Time range information."""
    from_time: str
    to_time: str
    description: str


class SecurityOverviewResponse(BaseModel):
    """Security overview response."""
    metrics: MetricBreakdown
    time_series: List[TimeSeriesDataPoint]
    recent_alerts: List[SecurityAlertBase]
    time_range: TimeRange 