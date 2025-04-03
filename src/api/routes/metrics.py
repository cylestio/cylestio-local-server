from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, timedelta

from src.database.session import get_db
from src.utils.logging import get_logger
from src.api.schemas.metrics import (
    MetricQuery,
    MetricResponse,
    DashboardResponse,
    TimeRange
)
from src.analysis.interface import get_metric, get_dashboard_metrics

logger = get_logger(__name__)
router = APIRouter()

# Dashboard endpoint
@router.get(
    "/dashboard",
    response_model=DashboardResponse,
    summary="Get main dashboard metrics"
)
async def get_dashboard(
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    time_range: str = Query("30d", description="Time range (1h, 1d, 7d, 30d)"),
    metrics: Optional[str] = Query(None, description="Comma-separated list of metrics to include"),
    db: Session = Depends(get_db)
):
    """
    Get key system-wide metrics for the dashboard with trend information.
    
    This endpoint provides aggregated metrics across all monitored agents,
    including trends comparing to the previous period.
    
    Args:
        agent_id: Optional agent ID to filter by
        time_range: Time range for metrics (1h, 1d, 7d, 30d)
        metrics: Optional comma-separated list of metrics to include
        
    Returns:
        DashboardResponse: Dashboard metrics with trend information
    """
    logger.info(f"Getting dashboard metrics, time range: {time_range}")
    
    # Validate time_range
    if time_range not in ["1h", "1d", "7d", "30d"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid time_range value: {time_range}. Valid values are: 1h, 1d, 7d, 30d"
        )
    
    # Parse metrics list if provided
    metric_list = None
    if metrics:
        metric_list = [m.strip() for m in metrics.split(',')]
    
    try:
        # Convert string time_range to TimeRange enum
        time_range_enum = None
        if time_range == "1h":
            time_range_enum = TimeRange.HOUR
        elif time_range == "1d":
            time_range_enum = TimeRange.DAY
        elif time_range == "7d":
            time_range_enum = TimeRange.WEEK
        elif time_range == "30d":
            time_range_enum = TimeRange.MONTH
        
        # Get dashboard metrics from analysis layer
        dashboard_data = get_dashboard_metrics(time_range_enum, agent_id, db)
        
        # Filter metrics if requested
        if metric_list:
            dashboard_data.metrics = [m for m in dashboard_data.metrics if m.metric in metric_list]
            
        return dashboard_data
        
    except Exception as e:
        logger.error(f"Error getting dashboard metrics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving dashboard metrics: {str(e)}"
        )

# Individual metric endpoints
@router.get(
    "/metrics/llm/request_count",
    response_model=MetricResponse,
    summary="Get LLM request count metrics"
)
async def get_llm_request_count(
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    from_time: Optional[datetime] = Query(None, description="Start time (ISO format)"),
    to_time: Optional[datetime] = Query(None, description="End time (ISO format)"),
    time_range: Optional[str] = Query("30d", description="Predefined time range (1h, 1d, 7d, 30d)"),
    interval: Optional[str] = Query(None, description="Aggregation interval (1m, 1h, 1d, 7d)"),
    dimensions: Optional[str] = Query(None, description="Comma-separated list of dimensions to group by"),
    db: Session = Depends(get_db)
):
    """
    Get LLM request count metrics with optional filtering and grouping.
    
    Returns:
        MetricResponse: LLM request count data points
    """
    logger.info("Querying LLM request count metrics")
    
    # Parse dimensions if provided
    dimension_list = None
    if dimensions:
        dimension_list = [d.strip() for d in dimensions.split(',')]
    
    # Validate time_range if provided
    if time_range and time_range not in ["1h", "1d", "7d", "30d"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid time_range value: {time_range}. Valid values are: 1h, 1d, 7d, 30d"
        )
    
    # Create query object
    query = MetricQuery(
        metric="llm_request_count",
        agent_id=agent_id,
        from_time=from_time,
        to_time=to_time,
        time_range=time_range,  # Pass the string directly
        interval=interval,
        dimensions=dimension_list
    )
    
    try:
        # Get metric data
        metric_data = get_metric(query, db)
        return metric_data
        
    except Exception as e:
        logger.error(f"Error getting LLM request count metrics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving LLM request count metrics: {str(e)}"
        )

