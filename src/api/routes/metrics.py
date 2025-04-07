from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Union
import csv
import json
import os

from fastapi import APIRouter, Depends, Query, HTTPException, status, Path
from sqlalchemy.orm import Session

from src.database.session import get_db
from src.api.schemas.metrics import (
    MetricResponse, DashboardResponse, ToolInteractionListResponse
)
from src.analysis.interface import (
    MetricQuery, TimeRangeParams, TimeSeriesParams, TimeResolution, MetricParams,
    get_metric, get_dashboard_metrics
)
from src.analysis.metrics.token_metrics import TokenMetrics
from src.analysis.metrics.tool_metrics import ToolMetrics
from src.utils.logging import get_logger
from src.analysis.utils import parse_time_range

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
    summary="Get LLM token usage time series"
)
async def get_llm_token_usage(
    time_range: Optional[str] = Query("30d", description="Predefined time range (1h, 1d, 7d, 30d)"),
    interval: Optional[str] = Query("1d", description="Aggregation interval (1m, 1h, 1d, 7d)"),
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    model: Optional[str] = Query(None, description="Filter by model name"),
    db: Session = Depends(get_db)
):
    """
    Get LLM token usage time series data with filtering options.
    
    Returns:
        Time series token usage data points with model and token type dimensions
    """
    logger.info("Querying LLM token usage time series")
    
    try:
        # Validate time_range
        if time_range not in ["1h", "1d", "7d", "30d"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid time_range value: {time_range}. Valid values are: 1h, 1d, 7d, 30d"
            )
        
        # Calculate time range
        to_time = datetime.utcnow()
        if time_range == "1h":
            from_time = to_time - timedelta(hours=1)
        elif time_range == "1d":
            from_time = to_time - timedelta(days=1)
        elif time_range == "7d":
            from_time = to_time - timedelta(days=7)
        elif time_range == "30d":
            from_time = to_time - timedelta(days=30)
        
        # Create token metrics analyzer
        token_metrics = TokenMetrics(db)
        
        # Configure time range and resolution
        time_range_obj = TimeRangeParams(start=from_time, end=to_time)
        
        # Map interval to resolution
        resolution_map = {
            "1m": TimeResolution.MINUTE,
            "1h": TimeResolution.HOUR,
            "1d": TimeResolution.DAY,
            "7d": TimeResolution.WEEK
        }
        resolution = resolution_map.get(interval, TimeResolution.DAY)
        
        # Create params for time series
        params = TimeSeriesParams(
            time_range=time_range_obj,
            resolution=resolution
        )
        
        # Add agent filter if specified
        if agent_id:
            params.agent_ids = [agent_id]
        
        # Get time series data
        time_series_data = token_metrics.get_token_usage_time_series(params)
        
        # If model is specified, filter the data after retrieval
        filtered_data = time_series_data
        if model:
            filtered_data = [point for point in time_series_data if point.get('model') == model]
            # If no data matches the model, use all data
            if not filtered_data:
                filtered_data = time_series_data
                logger.warning(f"No data found for model {model}, using all data")
        
        # Format the data according to the requested structure
        formatted_data = []
        
        for point in filtered_data:
            # Make sure time_bucket is available in the point
            if 'time_bucket' not in point:
                logger.warning(f"Missing time_bucket in data point: {point}")
                continue
                
            timestamp = point['time_bucket']
            if timestamp is None:
                logger.warning("Skipping data point with null timestamp")
                continue
                
            # Handle timestamp formatting
            if isinstance(timestamp, datetime):
                timestamp_str = timestamp.isoformat()
            elif isinstance(timestamp, str):
                # It's already a string from sql_time_bucket
                timestamp_str = timestamp
            else:
                timestamp_str = str(timestamp)
            
            # Add input token data point
            input_point = {
                "timestamp": timestamp_str,
                "value": point.get("input_tokens", 0),
                "dimensions": {
                    "type": "input",
                    "model": point.get("model", "all") if model is None else model
                }
            }
            formatted_data.append(input_point)
            
            # Add output token data point
            output_point = {
                "timestamp": timestamp_str,
                "value": point.get("output_tokens", 0),
                "dimensions": {
                    "type": "output",
                    "model": point.get("model", "all") if model is None else model
                }
            }
            formatted_data.append(output_point)
        
        # Create the response
        response = {
            "metric": "llm_token_usage",
            "from_time": from_time.isoformat(),
            "to_time": to_time.isoformat(),
            "interval": interval,
            "data": formatted_data
        }
        
        return response
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
        Token usage data across the system with model breakdown
    """
    logger.info("Querying system-wide token usage metrics")
    
    # Create token metrics analyzer
    token_metrics = TokenMetrics(db)
    
    # Get token usage summary for overall counts
    summary = token_metrics.get_token_usage_summary()
    
    # Get token usage by model for the breakdown
    model_params = MetricParams()
    model_usage = token_metrics.get_token_usage_by_model(model_params)
    
    # Format the response in the requested structure
    models = []
    for item in model_usage.items:
        models.append({
            "name": item["model"],
            "input_tokens": item["input_tokens"],
            "output_tokens": item["output_tokens"],
            "total_tokens": item["total_tokens"]
        })
    
    # Create the response object
    response = {
        "input_tokens": summary["total_input_tokens"],
        "output_tokens": summary["total_output_tokens"],
        "total_tokens": summary["total_tokens"],
        "models": models
    }
    
    return response

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

# Tool interaction comprehensive endpoint
@router.get(
    "/metrics/tool_interactions",
    response_model=ToolInteractionListResponse,
    summary="Get comprehensive tool interaction data"
)
async def get_tool_interactions(
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    from_time: Optional[datetime] = Query(None, description="Start time (ISO format)"),
    to_time: Optional[datetime] = Query(None, description="End time (ISO format)"),
    time_range: Optional[str] = Query("30d", description="Predefined time range (1h, 1d, 7d, 30d)"),
    tool_name: Optional[str] = Query(None, description="Filter by specific tool name"),
    tool_status: Optional[str] = Query(None, description="Filter by execution status (success, error, pending)"),
    framework_name: Optional[str] = Query(None, description="Filter by framework name"),
    interaction_type: Optional[str] = Query(None, description="Filter by interaction type (execution, result)"),
    sort_by: Optional[str] = Query("request_timestamp", description="Field to sort by"),
    sort_dir: Optional[str] = Query("desc", description="Sort direction (asc, desc)"),
    page: int = Query(1, description="Page number", ge=1),
    page_size: int = Query(20, description="Page size", ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Get detailed information about tool interactions with rich filtering options.
    
    This endpoint provides comprehensive data about tool interactions, including:
    - Execution details (parameters, status, duration)
    - Result data (responses, errors)
    - Metadata (timestamps, framework, version)
    - Raw attributes and associated event information
    
    Results can be filtered by various criteria and are paginated.
    
    Returns:
        ToolInteractionListResponse: Paginated tool interaction details
    """
    logger.info("Querying comprehensive tool interaction data")
    
    # Validate time_range if provided
    if time_range and time_range not in ["1h", "1d", "7d", "30d"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid time_range value: {time_range}. Valid values are: 1h, 1d, 7d, 30d"
        )
    
    try:
        # Convert time parameters to objects that the metrics interface expects
        time_params = parse_time_range(from_time, to_time, time_range)
        
        # Create the tool metrics interface
        tool_metrics = ToolMetrics(db)
        
        # Get detailed tool interactions
        interactions_data = tool_metrics.get_tool_interactions_detailed(
            from_time=time_params[0],
            to_time=time_params[1],
            agent_id=agent_id,
            tool_name=tool_name,
            status=tool_status,
            framework_name=framework_name,
            interaction_type=interaction_type,
            sort_by=sort_by,
            sort_dir=sort_dir,
            page=page,
            page_size=page_size
        )
        
        return ToolInteractionListResponse(**interactions_data)
        
    except Exception as e:
        logger.error(f"Error getting tool interaction data: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving tool interaction data: {str(e)}"
        )

