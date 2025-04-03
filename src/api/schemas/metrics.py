from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, validator
from datetime import datetime, timedelta
from enum import Enum

class TimeRange(str, Enum):
    """Time range options for metrics queries"""
    HOUR = "1h"
    DAY = "1d"
    WEEK = "7d"
    MONTH = "30d"
    
class AggregationInterval(str, Enum):
    """Aggregation interval options"""
    MINUTE = "1m"
    HOUR = "1h"
    DAY = "1d"
    WEEK = "7d"

class MetricType(str, Enum):
    """Types of metrics that can be queried"""
    LLM_REQUEST_COUNT = "llm_request_count"
    LLM_TOKEN_USAGE = "llm_token_usage"
    LLM_RESPONSE_TIME = "llm_response_time"
    TOOL_EXECUTION_COUNT = "tool_execution_count"
    TOOL_SUCCESS_RATE = "tool_success_rate"
    ERROR_COUNT = "error_count"
    SESSION_COUNT = "session_count"
    
class MetricQueryBase(BaseModel):
    """Base model for metric queries"""
    agent_id: Optional[str] = Field(None, description="Filter by agent ID")
    from_time: Optional[datetime] = Field(None, description="Start time (ISO format)")
    to_time: Optional[datetime] = Field(None, description="End time (ISO format)")
    time_range: Optional[TimeRange] = Field(None, description="Predefined time range")
    
    @validator('to_time')
    def validate_time_range(cls, to_time, values):
        from_time = values.get('from_time')
        time_range = values.get('time_range')
        
        if (from_time is None and to_time is not None) or (from_time is not None and to_time is None):
            raise ValueError("Both from_time and to_time must be provided together")
            
        if from_time is not None and to_time is not None and from_time >= to_time:
            raise ValueError("from_time must be before to_time")
            
        if from_time is not None and time_range is not None:
            raise ValueError("Cannot specify both explicit time range and predefined time_range")
            
        return to_time

class MetricQuery(MetricQueryBase):
    """Schema for metric query"""
    metric: MetricType = Field(..., description="Type of metric to query")
    interval: Optional[AggregationInterval] = Field(None, description="Aggregation interval")
    dimensions: Optional[List[str]] = Field(None, description="Dimensions to group by")
    
    @validator('dimensions')
    def validate_dimensions(cls, dimensions):
        if dimensions is not None:
            valid_dimensions = [
                "agent_id", "level", "name", "llm.vendor", "llm.model", 
                "tool.name", "status", "error.type"
            ]
            for dim in dimensions:
                if dim not in valid_dimensions:
                    raise ValueError(f"Invalid dimension: {dim}. Valid dimensions are: {', '.join(valid_dimensions)}")
        return dimensions

class MetricDataPoint(BaseModel):
    """Schema for a single metric data point"""
    timestamp: datetime = Field(..., description="Timestamp for this data point")
    value: Union[int, float] = Field(..., description="Metric value")
    dimensions: Optional[Dict[str, str]] = Field(None, description="Dimension values if grouped")

class MetricResponse(BaseModel):
    """Schema for metric query response"""
    metric: str = Field(..., description="Metric type")
    from_time: datetime = Field(..., description="Query start time")
    to_time: datetime = Field(..., description="Query end time")
    interval: Optional[str] = Field(None, description="Aggregation interval used")
    data: List[MetricDataPoint] = Field(..., description="Metric data points")
    
class MetricSummary(BaseModel):
    """Schema for metric summary"""
    metric: str = Field(..., description="Metric name")
    value: Union[int, float] = Field(..., description="Current value")
    change: Optional[float] = Field(None, description="Percentage change from previous period")
    trend: Optional[str] = Field(None, description="Trend direction: up, down, flat")
    
class DashboardResponse(BaseModel):
    """Schema for dashboard summary response"""
    period: str = Field(..., description="Time period for the summary")
    time_range: str = Field(..., description="Time range for the metrics")
    from_time: str = Field(..., description="Start time of the metrics in ISO format")
    to_time: str = Field(..., description="End time of the metrics in ISO format")
    agent_id: Optional[str] = Field(None, description="Optional agent ID filter")
    metrics: List[MetricSummary] = Field(..., description="List of key metrics")
    error: Optional[str] = Field(None, description="Optional error message") 