@router.get(
    "/metrics/llm/token_usage",
    response_model=MetricResponse,
    summary="Get LLM token usage metrics"
)
async def get_llm_token_usage(
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    from_time: Optional[datetime] = Query(None, description="Start time (ISO format)"),
    to_time: Optional[datetime] = Query(None, description="End time (ISO format)"),
    time_range: Optional[str] = Query("30d", description="Predefined time range (1h, 1d, 7d, 30d)"),
    interval: Optional[str] = Query(None, description="Aggregation interval (1m, 1h, 1d, 7d)"),
    dimensions: Optional[str] = Query(None, description="Comma-separated list of dimensions to group by"),
    db: Session = Depends(get_db)
):
    """
    Get LLM token usage metrics with optional filtering and grouping.
    
    Returns:
        MetricResponse: LLM token usage data points
    """
    logger.info("Querying LLM token usage metrics")
    
    # Parse dimensions if provided
    dimension_list = None
    if dimensions:
        dimension_list = [d.strip() for d in dimensions.split(',')]
    
    # Validate time_range if provided
    if time_range and time_range not in ["1h", "1d", "7d", "30d"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid time_range value: {time_range}. Valid values are: 1h, 1d, 7d, 30d"
        )
    
    # Create query object
    query = MetricQuery(
        metric="llm_token_usage",
        agent_id=agent_id,
        from_time=from_time,
        to_time=to_time,
        time_range=time_range,  # Pass the string directly
        interval=interval,
        dimensions=dimension_list
    )
    
    try:
        # Get metric data
        metric_data = get_metric(query, db)
        return metric_data
        
    except Exception as e:
        logger.error(f"Error getting LLM token usage metrics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving LLM token usage metrics: {str(e)}"
        )

@router.get(
    "/metrics/llm/response_time",
    response_model=MetricResponse,
    summary="Get LLM response time metrics"
)
async def get_llm_response_time(
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    from_time: Optional[datetime] = Query(None, description="Start time (ISO format)"),
    to_time: Optional[datetime] = Query(None, description="End time (ISO format)"),
    time_range: Optional[str] = Query("30d", description="Predefined time range (1h, 1d, 7d, 30d)"),
    interval: Optional[str] = Query(None, description="Aggregation interval (1m, 1h, 1d, 7d)"),
    dimensions: Optional[str] = Query(None, description="Comma-separated list of dimensions to group by"),
    db: Session = Depends(get_db)
):
    """
    Get LLM response time metrics with optional filtering and grouping.
    
    Returns:
        MetricResponse: LLM response time data points
    """
    logger.info("Querying LLM response time metrics")
    
    # Parse dimensions if provided
    dimension_list = None
    if dimensions:
        dimension_list = [d.strip() for d in dimensions.split(',')]
    
    # Validate time_range if provided
    if time_range and time_range not in ["1h", "1d", "7d", "30d"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid time_range value: {time_range}. Valid values are: 1h, 1d, 7d, 30d"
        )
    
    # Create query object
    query = MetricQuery(
        metric="llm_response_time",
        agent_id=agent_id,
        from_time=from_time,
        to_time=to_time,
        time_range=time_range,  # Pass the string directly
        interval=interval,
        dimensions=dimension_list
    )
    
    try:
        # Get metric data
        metric_data = get_metric(query, db)
        return metric_data
        
    except Exception as e:
        logger.error(f"Error getting LLM response time metrics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving LLM response time metrics: {str(e)}"
        )

@router.get(
    "/metrics/tool/execution_count",
    response_model=MetricResponse,
    summary="Get tool execution count metrics"
)
async def get_tool_execution_count(
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    from_time: Optional[datetime] = Query(None, description="Start time (ISO format)"),
    to_time: Optional[datetime] = Query(None, description="End time (ISO format)"),
    time_range: Optional[str] = Query("30d", description="Predefined time range (1h, 1d, 7d, 30d)"),
    interval: Optional[str] = Query(None, description="Aggregation interval (1m, 1h, 1d, 7d)"),
    dimensions: Optional[str] = Query(None, description="Comma-separated list of dimensions to group by"),
    db: Session = Depends(get_db)
):
    """
    Get tool execution count metrics with optional filtering and grouping.
    
    Returns:
        MetricResponse: Tool execution count data points
    """
    logger.info("Querying tool execution count metrics")
    
    # Parse dimensions if provided
    dimension_list = None
    if dimensions:
        dimension_list = [d.strip() for d in dimensions.split(',')]
    
    # Validate time_range if provided
    if time_range and time_range not in ["1h", "1d", "7d", "30d"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid time_range value: {time_range}. Valid values are: 1h, 1d, 7d, 30d"
        )
    
    # Create query object
    query = MetricQuery(
        metric="tool_execution_count",
        agent_id=agent_id,
        from_time=from_time,
        to_time=to_time,
        time_range=time_range,  # Pass the string directly
        interval=interval,
        dimensions=dimension_list
    )
    
    try:
        # Get metric data
        metric_data = get_metric(query, db)
        return metric_data
        
    except Exception as e:
        logger.error(f"Error getting tool execution count metrics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving tool execution count metrics: {str(e)}"
        )