@router.get(
    "/metrics/pricing/llm_models",
    summary="Get LLM models pricing data"
)
async def get_llm_models_pricing(
    provider: Optional[str] = Query(None, description="Filter by provider name"),
    model: Optional[str] = Query(None, description="Filter by model name"),
    db: Session = Depends(get_db)
):
    """
    Get LLM models pricing data from the pricing database.
    
    This endpoint returns pricing information for various LLM models to support the token usage insights view.
    
    Args:
        provider: Optional filter by provider name (e.g., 'OpenAI', 'Anthropic')
        model: Optional filter by model name (e.g., 'GPT-4', 'Claude 3 Haiku')
        
    Returns:
        Dictionary containing pricing information for LLM models
    """
    logger.info(f"Getting LLM models pricing data. Provider filter: {provider}, Model filter: {model}")
    
    try:
        # Define path to CSV file
        csv_path = os.path.join("resources", "full_llm_models_pricing_apr2025.csv")
        
        # Check if file exists
        if not os.path.exists(csv_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pricing data file not found"
            )
        
        # Read CSV data
        pricing_data = []
        with open(csv_path, mode='r', encoding='utf-8') as csv_file:
            csv_reader = csv.DictReader(csv_file)
            for row in csv_reader:
                # Apply filters if provided
                if provider and row.get('Provider', '').lower() != provider.lower():
                    continue
                if model and row.get('Model', '').lower() != model.lower():
                    continue
                
                # Convert price strings to floats where possible
                processed_row = {}
                for key, value in row.items():
                    if key in ('Input Price', 'Output Price'):
                        try:
                            # Remove $ and convert to float
                            if value.startswith('$'):
                                value = value[1:]
                            processed_row[key] = float(value)
                        except (ValueError, TypeError):
                            processed_row[key] = value
                    else:
                        processed_row[key] = value
                
                pricing_data.append(processed_row)
        
        # Format data to match the UI view
        result = {
            "models": pricing_data,
            "total_count": len(pricing_data)
        }
        
        return result
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error retrieving LLM models pricing data: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving LLM models pricing data: {str(e)}"
        )

