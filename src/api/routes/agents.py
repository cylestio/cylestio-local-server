import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Path, BackgroundTasks
from fastapi import status as http_status
from sqlalchemy.orm import Session

from src.utils.logging import get_logger
from src.database.session import get_db
from src.api.schemas.agents import (
    AgentListResponse, 
    AgentDetail, 
    AgentDashboardResponse,
    LLMUsageResponse,
    LLMRequestsResponse,
    TokenUsageResponse,
    ToolUsageResponse,
    ToolExecutionsResponse,
    SessionsResponse,
    TracesResponse,
    AlertsResponse
)
from src.api.schemas.metrics import TimeRange
from src.analysis.interface import (
    TimeRangeParams,
    PaginationParams,
    get_dashboard_metrics
)
from src.analysis.agent_analysis import (
    get_agent_sessions,
    get_agent_traces,
    get_agent_alerts,
    get_agents,
    get_agent_dashboard_metrics,
    get_agent_llm_usage as analyze_agent_llm_usage,
    get_agent_llm_requests as analyze_agent_llm_requests,
    get_agent_token_usage as analyze_agent_token_usage,
    get_agent_tool_usage as analyze_agent_tool_usage,
    get_agent_tool_executions
)

import asyncio
from functools import partial

logger = get_logger(__name__)

router = APIRouter()