@router.get(
    "/metrics/tool/success_rate",
    response_model=MetricResponse,
    summary="Get tool success rate metrics"
)
async def get_tool_success_rate(
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    from_time: Optional[datetime] = Query(None, description="Start time (ISO format)"),
    to_time: Optional[datetime] = Query(None, description="End time (ISO format)"),
    time_range: Optional[str] = Query(None, description="Predefined time range (1h, 1d, 7d, 30d)"),
    interval: Optional[str] = Query(None, description="Aggregation interval (1m, 1h, 1d, 7d)"),
    dimensions: Optional[str] = Query(None, description="Comma-separated list of dimensions to group by"),
    db: Session = Depends(get_db)
):
    """
    Get tool success rate metrics with optional filtering and grouping.
    
    Returns:
        MetricResponse: Tool success rate data points
    """
    logger.info("Querying tool success rate metrics")
    
    # Parse dimensions if provided
    dimension_list = None
    if dimensions:
        dimension_list = [d.strip() for d in dimensions.split(',')]
    
    # Validate time_range if provided
    if time_range and time_range not in ["1h", "1d", "7d", "30d"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid time_range value: {time_range}. Valid values are: 1h, 1d, 7d, 30d"
        )
    
    # Create query object
    query = MetricQuery(
        metric="tool_success_rate",
        agent_id=agent_id,
        from_time=from_time,
        to_time=to_time,
        time_range=time_range,  # Pass the string directly
        interval=interval,
        dimensions=dimension_list
    )
    
    try:
        # Get metric data
        metric_data = get_metric(query, db)
        return metric_data
        
    except Exception as e:
        logger.error(f"Error getting tool success rate metrics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving tool success rate metrics: {str(e)}"
        )

@router.get(
    "/metrics/error/count",
    response_model=MetricResponse,
    summary="Get error count metrics"
)
async def get_error_count(
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    from_time: Optional[datetime] = Query(None, description="Start time (ISO format)"),
    to_time: Optional[datetime] = Query(None, description="End time (ISO format)"),
    time_range: Optional[str] = Query("30d", description="Predefined time range (1h, 1d, 7d, 30d)"),
    interval: Optional[str] = Query(None, description="Aggregation interval (1m, 1h, 1d, 7d)"),
    dimensions: Optional[str] = Query(None, description="Comma-separated list of dimensions to group by"),
    db: Session = Depends(get_db)
):
    """
    Get error count metrics with optional filtering and grouping.
    
    Returns:
        MetricResponse: Error count data points
    """
    logger.info("Querying error count metrics")
    
    # Parse dimensions if provided
    dimension_list = None
    if dimensions:
        dimension_list = [d.strip() for d in dimensions.split(',')]
    
    # Validate time_range if provided
    if time_range and time_range not in ["1h", "1d", "7d", "30d"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid time_range value: {time_range}. Valid values are: 1h, 1d, 7d, 30d"
        )
    
    # Create query object
    query = MetricQuery(
        metric="error_count",
        agent_id=agent_id,
        from_time=from_time,
        to_time=to_time,
        time_range=time_range,  # Pass the string directly
        interval=interval,
        dimensions=dimension_list
    )
    
    try:
        # Get metric data
        metric_data = get_metric(query, db)
        return metric_data
        
    except Exception as e:
        logger.error(f"Error getting error count metrics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving error count metrics: {str(e)}"
        )

@router.get(
    "/metrics/session/count",
    response_model=MetricResponse,
    summary="Get session count metrics"
)
async def get_session_count(
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    from_time: Optional[datetime] = Query(None, description="Start time (ISO format)"),
    to_time: Optional[datetime] = Query(None, description="End time (ISO format)"),
    time_range: Optional[str] = Query("30d", description="Predefined time range (1h, 1d, 7d, 30d)"),
    interval: Optional[str] = Query(None, description="Aggregation interval (1m, 1h, 1d, 7d)"),
    dimensions: Optional[str] = Query(None, description="Comma-separated list of dimensions to group by"),
    db: Session = Depends(get_db)
):
    """
    Get session count metrics with optional filtering and grouping.
    
    Returns:
        MetricResponse: Session count data points
    """
    logger.info("Querying session count metrics")
    
    # Parse dimensions if provided
    dimension_list = None
    if dimensions:
        dimension_list = [d.strip() for d in dimensions.split(',')]
    
    # Validate time_range if provided
    if time_range and time_range not in ["1h", "1d", "7d", "30d"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid time_range value: {time_range}. Valid values are: 1h, 1d, 7d, 30d"
        )
    
    # Create query object
    query = MetricQuery(
        metric="session_count",
        agent_id=agent_id,
        from_time=from_time,
        to_time=to_time,
        time_range=time_range,  # Pass the string directly
        interval=interval,
        dimensions=dimension_list
    )
    
    try:
        # Get metric data
        metric_data = get_metric(query, db)
        return metric_data
        
    except Exception as e:
        logger.error(f"Error getting session count metrics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving session count metrics: {str(e)}"
        )

