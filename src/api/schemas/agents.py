from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, validator
from datetime import datetime
from enum import Enum

from src.api.schemas.metrics import MetricSummary


class AgentStatus(str, Enum):
    """Agent status options"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PAUSED = "paused"


class AgentType(str, Enum):
    """Types of agents"""
    ASSISTANT = "assistant"
    CHATBOT = "chatbot"
    AUTONOMOUS = "autonomous"
    FUNCTION = "function"
    OTHER = "other"


class AgentListItem(BaseModel):
    """Schema for an agent in a list response"""
    agent_id: str = Field(..., description="Unique identifier for the agent")
    name: str = Field(..., description="Agent name")
    type: AgentType = Field(..., description="Type of agent")
    status: AgentStatus = Field(..., description="Current agent status")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    request_count: int = Field(..., description="Total number of requests")
    token_usage: int = Field(..., description="Total token usage")
    error_count: int = Field(..., description="Total number of errors")


class AgentListResponse(BaseModel):
    """Schema for agent list response"""
    items: List[AgentListItem] = Field(..., description="List of agents")
    pagination: Dict[str, Any] = Field(..., description="Pagination information")
    meta: Dict[str, Any] = Field(..., description="Response metadata")


class AgentDetail(BaseModel):
    """Schema for detailed agent information"""
    agent_id: str = Field(..., description="Unique identifier for the agent")
    name: str = Field(..., description="Agent name")
    type: AgentType = Field(..., description="Type of agent")
    status: AgentStatus = Field(..., description="Current agent status")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    metrics: Dict[str, Any] = Field(..., description="Summary metrics including request_count, token_usage, avg_response_time_ms, tool_usage, error_count, security_alerts_count, and policy_violations_count")


class AgentDashboardResponse(BaseModel):
    """Schema for agent dashboard response"""
    agent_id: str = Field(..., description="Agent ID")
    period: str = Field(..., description="Time period for the dashboard data")
    metrics: List[MetricSummary] = Field(..., description="List of key metrics")


class LLMUsageItem(BaseModel):
    """Schema for LLM usage information"""
    model: str = Field(..., description="LLM model name")
    vendor: str = Field(..., description="LLM vendor/provider")
    request_count: int = Field(..., description="Number of requests")
    input_tokens: int = Field(..., description="Number of input tokens")
    output_tokens: int = Field(..., description="Number of output tokens")
    total_tokens: int = Field(..., description="Total number of tokens")
    estimated_cost: float = Field(..., description="Estimated cost in USD")


class LLMUsageResponse(BaseModel):
    """Schema for LLM usage response"""
    items: List[LLMUsageItem] = Field(..., description="List of LLM usage by model")
    total_requests: int = Field(..., description="Total LLM requests")
    total_tokens: int = Field(..., description="Total token usage")
    total_cost: float = Field(..., description="Total estimated cost")
    meta: Dict[str, Any] = Field(..., description="Response metadata")


class LLMRequestItem(BaseModel):
    """Schema for LLM request information"""
    request_id: str = Field(..., description="Request ID")
    timestamp: datetime = Field(..., description="Request timestamp")
    model: str = Field(..., description="LLM model used")
    status: str = Field(..., description="Request status")
    input_tokens: int = Field(..., description="Number of input tokens")
    output_tokens: int = Field(..., description="Number of output tokens")
    duration_ms: int = Field(..., description="Request duration in milliseconds")
    prompt_summary: Optional[str] = Field(None, description="Summary of the prompt")
    response_summary: Optional[str] = Field(None, description="Summary of the response")


class LLMRequestsResponse(BaseModel):
    """Schema for LLM requests response"""
    items: List[LLMRequestItem] = Field(..., description="List of LLM requests")
    pagination: Dict[str, Any] = Field(..., description="Pagination information")
    meta: Dict[str, Any] = Field(..., description="Response metadata")


class TokenUsageItem(BaseModel):
    """Schema for token usage information"""
    timestamp: datetime = Field(..., description="Timestamp")
    input_tokens: int = Field(..., description="Number of input tokens")
    output_tokens: int = Field(..., description="Number of output tokens")
    total_tokens: int = Field(..., description="Total number of tokens")
    model: Optional[str] = Field(None, description="LLM model if grouped by model")


class TokenUsageResponse(BaseModel):
    """Schema for token usage response"""
    items: List[TokenUsageItem] = Field(..., description="List of token usage data points")
    total_input: int = Field(..., description="Total input tokens")
    total_output: int = Field(..., description="Total output tokens")
    total: int = Field(..., description="Total tokens")
    pagination: Dict[str, Any] = Field(..., description="Pagination information")
    meta: Dict[str, Any] = Field(..., description="Response metadata")


class ToolUsageItem(BaseModel):
    """Schema for tool usage information"""
    tool_name: str = Field(..., description="Tool name")
    category: str = Field(..., description="Tool category")
    execution_count: int = Field(..., description="Number of executions")
    success_count: int = Field(..., description="Number of successful executions")
    error_count: int = Field(..., description="Number of failed executions")
    success_rate: float = Field(..., description="Success rate (0-1)")
    avg_duration_ms: int = Field(..., description="Average execution duration in milliseconds")


class ToolUsageResponse(BaseModel):
    """Schema for tool usage response"""
    items: List[ToolUsageItem] = Field(..., description="List of tool usage information")
    total_executions: int = Field(..., description="Total tool executions")
    overall_success_rate: float = Field(..., description="Overall success rate")
    meta: Dict[str, Any] = Field(..., description="Response metadata")


class ToolExecutionItem(BaseModel):
    """Schema for tool execution information"""
    execution_id: str = Field(..., description="Execution ID")
    timestamp: datetime = Field(..., description="Execution timestamp")
    tool_name: str = Field(..., description="Tool name")
    status: str = Field(..., description="Execution status")
    duration_ms: int = Field(..., description="Execution duration in milliseconds")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Tool parameters")
    result_summary: Optional[str] = Field(None, description="Summary of the result or error")


class ToolExecutionsResponse(BaseModel):
    """Schema for tool executions response"""
    items: List[ToolExecutionItem] = Field(..., description="List of tool executions")
    pagination: Dict[str, Any] = Field(..., description="Pagination information")
    meta: Dict[str, Any] = Field(..., description="Response metadata")


class SessionItem(BaseModel):
    """Schema for session information"""
    session_id: str = Field(..., description="Session ID")
    start_time: datetime = Field(..., description="Session start time")
    end_time: Optional[datetime] = Field(None, description="Session end time")
    duration_seconds: Optional[int] = Field(None, description="Session duration in seconds")
    event_count: int = Field(..., description="Number of events in the session")
    llm_request_count: int = Field(..., description="Number of LLM requests")
    tool_execution_count: int = Field(..., description="Number of tool executions")
    error_count: int = Field(..., description="Number of errors")
    status: str = Field(..., description="Session status")


class SessionsResponse(BaseModel):
    """Schema for sessions response"""
    items: List[SessionItem] = Field(..., description="List of sessions")
    pagination: Dict[str, Any] = Field(..., description="Pagination information")
    meta: Dict[str, Any] = Field(..., description="Response metadata")


class TraceItem(BaseModel):
    """Schema for trace information"""
    trace_id: str = Field(..., description="Trace ID")
    start_time: datetime = Field(..., description="Trace start time")
    end_time: Optional[datetime] = Field(None, description="Trace end time")
    duration_ms: Optional[int] = Field(None, description="Trace duration in milliseconds")
    event_count: int = Field(..., description="Number of events in the trace")
    status: str = Field(..., description="Trace status")
    initial_event_type: str = Field(..., description="Type of the initial event")


class TracesResponse(BaseModel):
    """Schema for traces response"""
    items: List[TraceItem] = Field(..., description="List of traces")
    pagination: Dict[str, Any] = Field(..., description="Pagination information")
    meta: Dict[str, Any] = Field(..., description="Response metadata")


class AlertItem(BaseModel):
    """Schema for alert information"""
    alert_id: str = Field(..., description="Alert ID")
    timestamp: datetime = Field(..., description="Alert timestamp")
    type: str = Field(..., description="Alert type")
    severity: str = Field(..., description="Alert severity")
    description: str = Field(..., description="Alert description")
    status: str = Field(..., description="Alert status")
    related_event_id: Optional[str] = Field(None, description="Related event ID")


class AlertsResponse(BaseModel):
    """Schema for alerts response"""
    items: List[AlertItem] = Field(..., description="List of alerts")
    pagination: Dict[str, Any] = Field(..., description="Pagination information")
    meta: Dict[str, Any] = Field(..., description="Response metadata")


class AgentCostResponse(BaseModel):
    """Schema for agent cost response"""
    agent_id: str = Field(..., description="Agent ID")
    total_cost: float = Field(..., description="Total estimated cost in USD")
    total_tokens: int = Field(..., description="Total token usage")
    input_tokens: int = Field(..., description="Total input tokens")
    output_tokens: int = Field(..., description="Total output tokens")
    request_count: int = Field(..., description="Total LLM request count")
    model_breakdown: Optional[List[LLMUsageItem]] = Field(None, description="Cost breakdown by model")
    meta: Dict[str, Any] = Field(..., description="Response metadata with time period information") 