@router.get(
    "/agents",
    response_model=AgentListResponse,
    summary="List all agents"
)
async def list_agents(
    status: Optional[str] = Query(None, description="Filter by agent status"),
    agent_type: Optional[str] = Query(None, description="Filter by agent type"),
    created_after: Optional[datetime] = Query(None, description="Filter by creation date"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=1000, description="Items per page"),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_dir: str = Query("desc", description="Sort direction (asc, desc)"),
    db: Session = Depends(get_db)
):
    """
    List all agents with optional filtering and sorting.
    
    Returns:
        AgentListResponse: List of agents
    """
    logger.info("Listing agents")
    
    try:
        # Create query filters based on parameters
        filters = {}
        if status:
            filters["status"] = status
        if agent_type:
            filters["type"] = agent_type
        if created_after:
            filters["created_at_min"] = created_after
            
        # Create pagination parameters
        pagination_params = PaginationParams(
            page=page,
            page_size=page_size
        )
        
        # Get agents from analysis layer
        items, total = get_agents(
            db, 
            filters, 
            pagination_params, 
            sort_by, 
            sort_dir
        )
        
        # Construct response
        response = {
            "items": items,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
                "has_next": page < ((total + page_size - 1) // page_size if total > 0 else 0),
                "has_prev": page > 1
            },
            "meta": {
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        return response
        
    except Exception as e:
        logger.error(f"Error listing agents: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing agents: {str(e)}"
        )


@router.get(
    "/agents/{agent_id}",
    response_model=AgentDetail,
    summary="Get agent details"
)
async def get_agent_details(
    agent_id: str = Path(..., description="Agent ID"),
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific agent.
    
    Returns:
        AgentDetail: Detailed agent information
    """
    logger.info(f"Getting details for agent: {agent_id}")
    
    try:
        # This would get agent details from the analysis layer
        # For now, we'll use placeholder data structure
        
        # Get agent details
        # In a real implementation, this would call a function like:
        # agent = get_agent_by_id(db, agent_id)
        
        # Check if agent exists
        # if not agent:
        #     raise HTTPException(
        #         status_code=http_status.HTTP_404_NOT_FOUND,
        #         detail=f"Agent with ID {agent_id} not found"
        #     )
        
        # Get summary metrics for the agent
        # In a real implementation, this would calculate metrics from telemetry data
        
        # For now, return mock data format
        response = {
            "agent_id": agent_id,
            "name": "Example Agent",
            "type": "assistant",
            "status": "active",
            "description": "An example agent",
            "created_at": datetime.utcnow() - timedelta(days=30),
            "updated_at": datetime.utcnow() - timedelta(days=1),
            "configuration": {
                "model": "gpt-4",
                "temperature": 0.7
            },
            "metrics": {
                "request_count": 1200,
                "token_usage": 45000,
                "avg_response_time_ms": 850,
                "tool_usage": 350,
                "error_count": 12
            }
        }
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting agent details: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting agent details: {str(e)}"
        )


@router.get(
    "/agents/{agent_id}/dashboard",
    response_model=AgentDashboardResponse,
    summary="Get agent dashboard data"
)
async def get_agent_dashboard(
    agent_id: str = Path(..., description="Agent ID"),
    time_range: str = Query("30d", description="Time range for metrics (1h, 1d, 7d, 30d)"),
    metrics: str = Query(None, description="Comma-separated list of metrics to include"),
    db: Session = Depends(get_db)
):
    """
    Get dashboard metrics for a specific agent over the specified time period.
    
    Returns:
        AgentDashboardResponse: Agent dashboard metrics
    """
    logger.info(f"Getting dashboard for agent: {agent_id}, time range: {time_range}")
    
    try:
        # Validate time_range
        if time_range not in ["1h", "1d", "7d", "30d"]:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid time_range value: {time_range}. Valid values are: 1h, 1d, 7d, 30d"
            )
            
        # Parse the TimeRange enum from string
        time_range_enum = None
        if time_range == "1h":
            time_range_enum = TimeRange.HOUR
        elif time_range == "1d":
            time_range_enum = TimeRange.DAY
        elif time_range == "7d":
            time_range_enum = TimeRange.WEEK
        elif time_range == "30d":
            time_range_enum = TimeRange.MONTH
            
        # Parse metrics filter if provided
        metrics_to_include = None
        if metrics:
            metrics_to_include = [m.strip() for m in metrics.split(',')]
            
        # Get dashboard metrics for the agent using the real analysis function
        dashboard_metrics = get_agent_dashboard_metrics(db, agent_id, time_range_enum)
        
        # Filter metrics if requested
        if metrics_to_include:
            dashboard_metrics = [m for m in dashboard_metrics if m.metric in metrics_to_include]
            
        # Construct response
        response = {
            "agent_id": agent_id,
            "period": f"Last {time_range}",
            "metrics": dashboard_metrics
        }
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting agent dashboard: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting agent dashboard: {str(e)}"
        )


@router.get(
    "/agents/{agent_id}/llms",
    response_model=LLMUsageResponse,
    summary="Get LLM usage for an agent"
)
def get_agent_llm_usage(
    agent_id: str = Path(..., description="Agent ID"),
    from_time: Optional[datetime] = Query(None, description="Start time (ISO format)"),
    to_time: Optional[datetime] = Query(None, description="End time (ISO format)"),
    time_range: str = Query("30d", description="Predefined time range (1h, 1d, 7d, 30d)"),
    db: Session = Depends(get_db)
):
    """
    Get LLM usage overview for a specific agent.
    
    Returns:
        LLMUsageResponse: LLM usage information
    """
    logger.info(f"Getting LLM usage for agent: {agent_id}")
    
    try:
        # Validate time_range
        if time_range and time_range not in ["1h", "1d", "7d", "30d"]:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid time_range value: {time_range}. Valid values are: 1h, 1d, 7d, 30d"
            )
            
        # Create time range params
        time_range_params = None
        if from_time and to_time:
            time_range_params = TimeRangeParams(start=from_time, end=to_time)
        elif time_range == "1h":
            time_range_params = TimeRangeParams.last_hour()
        elif time_range == "1d":
            time_range_params = TimeRangeParams.last_day()
        elif time_range == "7d":
            time_range_params = TimeRangeParams.last_week()
        elif time_range == "30d":
            time_range_params = TimeRangeParams.last_month()
            
        # Get LLM usage data for the agent using real analysis function with the alias
        llm_usage_data = analyze_agent_llm_usage(db, agent_id, time_range_params)
        
        # Add metadata to the response if not present
        if "meta" not in llm_usage_data:
            llm_usage_data["meta"] = {
                "timestamp": datetime.utcnow().isoformat(),
                "time_period": f"Last {time_range}" if not (from_time and to_time) else "Custom range"
            }
        
        # Ensure the response has the required fields for LLMUsageResponse
        if "items" not in llm_usage_data:
            llm_usage_data["items"] = []
        
        if "total_requests" not in llm_usage_data:
            llm_usage_data["total_requests"] = sum(item.get("request_count", 0) for item in llm_usage_data.get("items", []))
        
        if "total_tokens" not in llm_usage_data:
            llm_usage_data["total_tokens"] = sum(item.get("total_tokens", 0) for item in llm_usage_data.get("items", []))
        
        if "total_cost" not in llm_usage_data:
            llm_usage_data["total_cost"] = sum(item.get("estimated_cost", 0) for item in llm_usage_data.get("items", []))
        
        return llm_usage_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting agent LLM usage: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting agent LLM usage: {str(e)}"
        )


@router.get(
    "/agents/{agent_id}/llms/requests",
    response_model=LLMRequestsResponse,
    summary="Get LLM requests for an agent"
)
async def get_agent_llm_requests(
    agent_id: str = Path(..., description="Agent ID"),
    model: Optional[str] = Query(None, description="Filter by LLM model"),
    status: Optional[str] = Query(None, description="Filter by request status"),
    from_time: Optional[datetime] = Query(None, description="Start time (ISO format)"),
    to_time: Optional[datetime] = Query(None, description="End time (ISO format)"),
    time_range: str = Query("1d", description="Predefined time range (1h, 1d, 7d, 30d)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=1000, description="Items per page"),
    db: Session = Depends(get_db)
):
    """
    Get detailed LLM requests for a specific agent.
    
    Returns:
        LLMRequestsResponse: LLM request details
    """
    logger.info(f"Getting LLM requests for agent: {agent_id}")
    
    try:
        # Validate time_range
        if time_range and time_range not in ["1h", "1d", "7d", "30d"]:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid time_range value: {time_range}. Valid values are: 1h, 1d, 7d, 30d"
            )
            
        # Create time range params
        time_range_params = None
        if from_time and to_time:
            time_range_params = TimeRangeParams(start=from_time, end=to_time)
        elif time_range == "1h":
            time_range_params = TimeRangeParams.last_hour()
        elif time_range == "1d":
            time_range_params = TimeRangeParams.last_day()
        elif time_range == "7d":
            time_range_params = TimeRangeParams.last_week()
        elif time_range == "30d":
            time_range_params = TimeRangeParams.last_month()
            
        # Create pagination params
        pagination_params = PaginationParams(page=page, page_size=page_size)
        
        # Create filters
        filters = {}
        if model:
            filters["model"] = model
        if status:
            filters["status"] = status
            
        # Get LLM requests data for the agent using the real analysis function
        items, total = analyze_agent_llm_requests(
            db=db, 
            agent_id=agent_id, 
            time_range_params=time_range_params,
            filters=filters, 
            pagination_params=pagination_params
        )
        
        # Construct response
        response = {
            "items": items,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": (total + page_size - 1) // page_size,
                "has_next": page < ((total + page_size - 1) // page_size),
                "has_prev": page > 1
            },
            "meta": {
                "timestamp": datetime.utcnow().isoformat(),
                "time_period": f"Last {time_range}" if not (from_time and to_time) else f"Custom range",
                "filters_applied": filters
            }
        }
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting agent LLM requests: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting agent LLM requests: {str(e)}"
        )


@router.get(
    "/agents/{agent_id}/tokens",
    response_model=TokenUsageResponse,
    summary="Get token usage for an agent"
)
async def get_agent_token_usage(
    agent_id: str = Path(..., description="Agent ID"),
    from_time: Optional[datetime] = Query(None, description="Start time (ISO format)"),
    to_time: Optional[datetime] = Query(None, description="End time (ISO format)"),
    time_range: str = Query("7d", description="Predefined time range (1h, 1d, 7d, 30d)"),
    group_by: Optional[str] = Query(None, description="Group by field (model, time)"),
    interval: Optional[str] = Query("1d", description="Time interval for grouping (1h, 1d)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=1000, description="Items per page"),
    db: Session = Depends(get_db)
):
    """
    Get token usage metrics for a specific agent.
    
    Returns:
        TokenUsageResponse: Token usage metrics
    """
    logger.info(f"Getting token usage for agent: {agent_id}")
    
    try:
        # Validate time_range
        if time_range and time_range not in ["1h", "1d", "7d", "30d"]:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid time_range value: {time_range}. Valid values are: 1h, 1d, 7d, 30d"
            )
            
        # Validate interval
        if interval and interval not in ["1h", "1d"]:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid interval value: {interval}. Valid values are: 1h, 1d"
            )
            
        # Create time range params
        time_range_params = None
        if from_time and to_time:
            time_range_params = TimeRangeParams(start=from_time, end=to_time)
        elif time_range == "1h":
            time_range_params = TimeRangeParams.last_hour()
        elif time_range == "1d":
            time_range_params = TimeRangeParams.last_day()
        elif time_range == "7d":
            time_range_params = TimeRangeParams.last_week()
        elif time_range == "30d":
            time_range_params = TimeRangeParams.last_month()
            
        # Create pagination params
        pagination_params = PaginationParams(page=page, page_size=page_size)
        
        # Get token usage data for the agent using real analysis function
        token_usage_data = analyze_agent_token_usage(
            db, 
            agent_id, 
            time_range_params, 
            group_by=group_by, 
            interval=interval,
            pagination_params=pagination_params
        )
        
        # Add metadata to the response
        token_usage_data["meta"] = {
            "timestamp": datetime.utcnow().isoformat(),
            "time_period": f"Last {time_range}" if not (from_time and to_time) else "Custom range",
            "group_by": group_by
        }
        
        # Add pagination
        items = token_usage_data.get("items", [])
        total_items = len(items)
        
        token_usage_data["pagination"] = {
            "page": page,
            "page_size": page_size,
            "total": total_items,
            "total_pages": (total_items + page_size - 1) // page_size,
            "has_next": page < ((total_items + page_size - 1) // page_size),
            "has_prev": page > 1
        }
        
        return token_usage_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting agent token usage: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting agent token usage: {str(e)}"
        )


@router.get(
    "/agents/{agent_id}/tools",
    response_model=ToolUsageResponse,
    summary="Get tool usage for an agent"
)
async def get_agent_tool_usage(
    agent_id: str = Path(..., description="Agent ID"),
    from_time: Optional[datetime] = Query(None, description="Start time (ISO format)"),
    to_time: Optional[datetime] = Query(None, description="End time (ISO format)"),
    time_range: str = Query("30d", description="Predefined time range (1h, 1d, 7d, 30d)"),
    db: Session = Depends(get_db)
):
    """
    Get tool usage overview for a specific agent.
    
    Returns:
        ToolUsageResponse: Tool usage information
    """
    logger.info(f"Getting tool usage for agent: {agent_id}")
    
    try:
        # Validate time_range
        if time_range and time_range not in ["1h", "1d", "7d", "30d"]:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid time_range value: {time_range}. Valid values are: 1h, 1d, 7d, 30d"
            )
            
        # Create time range params
        time_range_params = None
        if from_time and to_time:
            time_range_params = TimeRangeParams(start=from_time, end=to_time)
        elif time_range == "1h":
            time_range_params = TimeRangeParams.last_hour()
        elif time_range == "1d":
            time_range_params = TimeRangeParams.last_day()
        elif time_range == "7d":
            time_range_params = TimeRangeParams.last_week()
        elif time_range == "30d":
            time_range_params = TimeRangeParams.last_month()
            
        # Get tool usage data for the agent using real analysis function
        tool_usage_data = analyze_agent_tool_usage(db, agent_id, time_range_params)
        
        # Add metadata to the response if not present
        if "meta" not in tool_usage_data:
            tool_usage_data["meta"] = {
                "timestamp": datetime.utcnow().isoformat(),
                "time_period": f"Last {time_range}" if not (from_time and to_time) else "Custom range"
            }
        
        # Ensure the response has the required fields for ToolUsageResponse
        if "items" not in tool_usage_data:
            tool_usage_data["items"] = []
            
        if "total_executions" not in tool_usage_data:
            tool_usage_data["total_executions"] = sum(item.get("execution_count", 0) for item in tool_usage_data.get("items", []))
            
        if "overall_success_rate" not in tool_usage_data:
            total_executions = tool_usage_data["total_executions"]
            total_success = sum(item.get("success_count", 0) for item in tool_usage_data.get("items", []))
            tool_usage_data["overall_success_rate"] = total_success / total_executions if total_executions > 0 else 0.0
        
        return tool_usage_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting agent tool usage: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting agent tool usage: {str(e)}"
        )


@router.get(
    "/agents/{agent_id}/tools/executions",
    response_model=ToolExecutionsResponse,
    summary="Get tool executions for an agent"
)
async def get_agent_tool_executions_route(
    agent_id: str = Path(..., description="Agent ID"),
    tool_name: Optional[str] = Query(None, description="Filter by tool name"),
    status: Optional[str] = Query(None, description="Filter by execution status"),
    from_time: Optional[datetime] = Query(None, description="Start time (ISO format)"),
    to_time: Optional[datetime] = Query(None, description="End time (ISO format)"),
    time_range: str = Query("1d", description="Predefined time range (1h, 1d, 7d, 30d)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=1000, description="Items per page"),
    db: Session = Depends(get_db)
):
    """
    Get detailed tool executions for a specific agent.
    
    Returns:
        ToolExecutionsResponse: Tool execution details
    """
    logger.info(f"Getting tool executions for agent: {agent_id}")
    
    try:
        # Validate time_range
        if time_range and time_range not in ["1h", "1d", "7d", "30d"]:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid time_range value: {time_range}. Valid values are: 1h, 1d, 7d, 30d"
            )
            
        # Create time range params
        time_range_params = None
        if from_time and to_time:
            time_range_params = TimeRangeParams(start=from_time, end=to_time)
        elif time_range == "1h":
            time_range_params = TimeRangeParams.last_hour()
        elif time_range == "1d":
            time_range_params = TimeRangeParams.last_day()
        elif time_range == "7d":
            time_range_params = TimeRangeParams.last_week()
        elif time_range == "30d":
            time_range_params = TimeRangeParams.last_month()
            
        # Create filters
        filters = {}
        if tool_name:
            filters["tool_name"] = tool_name
        if status:
            filters["status"] = status
            
        # Create pagination params
        pagination_params = PaginationParams(page=page, page_size=page_size)
        
        # Get tool executions data for the agent using real analysis function
        # Note: The analysis function is not async, so no need to await it
        executions, total_count = get_agent_tool_executions(
            db, 
            agent_id, 
            time_range_params, 
            filters, 
            pagination_params
        )
        
        # Construct response
        response = {
            "items": executions,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total_count,
                "total_pages": (total_count + page_size - 1) // page_size,
                "has_next": page < ((total_count + page_size - 1) // page_size),
                "has_prev": page > 1
            },
            "meta": {
                "timestamp": datetime.utcnow().isoformat(),
                "time_period": f"Last {time_range}" if not (from_time and to_time) else "Custom range",
                "filters_applied": filters
            }
        }
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting agent tool executions: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting agent tool executions: {str(e)}"
        )


@router.get(
    "/agents/{agent_id}/sessions",
    response_model=SessionsResponse,
    summary="Get sessions for an agent"
)
async def get_agent_sessions_route(
    agent_id: str = Path(..., description="Agent ID"),
    status: Optional[str] = Query(None, description="Filter by session status"),
    min_duration: Optional[int] = Query(None, description="Minimum duration in seconds"),
    max_duration: Optional[int] = Query(None, description="Maximum duration in seconds"),
    from_time: Optional[datetime] = Query(None, description="Start time (ISO format)"),
    to_time: Optional[datetime] = Query(None, description="End time (ISO format)"),
    time_range: str = Query("7d", description="Predefined time range (1h, 1d, 7d, 30d)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=1000, description="Items per page"),
    db: Session = Depends(get_db)
):
    """
    Get sessions for a specific agent.
    
    Returns:
        SessionsResponse: List of sessions
    """
    logger.info(f"Getting sessions for agent: {agent_id}")
    
    try:
        # Validate time_range
        if time_range and time_range not in ["1h", "1d", "7d", "30d"]:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid time_range value: {time_range}. Valid values are: 1h, 1d, 7d, 30d"
            )
            
        # Create time range params
        time_range_params = None
        if from_time and to_time:
            time_range_params = TimeRangeParams(start=from_time, end=to_time)
        elif time_range == "1h":
            time_range_params = TimeRangeParams.last_hour()
        elif time_range == "1d":
            time_range_params = TimeRangeParams.last_day()
        elif time_range == "7d":
            time_range_params = TimeRangeParams.last_week()
        elif time_range == "30d":
            time_range_params = TimeRangeParams.last_month()
            
        # Create filters
        filters = {}
        if status:
            filters["status"] = status
        if min_duration is not None:
            filters["min_duration"] = min_duration
        if max_duration is not None:
            filters["max_duration"] = max_duration
            
        # Create pagination params
        pagination_params = PaginationParams(page=page, page_size=page_size)
        
        # Get sessions data for the agent using real analysis function
        # Note: The analysis function is synchronous, not an async coroutine
        sessions_data, total_count = get_agent_sessions(
            db, 
            agent_id, 
            time_range_params, 
            filters, 
            pagination_params
        )
        
        # Construct response
        response = {
            "items": sessions_data,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total_count,
                "pages": (total_count + page_size - 1) // page_size
            },
            "meta": {
                "timestamp": datetime.utcnow().isoformat(),
                "time_period": f"Last {time_range}" if not (from_time and to_time) else "Custom range"
            }
        }
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting agent sessions: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting agent sessions: {str(e)}"
        )


@router.get(
    "/agents/{agent_id}/traces",
    response_model=TracesResponse,
    summary="Get traces for an agent"
)
async def get_agent_traces_route(
    agent_id: str = Path(..., description="Agent ID"),
    status: Optional[str] = Query(None, description="Filter by trace status"),
    event_type: Optional[str] = Query(None, description="Filter by initial event type"),
    min_duration: Optional[int] = Query(None, description="Minimum duration in milliseconds"),
    max_duration: Optional[int] = Query(None, description="Maximum duration in milliseconds"),
    from_time: Optional[datetime] = Query(None, description="Start time (ISO format)"),
    to_time: Optional[datetime] = Query(None, description="End time (ISO format)"),
    time_range: str = Query("7d", description="Predefined time range (1h, 1d, 7d, 30d)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=1000, description="Items per page"),
    db: Session = Depends(get_db)
):
    """
    Get traces for a specific agent.
    
    Returns:
        TracesResponse: List of traces
    """
    logger.info(f"Getting traces for agent: {agent_id}")
    
    try:
        # Validate time_range
        if time_range and time_range not in ["1h", "1d", "7d", "30d"]:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid time_range value: {time_range}. Valid values are: 1h, 1d, 7d, 30d"
            )
            
        # Create time range params
        time_range_params = None
        if from_time and to_time:
            time_range_params = TimeRangeParams(start=from_time, end=to_time)
        elif time_range == "1h":
            time_range_params = TimeRangeParams.last_hour()
        elif time_range == "1d":
            time_range_params = TimeRangeParams.last_day()
        elif time_range == "7d":
            time_range_params = TimeRangeParams.last_week()
        elif time_range == "30d":
            time_range_params = TimeRangeParams.last_month()
            
        # Create filters
        filters = {}
        if status:
            filters["status"] = status
        if event_type:
            filters["event_type"] = event_type
        if min_duration is not None:
            filters["min_duration"] = min_duration
        if max_duration is not None:
            filters["max_duration"] = max_duration
            
        # Create pagination params
        pagination_params = PaginationParams(page=page, page_size=page_size)
        
        # Get traces data for the agent using real analysis function
        # Note: The analysis function is synchronous, not an async coroutine
        traces_data, total_count = get_agent_traces(
            db, 
            agent_id, 
            time_range_params, 
            filters, 
            pagination_params
        )
        
        # Construct response
        response = {
            "items": traces_data,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total_count,
                "pages": (total_count + page_size - 1) // page_size
            },
            "meta": {
                "timestamp": datetime.utcnow().isoformat(),
                "time_period": f"Last {time_range}" if not (from_time and to_time) else "Custom range"
            }
        }
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting agent traces: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting agent traces: {str(e)}"
        )


@router.get(
    "/agents/{agent_id}/alerts",
    response_model=AlertsResponse,
    summary="Get security alerts for an agent"
)
async def get_agent_alerts_route(
    agent_id: str = Path(..., description="Agent ID"),
    severity: Optional[str] = Query(None, description="Filter by alert severity"),
    type: Optional[str] = Query(None, description="Filter by alert type"),
    status: Optional[str] = Query(None, description="Filter by alert status"),
    from_time: Optional[datetime] = Query(None, description="Start time (ISO format)"),
    to_time: Optional[datetime] = Query(None, description="End time (ISO format)"),
    time_range: str = Query("7d", description="Predefined time range (1h, 1d, 7d, 30d)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=1000, description="Items per page"),
    db: Session = Depends(get_db)
):
    """
    Get security alerts for a specific agent.
    
    Returns:
        AlertsResponse: List of security alerts
    """
    logger.info(f"Getting alerts for agent: {agent_id}")
    
    try:
        # Validate time_range
        if time_range and time_range not in ["1h", "1d", "7d", "30d"]:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid time_range value: {time_range}. Valid values are: 1h, 1d, 7d, 30d"
            )
            
        # Create time range params
        time_range_params = None
        if from_time and to_time:
            time_range_params = TimeRangeParams(start=from_time, end=to_time)
        elif time_range == "1h":
            time_range_params = TimeRangeParams.last_hour()
        elif time_range == "1d":
            time_range_params = TimeRangeParams.last_day()
        elif time_range == "7d":
            time_range_params = TimeRangeParams.last_week()
        elif time_range == "30d":
            time_range_params = TimeRangeParams.last_month()
            
        # Create filters
        filters = {}
        if severity:
            filters["severity"] = severity
        if type:
            filters["type"] = type
        if status:
            filters["status"] = status
            
        # Create pagination params
        pagination_params = PaginationParams(page=page, page_size=page_size)
        
        # Get alerts data for the agent using real analysis function
        # Note: The analysis function is synchronous, not an async coroutine
        alerts_data, total_count = get_agent_alerts(
            db, 
            agent_id, 
            time_range_params, 
            filters, 
            pagination_params
        )
        
        # Construct response
        response = {
            "items": alerts_data,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total_count,
                "pages": (total_count + page_size - 1) // page_size
            },
            "meta": {
                "timestamp": datetime.utcnow().isoformat(),
                "time_period": f"Last {time_range}" if not (from_time and to_time) else "Custom range"
            }
        }
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting agent security alerts: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting agent security alerts: {str(e)}"
        ) 