@router.get(
    "/metrics/agent/{agent_id}",
    response_model=Dict[str, Any],
    summary="Get all metrics for a specific agent"
)
async def get_agent_metrics(
    agent_id: str = Path(..., description="Agent ID to get metrics for"),
    time_range: str = Query("30d", description="Time range (1h, 1d, 7d, 30d)"),
    db: Session = Depends(get_db)
):
    """
    Get all metrics for a specific agent.
    
    Args:
        agent_id: Agent ID to get metrics for
        time_range: Time range for the metrics
        
    Returns:
        Dict[str, Any]: Dictionary containing all metrics for the agent
    """
    logger.info(f"Getting metrics for agent {agent_id}, time range: {time_range}")
    
    # Validate time_range if provided
    if time_range and time_range not in ["1h", "1d", "7d", "30d"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid time_range value: {time_range}. Valid values are: 1h, 1d, 7d, 30d"
        )
    
    # Initialize metrics object
    metrics = {}
    error_messages = []
    
    try:
        # Get metrics individually, catching errors for individual metrics
        try:
            llm_request_metric = get_metric(
                MetricQuery(metric="llm_request_count", agent_id=agent_id, time_range=time_range),
                db
            )
            metrics["llm_requests"] = _extract_metric_value(llm_request_metric)
        except Exception as e:
            logger.error(f"Error getting llm_request_count metric: {str(e)}")
            error_messages.append(f"llm_request_count: {str(e)}")
            metrics["llm_requests"] = 0
        
        try:
            token_usage_metric = get_metric(
                MetricQuery(metric="llm_token_usage", agent_id=agent_id, time_range=time_range),
                db
            )
            metrics["token_usage"] = _extract_metric_value(token_usage_metric)
        except Exception as e:
            logger.error(f"Error getting llm_token_usage metric: {str(e)}")
            error_messages.append(f"llm_token_usage: {str(e)}")
            metrics["token_usage"] = 0
        
        try:
            tool_execution_metric = get_metric(
                MetricQuery(metric="tool_execution_count", agent_id=agent_id, time_range=time_range),
                db
            )
            metrics["tool_executions"] = _extract_metric_value(tool_execution_metric)
        except Exception as e:
            logger.error(f"Error getting tool_execution_count metric: {str(e)}")
            error_messages.append(f"tool_execution_count: {str(e)}")
            metrics["tool_executions"] = 0
        
        try:
            error_count_metric = get_metric(
                MetricQuery(metric="error_count", agent_id=agent_id, time_range=time_range),
                db
            )
            metrics["errors"] = _extract_metric_value(error_count_metric)
        except Exception as e:
            logger.error(f"Error getting error_count metric: {str(e)}")
            error_messages.append(f"error_count: {str(e)}")
            metrics["errors"] = 0
        
        # Combine into a single response
        response = {
            "agent_id": agent_id,
            "time_range": time_range,
            "metrics": metrics
        }
        
        # Add errors if any
        if error_messages:
            response["error_details"] = error_messages
            
        return response
        
    except Exception as e:
        logger.error(f"Error getting agent metrics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving agent metrics: {str(e)}"
        )

def _extract_metric_value(metric_response: MetricResponse) -> Union[int, float]:
    """Helper function to extract the total value from a metric response"""
    if metric_response.data and len(metric_response.data) > 0:
        # Sum values if multiple data points
        return sum(point.value for point in metric_response.data)
    return 0 

# Aggregated system-wide metrics endpoints

@router.get(
    "/metrics/llms",
    response_model=MetricResponse,
    summary="Get aggregated LLM usage metrics"
)
async def get_aggregated_llm_metrics(
    from_time: Optional[datetime] = Query(None, description="Start time (ISO format)"),
    to_time: Optional[datetime] = Query(None, description="End time (ISO format)"),
    time_range: Optional[str] = Query("30d", description="Predefined time range (1h, 1d, 7d, 30d)"),
    interval: Optional[str] = Query(None, description="Aggregation interval (1m, 1h, 1d, 7d)"),
    dimensions: Optional[str] = Query("llm.model", description="Comma-separated list of dimensions to group by (default: llm.model)"),
    db: Session = Depends(get_db)
):
    """
    Get aggregated LLM usage metrics across all agents, with breakdown by model.
    
    This endpoint provides a comprehensive view of LLM usage across the system,
    including total requests, tokens, and costs. Results can be grouped by 
    different dimensions like model, vendor, etc.
    
    Returns:
        MetricResponse: Aggregated LLM usage data points
    """
    logger.info("Querying aggregated LLM usage metrics")
    
    # Parse dimensions if provided
    dimension_list = None
    if dimensions:
        dimension_list = [d.strip() for d in dimensions.split(',')]
    
    # Validate time_range if provided
    if time_range and time_range not in ["1h", "1d", "7d", "30d"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid time_range value: {time_range}. Valid values are: 1h, 1d, 7d, 30d"
        )
    
    # Create query object - primarily use llm_request_count but with appropriate dimensions
    query = MetricQuery(
        metric="llm_request_count",
        from_time=from_time,
        to_time=to_time,
        time_range=time_range,
        interval=interval,
        dimensions=dimension_list
    )
    
    try:
        # Get metric data
        metric_data = get_metric(query, db)
        
        # Adjust the metric name for clarity in response
        metric_data.metric = "llm_aggregated_usage"
        
        return metric_data
        
    except Exception as e:
        logger.error(f"Error getting aggregated LLM usage metrics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving aggregated LLM usage metrics: {str(e)}"
        )

