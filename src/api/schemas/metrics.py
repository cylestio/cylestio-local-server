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

class ToolInteractionDetailItem(BaseModel):
    """Schema for detailed tool interaction data"""
    id: int = Field(..., description="Tool interaction ID")
    associated_event_ids: List[int] = Field(default_factory=list, description="List of all event IDs associated with this tool interaction (sharing the same span_id)")
    tool_name: str = Field(..., description="Name of the tool")
    interaction_type: str = Field(..., description="Type of interaction (execution, result)")
    status: str = Field(..., description="Status of the tool interaction (success, error, pending)")
    status_code: Optional[int] = Field(None, description="Status code if applicable")
    parameters: Optional[Any] = Field(None, description="Tool parameters (parsed from JSON)")
    result: Optional[Any] = Field(None, description="Tool result (parsed from JSON)")
    error: Optional[str] = Field(None, description="Error message if any")
    request_timestamp: Optional[datetime] = Field(None, description="When the tool request was made")
    response_timestamp: Optional[datetime] = Field(None, description="When the tool response was received")
    duration_ms: Optional[float] = Field(None, description="Duration of the tool execution in milliseconds")
    framework_name: Optional[str] = Field(None, description="Framework that was used")
    tool_version: Optional[str] = Field(None, description="Tool version")
    authorization_level: Optional[str] = Field(None, description="Authorization level used")
    execution_time_ms: Optional[float] = Field(None, description="Execution time in milliseconds")
    cache_hit: Optional[bool] = Field(None, description="Whether the result was from cache")
    api_version: Optional[str] = Field(None, description="API version used")
    raw_attributes: Optional[Dict[str, Any]] = Field(None, description="Raw attributes from the event")
    span_id: Optional[str] = Field(None, description="Span ID from the associated event")
    trace_id: Optional[str] = Field(None, description="Trace ID from the associated event")
    agent_id: Optional[str] = Field(None, description="Agent ID from the associated event")

class ToolInteractionListResponse(BaseModel):
    """Schema for a list of tool interactions"""
    total: int = Field(..., description="Total number of interactions matching the query")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Page size")
    from_time: datetime = Field(..., description="Query start time")
    to_time: datetime = Field(..., description="Query end time")
    interactions: List[ToolInteractionDetailItem] = Field(..., description="List of tool interactions")

class TimeGranularity(str, Enum):
    """Time granularity options for LLM metrics"""
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"

class LLMMetricsFilter(BaseModel):
    """Schema for LLM metrics filters"""
    agent_id: Optional[str] = Field(None, description="Filter by agent ID")
    model_name: Optional[str] = Field(None, description="Filter by model name")
    from_time: Optional[datetime] = Field(None, description="Start time (ISO format)")
    to_time: Optional[datetime] = Field(None, description="End time (ISO format)")
    granularity: Optional[TimeGranularity] = Field(TimeGranularity.DAY, description="Time granularity")
    
    @validator('to_time')
    def validate_time_range(cls, to_time, values):
        from_time = values.get('from_time')
        
        if (from_time is None and to_time is not None) or (from_time is not None and to_time is None):
            raise ValueError("Both from_time and to_time must be provided together")
            
        if from_time is not None and to_time is not None and from_time >= to_time:
            raise ValueError("from_time must be before to_time")
            
        return to_time

class LLMMetricsBreakdown(str, Enum):
    """Breakdown options for LLM metrics"""
    NONE = "none"
    AGENT = "agent"
    MODEL = "model"
    TIME = "time"

class LLMMetricsResponse(BaseModel):
    """Schema for LLM metrics response"""
    request_count: int = Field(..., description="Total number of LLM requests")
    response_time_avg: float = Field(..., description="Average response time in ms")
    response_time_p95: float = Field(..., description="95th percentile response time in ms")
    success_rate: float = Field(..., description="Success rate (0-1)")
    error_rate: float = Field(..., description="Error rate (0-1)")
    token_count_input: int = Field(..., description="Total input tokens")
    token_count_output: int = Field(..., description="Total output tokens")
    token_count_total: int = Field(..., description="Total tokens")
    estimated_cost_usd: float = Field(..., description="Estimated cost in USD")
    first_seen: Optional[datetime] = Field(None, description="First seen timestamp")
    last_seen: Optional[datetime] = Field(None, description="Last seen timestamp")
    
class LLMMetricsBreakdownItem(BaseModel):
    """Schema for a single item in a breakdown response"""
    key: str = Field(..., description="Breakdown key (agent ID, model name, or timestamp)")
    metrics: LLMMetricsResponse = Field(..., description="Metrics for this item")
    relation_type: Optional[str] = Field(None, description="For agent-model relationships, specifies the type (primary, fallback, etc.)")
    time_distribution: Optional[List[Dict[str, Any]]] = Field(None, description="Optional time-based distribution data for histograms")
    token_distribution: Optional[List[Dict[str, Any]]] = Field(None, description="Optional token count distribution data for histograms")