@router.get(
    "/metrics/pricing/token_usage_cost",
    summary="Calculate token usage cost based on models"
)
async def calculate_token_usage_cost(
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    from_time: Optional[datetime] = Query(None, description="Start time (ISO format)"),
    to_time: Optional[datetime] = Query(None, description="End time (ISO format)"),
    time_range: Optional[str] = Query("30d", description="Predefined time range (1h, 1d, 7d, 30d)"),
    db: Session = Depends(get_db)
):
    """
    Calculate token usage cost based on model pricing data.
    
    This endpoint returns token usage cost breakdown by model for the specified time period,
    matching the Token Usage Insights view in the UI.
    
    Args:
        agent_id: Optional filter by agent ID
        from_time: Optional start time
        to_time: Optional end time
        time_range: Predefined time range
        
    Returns:
        Dictionary containing token usage cost breakdown
    """
    logger.info(f"Calculating token usage cost. Time range: {time_range}")
    
    try:
        # Calculate time range
        start_time, end_time = parse_time_range(from_time, to_time, time_range)
        
        # Create token metrics analyzer
        token_metrics = TokenMetrics(db)
        
        # Prepare parameters for the metric query
        time_range_params = TimeRangeParams(start=start_time, end=end_time)
        metric_params_args = {"time_range": time_range_params}
        if agent_id:
            metric_params_args["agent_ids"] = [agent_id]
            
        metrics_params = MetricParams(**metric_params_args)
        
        # Get token usage data by model
        token_usage_result = token_metrics.get_token_usage_by_model(params=metrics_params)
        token_usage_by_model = token_usage_result.items # Access items from QueryResult

        # Load model pricing data
        csv_path = os.path.join("resources", "full_llm_models_pricing_apr2025.csv")
        model_pricing = {}
        with open(csv_path, mode='r', encoding='utf-8') as csv_file:
            csv_reader = csv.DictReader(csv_file)
            for row in csv_reader:
                # Construct a more robust key combining provider and model
                provider_key = row.get('Provider', '').strip().lower()
                model_key = row.get('Model', '').strip().lower()
                
                # Handle potential variations in model naming (e.g., version info)
                # This basic key might need refinement based on actual data patterns
                combined_key = f"{provider_key}-{model_key}" 
                
                input_price_str = row.get('Input Price', '0').replace('$', '').strip()
                output_price_str = row.get('Output Price', '0').replace('$', '').strip()

                # Handle price ranges (e.g., "0.00125–0.0025")
                input_price = 0.0
                try:
                    if '–' in input_price_str or '-' in input_price_str:
                        # Take average of range
                        range_parts = input_price_str.replace('–', '-').split('-')
                        range_values = []
                        for part in range_parts:
                            if part and part != 'N/A':
                                try:
                                    range_values.append(float(part.strip()))
                                except ValueError:
                                    pass
                        if range_values:
                            input_price = sum(range_values) / len(range_values)
                            logger.debug(f"Parsed price range {input_price_str} as average: {input_price}")
                    elif input_price_str and input_price_str != 'N/A':
                        input_price = float(input_price_str)
                except ValueError:
                    logger.warning(f"Could not parse input price '{input_price_str}' for {combined_key}, using 0.0")
                
                # Handle price ranges for output price too
                output_price = 0.0
                try:
                    if '–' in output_price_str or '-' in output_price_str:
                        # Take average of range
                        range_parts = output_price_str.replace('–', '-').split('-')
                        range_values = []
                        for part in range_parts:
                            if part and part != 'N/A':
                                try:
                                    range_values.append(float(part.strip()))
                                except ValueError:
                                    pass
                        if range_values:
                            output_price = sum(range_values) / len(range_values)
                            logger.debug(f"Parsed price range {output_price_str} as average: {output_price}")
                    elif output_price_str and output_price_str != 'N/A':
                        output_price = float(output_price_str)
                except ValueError:
                    logger.warning(f"Could not parse output price '{output_price_str}' for {combined_key}, using 0.0")

                model_pricing[combined_key] = {
                    'provider': row.get('Provider', '').strip(),
                    'model': row.get('Model', '').strip(),
                    'input_price': input_price,
                    'output_price': output_price
                }
        
        # Calculate costs for each model
        cost_breakdown = []
        total_input_tokens = 0
        total_output_tokens = 0
        total_tokens = 0
        total_input_cost = 0.0
        total_output_cost = 0.0
        total_cost = 0.0

        for model_data in token_usage_by_model:
            # Check if model_data is a dict (it should be after conversion in get_token_usage_by_model)
            if not isinstance(model_data, dict):
                 logger.warning(f"Skipping unexpected model data format: {type(model_data)}")
                 continue

            model_name = model_data.get('model', '')
            vendor = model_data.get('vendor', '').lower()

            # Try to find pricing data for this model
            pricing_key = None
            
            # Clean model name for better matching
            clean_model_name = model_name.lower()
            # Remove date/version suffixes like -20240307
            clean_model_name = '-'.join([part for part in clean_model_name.split('-') if not (part.isdigit() and len(part) >= 8)])
            # Replace dashes with spaces for better matching with CSV format
            clean_model_name_alt = clean_model_name.replace('-', ' ')
            # Additional normalization for number formats (3-5 vs 3.5)
            clean_model_name_dots = clean_model_name.replace('-', '.')
            
            # Special case handling for common models
            if "gpt-3.5-turbo" in clean_model_name:
                base_model_name = "gpt-3.5-turbo"
            elif "gpt-4" in clean_model_name and "turbo" in clean_model_name:
                base_model_name = "gpt-4-turbo"
            elif "gpt-4" in clean_model_name:
                base_model_name = "gpt-4"
            elif "claude-3-haiku" in clean_model_name:
                base_model_name = "claude-3-haiku"
            elif "claude-3-sonnet" in clean_model_name or "claude-3-5-sonnet" in clean_model_name:
                base_model_name = "claude-3.5-sonnet"
            elif "claude-3-opus" in clean_model_name:
                base_model_name = "claude-3-opus"
            else:
                base_model_name = clean_model_name
                
            logger.debug(f"Looking for pricing match. Original: '{model_name}', Base: '{base_model_name}', Cleaned: '{clean_model_name}', Alt: '{clean_model_name_alt}', Dots: '{clean_model_name_dots}'")
            
            # Debug all available pricing keys to help with diagnostics
            all_keys = list(model_pricing.keys())
            logger.debug(f"Available pricing keys: {all_keys}")
            
            for key in model_pricing:
                csv_model_name = model_pricing[key]['model'].lower()
                csv_provider = model_pricing[key]['provider'].lower()
                
                # Try multiple matching strategies
                provider_match = vendor in csv_provider or csv_provider in vendor
                
                # Debug info for specific models we're having trouble with
                if "gpt-3.5" in model_name.lower() or "claude-3.5" in model_name.lower() or "claude-3-5" in model_name.lower():
                    logger.debug(f"Trying to match {model_name} with {csv_model_name} (Key: {key})")
                    logger.debug(f"Provider match: {provider_match}, CSV provider: {csv_provider}, Vendor: {vendor}")
                
                # 0. Base model match (for specially handled common models)
                model_match = False
                if base_model_name.lower() in csv_model_name or csv_model_name in base_model_name.lower():
                    model_match = True
                    logger.debug(f"Base model name match: {base_model_name} matches {csv_model_name}")
                
                # 1. Direct substring match
                if not model_match:
                    model_match = clean_model_name in csv_model_name or csv_model_name in clean_model_name
                    if model_match and ("gpt-3.5" in model_name.lower() or "claude-3.5" in model_name.lower()):
                        logger.debug(f"Direct substring match: {clean_model_name} matches {csv_model_name}")
                
                # 2. Space-normalized match (for "claude 3 haiku" vs "claude-3-haiku")
                if not model_match:
                    model_match = clean_model_name_alt in csv_model_name or csv_model_name in clean_model_name_alt
                    if model_match and ("gpt-3.5" in model_name.lower() or "claude-3.5" in model_name.lower()):
                        logger.debug(f"Space-normalized match: {clean_model_name_alt} matches {csv_model_name}")
                
                # 3. Number format normalized match (for "claude-3-5" vs "claude 3.5")
                if not model_match:
                    # Handle version numbers with dots vs dashes (3.5 vs 3-5)
                    model_match = clean_model_name_dots in csv_model_name or csv_model_name.replace('.', '-') in clean_model_name
                    if model_match and ("gpt-3.5" in model_name.lower() or "claude-3.5" in model_name.lower()):
                        logger.debug(f"Number format match: {clean_model_name_dots} matches {csv_model_name}")
                
                # 4. Core name match - focus on key identifiers
                if not model_match:
                    # Extract key parts like "gpt-4" from "gpt-4-turbo-preview"
                    db_core = ''.join([c for c in clean_model_name if c.isalnum() or c in ['-', '.']])
                    csv_core = ''.join([c for c in csv_model_name if c.isalnum() or c in [' ', '.']])
                    
                    # Special cases for common model families
                    if ("gpt-3.5" in db_core and "gpt-3.5" in csv_core) or \
                       ("gpt-4" in db_core and "gpt-4" in csv_core) or \
                       ("claude-3" in db_core and "claude 3" in csv_core):
                        model_match = True
                        if "gpt-3.5" in model_name.lower() or "claude-3.5" in model_name.lower():
                            logger.debug(f"Special case match: {db_core} matches {csv_core}")
                    elif db_core in csv_core or csv_core in db_core:
                        model_match = True
                        if "gpt-3.5" in model_name.lower() or "claude-3.5" in model_name.lower():
                            logger.debug(f"Core match: {db_core} matches {csv_core}")
                
                # 5. Manual override for certain models
                if not model_match:
                    # GPT-3.5 Turbo special case
                    if "gpt-3.5-turbo" in model_name.lower() and "gpt-3.5 turbo" in csv_model_name:
                        model_match = True
                        logger.debug(f"Manual override match for GPT-3.5 Turbo")
                    # Claude 3.5 Sonnet special case
                    elif ("claude-3-5-sonnet" in model_name.lower() or "claude-3.5-sonnet" in model_name.lower()) and "claude 3.5 sonnet" in csv_model_name:
                        model_match = True
                        logger.debug(f"Manual override match for Claude 3.5 Sonnet")
                
                if (provider_match or not vendor) and model_match:
                    logger.debug(f"FINAL MATCH! DB model '{model_name}' matches CSV model '{model_pricing[key]['model']}' with prices: Input=${model_pricing[key]['input_price']}, Output=${model_pricing[key]['output_price']}")
                    pricing_key = key
                    break
            
            # Additional debug for GPT-3.5 Turbo
            if "gpt-3.5" in model_name.lower() and not pricing_key:
                logger.warning(f"Failed to match GPT-3.5 Turbo model: {model_name}")

            # Default pricing if not found
            input_price = 0.0
            output_price = 0.0

            if pricing_key:
                input_price = model_pricing[pricing_key]['input_price']
                output_price = model_pricing[pricing_key]['output_price']
            else:
                logger.warning(f"Pricing not found for model: {model_name} (Vendor: {vendor}). Using default $0.0.")

            # Get token counts
            input_tokens = model_data.get('input_tokens', 0) or 0
            output_tokens = model_data.get('output_tokens', 0) or 0
            model_total_tokens = input_tokens + output_tokens

            # Log values before calculation for debugging
            logger.debug(f"Calculating cost for {model_name}: Tokens(Input={input_tokens}, Output={output_tokens}), Prices(Input={input_price}, Output={output_price})")

            # Calculate costs
            input_cost = (input_tokens / 1000) * input_price
            output_cost = (output_tokens / 1000) * output_price
            model_total_cost = input_cost + output_cost

            logger.debug(f"Calculated costs for {model_name}: InputCost={input_cost:.6f}, OutputCost={output_cost:.6f}, TotalCost={model_total_cost:.6f}")

            # Add to totals
            total_input_tokens += input_tokens
            total_output_tokens += output_tokens
            total_tokens += model_total_tokens
            total_input_cost += input_cost
            total_output_cost += output_cost
            total_cost += model_total_cost

            # Add to breakdown
            cost_breakdown.append({
                'model': model_name,
                'vendor': model_data.get('vendor', ''), # Use original vendor casing for display
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'total_tokens': model_total_tokens,
                'input_price_per_1k': round(input_price, 6),  # Price per 1K tokens
                'output_price_per_1k': round(output_price, 6),  # Price per 1K tokens
                'input_cost': round(input_cost, 4),  # Total cost for input tokens
                'output_cost': round(output_cost, 4),  # Total cost for output tokens
                'total_cost': round(model_total_cost, 4)  # Total cost for this model
            })

        # Prepare response matching the UI
        result = {
            "total_tokens": {
                "value": total_tokens,
                "description": "Across all models"
            },
            "estimated_cost": {
                "value": round(total_cost, 2),
                "description": "Based on standard pricing"
            },
            "models_used": {
                "value": len(cost_breakdown),
                "description": "Active in this period"
            },
            "cost_breakdown": cost_breakdown,
            "totals": {
                "model": "Total", # Match UI
                "input_tokens": total_input_tokens,
                "input_cost": round(total_input_cost, 4),
                "output_tokens": total_output_tokens,
                "output_cost": round(total_output_cost, 4),
                "total_tokens": total_tokens, # Redundant but matches UI totals row
                "total_cost": round(total_cost, 4)
            },
            "pricing_note": "Input and output prices are per 1,000 tokens. Costs are calculated as (tokens/1000) * price.",
            "time_period": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
                "description": f"Data for period: {time_range}"
            }
        }

        return result

    except Exception as e:
        logger.error(f"Error calculating token usage cost: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calculating token usage cost: {str(e)}"
        ) 