@router.get(
    "/metrics/llms/requests",
    response_model=MetricResponse,
    summary="Get LLM request metrics across all agents"
)
async def get_llm_requests_metrics(
    from_time: Optional[datetime] = Query(None, description="Start time (ISO format)"),
    to_time: Optional[datetime] = Query(None, description="End time (ISO format)"),
    time_range: Optional[str] = Query("30d", description="Predefined time range (1h, 1d, 7d, 30d)"),
    interval: Optional[str] = Query("1d", description="Aggregation interval (1m, 1h, 1d, 7d)"),
    group_by: Optional[str] = Query(None, description="Dimension to group by (model, agent_id, status)"),
    db: Session = Depends(get_db)
):
    """
    Get LLM request metrics across all agents with time series data.
    
    This endpoint provides time series data for request volume,
    with optional grouping by model, agent, or status.
    
    Returns:
        MetricResponse: LLM request time series data
    """
    logger.info("Querying LLM request metrics with time series")
    
    # Parse group_by if provided to create dimensions list
    dimension_list = None
    if group_by:
        # Map frontend-friendly names to actual dimension names
        dimension_map = {
            "model": "llm.model",
            "agent": "agent_id",
            "status": "status"
        }
        # Get the actual dimension name or use as-is if not in map
        actual_dimension = dimension_map.get(group_by, group_by)
        dimension_list = [actual_dimension]
    
    # Validate time_range if provided
    if time_range and time_range not in ["1h", "1d", "7d", "30d"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid time_range value: {time_range}. Valid values are: 1h, 1d, 7d, 30d"
        )
    
    # Create query object
    query = MetricQuery(
        metric="llm_request_count",
        from_time=from_time,
        to_time=to_time,
        time_range=time_range,
        interval=interval,
        dimensions=dimension_list
    )
    
    try:
        # Get metric data
        metric_data = get_metric(query, db)
        return metric_data
        
    except Exception as e:
        logger.error(f"Error getting LLM request metrics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving LLM request metrics: {str(e)}"
        )

@router.get(
    "/metrics/tokens",
    response_model=MetricResponse,
    summary="Get system-wide token usage metrics"
)
async def get_system_token_metrics(
    from_time: Optional[datetime] = Query(None, description="Start time (ISO format)"),
    to_time: Optional[datetime] = Query(None, description="End time (ISO format)"),
    time_range: Optional[str] = Query("30d", description="Predefined time range (1h, 1d, 7d, 30d)"),
    interval: Optional[str] = Query("1d", description="Aggregation interval (1m, 1h, 1d, 7d)"),
    group_by: Optional[str] = Query(None, description="Dimension to group by (model, agent)"),
    db: Session = Depends(get_db)
):
    """
    Get system-wide token usage metrics with breakdown options.
    
    This endpoint provides token usage analytics across all agents,
    including input/output token counts and estimated costs.
    
    Returns:
        MetricResponse: Token usage data across the system
    """
    logger.info("Querying system-wide token usage metrics")
    
    # Parse group_by if provided to create dimensions list
    dimension_list = None
    if group_by:
        # Map frontend-friendly names to actual dimension names
        dimension_map = {
            "model": "llm.model",
            "agent": "agent_id"
        }
        # Get the actual dimension name or use as-is if not in map
        actual_dimension = dimension_map.get(group_by, group_by)
        dimension_list = [actual_dimension]
    
    # Validate time_range if provided
    if time_range and time_range not in ["1h", "1d", "7d", "30d"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid time_range value: {time_range}. Valid values are: 1h, 1d, 7d, 30d"
        )
    
    # Create query object
    query = MetricQuery(
        metric="llm_token_usage",
        from_time=from_time,
        to_time=to_time,
        time_range=time_range,
        interval=interval,
        dimensions=dimension_list
    )
    
    try:
        # Get metric data
        metric_data = get_metric(query, db)
        return metric_data
        
    except Exception as e:
        logger.error(f"Error getting system token usage metrics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving system token usage metrics: {str(e)}"
        )

# Tool usage metrics endpoints