class LLMMetricsBreakdownResponse(BaseModel):
    """Schema for LLM metrics breakdown response"""
    total: LLMMetricsResponse = Field(..., description="Aggregated metrics") 
    breakdown: List[LLMMetricsBreakdownItem] = Field(..., description="Breakdown items")
    from_time: datetime = Field(..., description="Query start time")
    to_time: datetime = Field(..., description="Query end time")
    filters: LLMMetricsFilter = Field(..., description="Applied filters")
    breakdown_by: LLMMetricsBreakdown = Field(..., description="Breakdown dimension")

# New schemas for LLM Explorer UI

class ConversationSummary(BaseModel):
    """Schema for conversation summary in list view"""
    trace_id: str = Field(..., description="Trace ID that identifies the conversation")
    first_timestamp: datetime = Field(..., description="Timestamp of first message in conversation")
    last_timestamp: datetime = Field(..., description="Timestamp of last message in conversation")
    agent_id: str = Field(..., description="Agent ID")
    agent_name: str = Field(..., description="Agent name")
    model: Optional[str] = Field(None, description="Primary model used in conversation")
    request_count: int = Field(..., description="Number of requests in conversation")
    total_tokens: int = Field(0, description="Total token usage")
    status: str = Field(..., description="Conversation status: success, error, or mixed")
    duration_ms: int = Field(0, description="Total duration of conversation")
    user_messages: int = Field(0, description="Count of user messages")
    assistant_messages: int = Field(0, description="Count of assistant messages")


class ConversationListResponse(BaseModel):
    """Schema for list of conversations"""
    items: List[ConversationSummary] = Field(..., description="List of conversations")
    pagination: Dict[str, Any] = Field(..., description="Pagination information")


class ConversationMessage(BaseModel):
    """Schema for a message in a conversation"""
    id: str = Field(..., description="Unique message ID")
    timestamp: datetime = Field(..., description="Message timestamp")
    trace_id: str = Field(..., description="Trace ID")
    span_id: str = Field(..., description="Span ID")
    model: Optional[str] = Field(None, description="Model used for this message")
    role: str = Field(..., description="Message role: user, assistant, or system")
    message_type: str = Field("unknown", description="Message type: request or response")
    status: str = Field(..., description="Message status")
    duration_ms: Optional[int] = Field(None, description="Processing duration in ms")
    input_tokens: Optional[int] = Field(None, description="Input token count")
    output_tokens: Optional[int] = Field(None, description="Output token count")
    content: str = Field(..., description="Message content")
    parent_id: Optional[str] = Field(None, description="ID of parent message")
    agent_id: str = Field(..., description="Agent ID")
    agent_name: str = Field(..., description="Agent name")
    event_id: Optional[int] = Field(None, description="ID of the source raw event")


class ConversationDetailResponse(BaseModel):
    """Schema for conversation detail with messages"""
    items: List[ConversationMessage] = Field(..., description="Messages in the conversation")
    pagination: Dict[str, Any] = Field(..., description="Pagination information")


class ConversationSearchParams(BaseModel):
    """Schema for conversation search parameters"""
    query: Optional[str] = Field(None, description="Full-text search across conversation content")
    agent_id: Optional[str] = Field(None, description="Filter by agent")
    status: Optional[str] = Field(None, description="Filter by conversation status")
    from_time: Optional[datetime] = Field(None, description="Start time filter")
    to_time: Optional[datetime] = Field(None, description="End time filter")
    token_min: Optional[int] = Field(None, description="Minimum token count filter")
    token_max: Optional[int] = Field(None, description="Maximum token count filter")
    has_error: Optional[bool] = Field(None, description="Filter for conversations with errors")
    page: int = Field(1, description="Page number")
    page_size: int = Field(20, description="Items per page")
    
    @validator('to_time')
    def validate_time_range(cls, to_time, values):
        from_time = values.get('from_time')
        
        if (from_time is None and to_time is not None) or (from_time is not None and to_time is None):
            raise ValueError("Both from_time and to_time must be provided together")
            
        if from_time is not None and to_time is not None and from_time >= to_time:
            raise ValueError("from_time must be before to_time")
            
        return to_time

# Update existing LLMInteraction schema to include agent info
class LLMRequestDetail(BaseModel):
    """Enhanced schema for LLM request details"""
    id: str = Field(..., description="Request ID")
    timestamp: datetime = Field(..., description="Request timestamp")
    trace_id: str = Field(..., description="Trace ID")
    span_id: str = Field(..., description="Span ID")
    model: str = Field(..., description="Model name")
    status: str = Field(..., description="Request status")
    duration_ms: Optional[int] = Field(None, description="Processing duration in ms")
    input_tokens: Optional[int] = Field(None, description="Input token count")
    output_tokens: Optional[int] = Field(None, description="Output token count")
    agent_id: str = Field(..., description="Agent ID")
    agent_name: str = Field(..., description="Agent name")
    content: Optional[str] = Field(None, description="Request content")
    response: Optional[str] = Field(None, description="Response content")
    
class LLMRequestListResponse(BaseModel):
    """Schema for list of LLM requests"""
    items: List[LLMRequestDetail] = Field(..., description="List of LLM requests")
    pagination: Dict[str, Any] = Field(..., description="Pagination information") 