@router.get(
    "/metrics/tools",
    response_model=MetricResponse,
    summary="Get aggregated tool usage analytics"
)
async def get_tool_usage_metrics(
    from_time: Optional[datetime] = Query(None, description="Start time (ISO format)"),
    to_time: Optional[datetime] = Query(None, description="End time (ISO format)"),
    time_range: Optional[str] = Query("30d", description="Predefined time range (1h, 1d, 7d, 30d)"),
    interval: Optional[str] = Query(None, description="Aggregation interval (1m, 1h, 1d, 7d)"),
    group_by: Optional[str] = Query("tool.name", description="Dimension to group by (default: tool.name)"),
    db: Session = Depends(get_db)
):
    """
    Get aggregated tool usage analytics across all agents.
    
    This endpoint provides data on the most-used tools across all agents,
    including success rates and execution counts.
    
    Returns:
        MetricResponse: Aggregated tool usage data
    """
    logger.info("Querying aggregated tool usage metrics")
    
    # Parse group_by to create dimensions list
    dimension_list = None
    if group_by:
        # Map frontend-friendly names to actual dimension names
        dimension_map = {
            "tool": "tool.name",
            "agent": "agent_id",
            "status": "status"
        }
        # Get the actual dimension name or use as-is if not in map
        actual_dimension = dimension_map.get(group_by, group_by)
        dimension_list = [actual_dimension]
    
    # Validate time_range if provided
    if time_range and time_range not in ["1h", "1d", "7d", "30d"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid time_range value: {time_range}. Valid values are: 1h, 1d, 7d, 30d"
        )
    
    # Create query object
    query = MetricQuery(
        metric="tool_execution_count",
        from_time=from_time,
        to_time=to_time,
        time_range=time_range,
        interval=interval,
        dimensions=dimension_list
    )
    
    try:
        # Get metric data
        metric_data = get_metric(query, db)
        
        # Adjust the metric name for clarity in response
        metric_data.metric = "tool_usage_analytics"
        
        return metric_data
        
    except Exception as e:
        logger.error(f"Error getting tool usage metrics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving tool usage metrics: {str(e)}"
        )

@router.get(
    "/metrics/tools/executions",
    response_model=MetricResponse,
    summary="Get tool execution metrics over time"
)
async def get_tool_execution_metrics(
    from_time: Optional[datetime] = Query(None, description="Start time (ISO format)"),
    to_time: Optional[datetime] = Query(None, description="End time (ISO format)"),
    time_range: Optional[str] = Query("30d", description="Predefined time range (1h, 1d, 7d, 30d)"),
    interval: Optional[str] = Query("1d", description="Aggregation interval (1m, 1h, 1d, 7d)"),
    tool_name: Optional[str] = Query(None, description="Filter by specific tool name"),
    status: Optional[str] = Query(None, description="Filter by execution status (success, error)"),
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    db: Session = Depends(get_db)
):
    """
    Get tool execution metrics over time with filtering options.
    
    This endpoint provides time series data for tool execution volume,
    with optional filtering by tool name, status, or agent.
    
    Returns:
        MetricResponse: Tool execution time series data
    """
    logger.info("Querying tool execution metrics over time")
    
    # Build filters based on parameters
    filters = {}
    if tool_name:
        filters["tool.name"] = tool_name
    if status:
        filters["status"] = status
    
    # Determine dimensions based on filters
    dimension_list = ["tool.name"]
    
    # Validate time_range if provided
    if time_range and time_range not in ["1h", "1d", "7d", "30d"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid time_range value: {time_range}. Valid values are: 1h, 1d, 7d, 30d"
        )
    
    # Create query object
    query = MetricQuery(
        metric="tool_execution_count",
        agent_id=agent_id,
        from_time=from_time,
        to_time=to_time,
        time_range=time_range,
        interval=interval,
        dimensions=dimension_list
    )
    
    try:
        # Get metric data
        metric_data = get_metric(query, db)
        
        # Filter data points if we have filters
        if filters:
            filtered_data = []
            for point in metric_data.data:
                include = True
                for key, value in filters.items():
                    if key in point.dimensions and point.dimensions[key] != value:
                        include = False
                        break
                if include:
                    filtered_data.append(point)
            metric_data.data = filtered_data
        
        return metric_data
        
    except Exception as e:
        logger.error(f"Error getting tool execution metrics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving tool execution metrics: {str(e)}"
        )

# Performance metrics endpoints

@router.get(
    "/metrics/performance",
    response_model=MetricResponse,
    summary="Get system-wide performance metrics"
)
async def get_performance_metrics(
    from_time: Optional[datetime] = Query(None, description="Start time (ISO format)"),
    to_time: Optional[datetime] = Query(None, description="End time (ISO format)"),
    time_range: Optional[str] = Query("30d", description="Predefined time range (1h, 1d, 7d, 30d)"),
    interval: Optional[str] = Query("1d", description="Aggregation interval (1m, 1h, 1d, 7d)"),
    group_by: Optional[str] = Query(None, description="Dimension to group by (agent, model)"),
    db: Session = Depends(get_db)
):
    """
    Get system-wide performance metrics.
    
    This endpoint provides data on response times, throughput, and concurrent sessions
    across all agents, with optional grouping by agent or model.
    
    Returns:
        MetricResponse: Performance metrics data
    """
    logger.info("Querying system-wide performance metrics")
    
    # Parse group_by if provided to create dimensions list
    dimension_list = None
    if group_by:
        # Map frontend-friendly names to actual dimension names
        dimension_map = {
            "model": "llm.model",
            "agent": "agent_id"
        }
        # Get the actual dimension name or use as-is if not in map
        actual_dimension = dimension_map.get(group_by, group_by)
        dimension_list = [actual_dimension]
    
    # Validate time_range if provided
    if time_range and time_range not in ["1h", "1d", "7d", "30d"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid time_range value: {time_range}. Valid values are: 1h, 1d, 7d, 30d"
        )
    
    # Use llm_response_time as the primary performance metric
    query = MetricQuery(
        metric="llm_response_time",
        from_time=from_time,
        to_time=to_time,
        time_range=time_range,
        interval=interval,
        dimensions=dimension_list
    )
    
    try:
        # Get metric data
        metric_data = get_metric(query, db)
        
        # Adjust the metric name for clarity in response
        metric_data.metric = "performance_metrics"
        
        return metric_data
        
    except Exception as e:
        logger.error(f"Error getting performance metrics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving performance metrics: {str(e)}"
        )

# Security and Alert metrics endpoints

@router.get(
    "/metrics/alerts",
    response_model=MetricResponse,
    summary="Get aggregated security alert metrics"
)
async def get_alert_metrics(
    from_time: Optional[datetime] = Query(None, description="Start time (ISO format)"),
    to_time: Optional[datetime] = Query(None, description="End time (ISO format)"),
    time_range: Optional[str] = Query("30d", description="Predefined time range (1h, 1d, 7d, 30d)"),
    interval: Optional[str] = Query("1d", description="Aggregation interval (1m, 1h, 1d, 7d)"),
    severity: Optional[str] = Query(None, description="Filter by alert severity (low, medium, high)"),
    alert_type: Optional[str] = Query(None, description="Filter by alert type"),
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    db: Session = Depends(get_db)
):
    """
    Get aggregated security alert metrics with filtering options.
    
    This endpoint provides data on security alerts across all agents,
    with trend information and filtering by severity, type, or agent.
    
    Returns:
        MetricResponse: Alert metrics data
    """
    logger.info("Querying security alert metrics")
    
    # For now, use error_count as proxy for alerts with dimensions
    # This will be replaced with actual alert metrics in the future
    dimension_list = ["error.type"]
    
    # Validate time_range if provided
    if time_range and time_range not in ["1h", "1d", "7d", "30d"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid time_range value: {time_range}. Valid values are: 1h, 1d, 7d, 30d"
        )
    
    # Create query object
    query = MetricQuery(
        metric="error_count",
        agent_id=agent_id,
        from_time=from_time,
        to_time=to_time,
        time_range=time_range,
        interval=interval,
        dimensions=dimension_list
    )
    
    try:
        # Get metric data
        metric_data = get_metric(query, db)
        
        # Adjust the metric name for clarity in response
        metric_data.metric = "security_alert_metrics"
        
        # Filter data points based on severity or alert_type if provided
        if severity or alert_type:
            filtered_data = []
            for point in metric_data.data:
                include = True
                
                # Basic mapping of error types to severity levels (to be improved)
                if severity and "error.type" in point.dimensions:
                    error_severity = {
                        "authentication": "high",
                        "authorization": "high",
                        "validation": "medium",
                        "resource": "medium",
                        "timeout": "low",
                        "network": "medium"
                    }.get(point.dimensions["error.type"].lower(), "low")
                    
                    if error_severity != severity.lower():
                        include = False
                
                # Filter by alert_type (currently mapped to error.type)
                if alert_type and "error.type" in point.dimensions:
                    if point.dimensions["error.type"].lower() != alert_type.lower():
                        include = False
                
                if include:
                    filtered_data.append(point)
            
            metric_data.data = filtered_data
        
        return metric_data
        
    except Exception as e:
        logger.error(f"Error getting alert metrics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving alert metrics: {str(e)}"
        )

@router.get(
    "/metrics/security",
    response_model=MetricResponse,
    summary="Get security posture metrics"
)
async def get_security_metrics(
    from_time: Optional[datetime] = Query(None, description="Start time (ISO format)"),
    to_time: Optional[datetime] = Query(None, description="End time (ISO format)"),
    time_range: Optional[str] = Query("30d", description="Predefined time range (1h, 1d, 7d, 30d)"),
    interval: Optional[str] = Query("1d", description="Aggregation interval (1m, 1h, 1d, 7d)"),
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    db: Session = Depends(get_db)
):
    """
    Get security posture metrics including suspicious activity rates.
    
    This endpoint provides data on security posture and anomaly detection
    across all agents, with optional filtering by agent.
    
    Returns:
        MetricResponse: Security posture metrics data
    """
    logger.info("Querying security posture metrics")
    
    # For now, use error_count as proxy for security metrics
    # This will be replaced with actual security metrics in the future
    
    # Validate time_range if provided
    if time_range and time_range not in ["1h", "1d", "7d", "30d"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid time_range value: {time_range}. Valid values are: 1h, 1d, 7d, 30d"
        )
    
    # Create query object
    query = MetricQuery(
        metric="error_count",
        agent_id=agent_id,
        from_time=from_time,
        to_time=to_time,
        time_range=time_range,
        interval=interval,
        dimensions=["error.type"]
    )
    
    try:
        # Get metric data
        metric_data = get_metric(query, db)
        
        # Adjust the metric name for clarity in response
        metric_data.metric = "security_posture_metrics"
        
        return metric_data
        
    except Exception as e:
        logger.error(f"Error getting security posture metrics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving security posture metrics: {str(e)}"
        )

# Session and Usage Analytics endpoints

@router.get(
    "/metrics/sessions",
    response_model=MetricResponse,
    summary="Get session analytics"
)
async def get_session_analytics(
    from_time: Optional[datetime] = Query(None, description="Start time (ISO format)"),
    to_time: Optional[datetime] = Query(None, description="End time (ISO format)"),
    time_range: Optional[str] = Query("30d", description="Predefined time range (1h, 1d, 7d, 30d)"),
    interval: Optional[str] = Query("1d", description="Aggregation interval (1m, 1h, 1d, 7d)"),
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    db: Session = Depends(get_db)
):
    """
    Get session analytics including counts, durations, and user activity.
    
    This endpoint provides data on session metrics across all agents,
    with optional filtering by agent and time period.
    
    Returns:
        MetricResponse: Session analytics data
    """
    logger.info("Querying session analytics")
    
    # Validate time_range if provided
    if time_range and time_range not in ["1h", "1d", "7d", "30d"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid time_range value: {time_range}. Valid values are: 1h, 1d, 7d, 30d"
        )
    
    # Create query object
    query = MetricQuery(
        metric="session_count",
        agent_id=agent_id,
        from_time=from_time,
        to_time=to_time,
        time_range=time_range,
        interval=interval,
        dimensions=["agent_id"] if agent_id is None else None
    )
    
    try:
        # Get metric data
        metric_data = get_metric(query, db)
        
        # Adjust the metric name for clarity in response
        metric_data.metric = "session_analytics"
        
        return metric_data
        
    except Exception as e:
        logger.error(f"Error getting session analytics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving session analytics: {str(e)}"
        )

@router.get(
    "/metrics/usage",
    response_model=MetricResponse,
    summary="Get overall usage patterns"
)
async def get_usage_patterns(
    from_time: Optional[datetime] = Query(None, description="Start time (ISO format)"),
    to_time: Optional[datetime] = Query(None, description="End time (ISO format)"),
    time_range: Optional[str] = Query("30d", description="Predefined time range (1h, 1d, 7d, 30d)"),
    interval: Optional[str] = Query("1d", description="Aggregation interval (1m, 1h, 1d, 7d)"),
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    pattern: Optional[str] = Query("hourly", description="Usage pattern type (hourly, daily, weekly)"),
    db: Session = Depends(get_db)
):
    """
    Get overall usage patterns including time-of-day and day-of-week patterns.
    
    This endpoint provides data on usage patterns across all agents,
    including peak usage metrics and growth trends.
    
    Returns:
        MetricResponse: Usage pattern data
    """
    logger.info(f"Querying usage patterns, pattern type: {pattern}")
    
    # Validate time_range if provided
    if time_range and time_range not in ["1h", "1d", "7d", "30d"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid time_range value: {time_range}. Valid values are: 1h, 1d, 7d, 30d"
        )
    
    # Validate pattern type
    if pattern not in ["hourly", "daily", "weekly"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid pattern value: {pattern}. Valid values are: hourly, daily, weekly"
        )
    
    # Determine interval based on pattern type
    if pattern == "hourly":
        # For hourly patterns, force 1h interval
        interval = "1h"
    elif pattern == "daily":
        # For daily patterns, force 1d interval
        interval = "1d"
    elif pattern == "weekly":
        # For weekly patterns, use 1d interval but will group later
        interval = "1d"
    
    # Create query object using llm_request_count as proxy for overall usage
    query = MetricQuery(
        metric="llm_request_count",
        agent_id=agent_id,
        from_time=from_time,
        to_time=to_time,
        time_range=time_range,
        interval=interval
    )
    
    try:
        # Get metric data
        metric_data = get_metric(query, db)
        
        # Process data based on pattern type
        if pattern == "hourly" or pattern == "daily":
            # Data already in correct format with appropriate interval
            pass
        elif pattern == "weekly":
            # Group daily data by day of week
            weekly_data = {}
            for point in metric_data.data:
                # Get day of week (0 = Monday, 6 = Sunday)
                day_of_week = point.timestamp.weekday()
                if day_of_week not in weekly_data:
                    weekly_data[day_of_week] = 0
                weekly_data[day_of_week] += point.value
            
            # Convert back to data points
            day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            new_data = []
            
            # Use a reference date for consistent sorting (use start of current week)
            today = datetime.now()
            start_of_week = today - timedelta(days=today.weekday())
            
            for day_num, value in weekly_data.items():
                day_date = start_of_week + timedelta(days=day_num)
                new_data.append(MetricDataPoint(
                    timestamp=day_date,
                    value=value,
                    dimensions={"day_of_week": day_names[day_num]}
                ))
            
            # Sort by day of week
            new_data.sort(key=lambda x: x.timestamp.weekday())
            metric_data.data = new_data
        
        # Adjust the metric name for clarity in response
        metric_data.metric = f"usage_pattern_{pattern}"
        
        return metric_data
        
    except Exception as e:
        logger.error(f"Error getting usage patterns: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving usage patterns: {str(e)}"
        ) 