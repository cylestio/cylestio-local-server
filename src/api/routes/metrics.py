from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Union
import csv
import json
import os

from fastapi import APIRouter, Depends, Query, HTTPException, status, Path
from sqlalchemy.orm import Session
from sqlalchemy import func, case

from src.database.session import get_db
from src.api.schemas.metrics import (
    MetricResponse, DashboardResponse, ToolInteractionListResponse,
    LLMMetricsFilter, LLMMetricsBreakdownResponse, LLMMetricsBreakdown,
    LLMMetricsBreakdownItem, TimeGranularity, TimeRange,
    ConversationSummary, 
    ConversationListResponse, 
    ConversationMessage, 
    ConversationDetailResponse,
    ConversationSearchParams,
    LLMRequestDetail,
    LLMRequestListResponse
)
from src.analysis.interface import (
    MetricQuery, TimeRangeParams, TimeSeriesParams, TimeResolution, MetricParams,
    get_metric, get_dashboard_metrics
)
from src.analysis.metrics.token_metrics import TokenMetrics
from src.analysis.metrics.tool_metrics import ToolMetrics
from src.analysis.metrics.llm_analytics import LLMAnalytics
from src.utils.logging import get_logger
from src.analysis.utils import parse_time_range
from src.analysis.utils import sql_time_bucket
# Import the pricing service
from src.services.pricing_service import pricing_service

logger = get_logger(__name__)
router = APIRouter()

# Dashboard endpoint
@router.get(
    "/dashboard",
    response_model=DashboardResponse,
    summary="Get main dashboard metrics"
)
async def get_dashboard(
    time_range: str = Query("30d", description="Time range (1h, 1d, 7d, 30d)"),
    db: Session = Depends(get_db)
):
    """
    Get main dashboard metrics including summary stats and recent activity.
    
    This endpoint aggregates key metrics for the main dashboard view including
    total LLM requests, token usage, active agents, and error rates.
    
    Returns:
        DashboardResponse: Dashboard metrics and summary stats
    """
    logger.info(f"Getting dashboard metrics for time_range: {time_range}")
    
    # Validate time_range
    if time_range not in ["1h", "1d", "7d", "30d"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid time_range value: {time_range}. Valid values are: 1h, 1d, 7d, 30d"
        )
    
    try:
        # Get dashboard metrics
        dashboard_data = get_dashboard_metrics(time_range, db)
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
    summary="Get LLM request count metrics",
    deprecated=True
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
    
    **Deprecated**: Use `/metrics/llm/analytics` instead with `breakdown_by` parameter.
    
    Returns:
        MetricResponse: LLM request count data points
    """
    logger.info("Querying LLM request count metrics (deprecated)")
    
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
    summary="Get LLM token usage time series",
    deprecated=True
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
    
    **Deprecated**: Use `/metrics/llm/analytics` with `breakdown_by=time` instead.
    
    Returns:
        Time series token usage data points with model and token type dimensions
    """
    logger.info("Querying LLM token usage time series (deprecated)")
    
    try:
        # Validate time_range
        if time_range not in ["1h", "1d", "7d", "30d"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid time_range value: {time_range}. Valid values are: 1h, 1d, 7d, 30d"
            )
        
        # Calculate time range
        to_time = datetime.utcnow() + timedelta(hours=2)
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
    summary="Get LLM response time metrics",
    deprecated=True
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
    
    **Deprecated**: Use `/metrics/llm/analytics` instead.
    
    Returns:
        MetricResponse: LLM response time data points
    """
    logger.info("Querying LLM response time metrics (deprecated)")
    
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
    Get all metrics for a specific agent in a single request.
    
    This endpoint aggregates multiple metrics for a specific agent, 
    including LLM requests, token usage, errors, and performance stats.
    
    Returns:
        Dict[str, Any]: Consolidated agent metrics
    """
    logger.info(f"Getting all metrics for agent: {agent_id}")
    
    # Validate time_range
    if time_range not in ["1h", "1d", "7d", "30d"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid time_range value: {time_range}. Valid values are: 1h, 1d, 7d, 30d"
        )
    
    # Helper function to extract a single value from a metric result
    def _extract_metric_value(metric_result):
        if not metric_result or not metric_result.data:
            return 0
            
        # If multiple data points, sum them (for breakdowns)
        total = 0
        for point in metric_result.data:
            if hasattr(point, 'value'):
                total += point.value
            elif isinstance(point, dict) and 'value' in point:
                total += point['value']
        
        return total
    
    # Initialize metrics object and error messages list
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

# Aggregated system-wide metrics endpoints

@router.get(
    "/metrics/llms",
    response_model=MetricResponse,
    summary="Get aggregated LLM usage metrics",
    deprecated=True
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
    Get aggregated LLM usage metrics with dimensions and filtering.
    
    **Deprecated**: Use `/metrics/llm/models` instead.
    
    Returns:
        MetricResponse: Aggregated LLM metrics
    """
    logger.info("Querying aggregated LLM metrics (deprecated)")
    
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
    summary="Get LLM request metrics across all agents",
    deprecated=True
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
    Get LLM request metrics across all agents with optional grouping.
    
    **Deprecated**: Use `/metrics/llm/analytics` instead.
    
    Returns:
        MetricResponse: LLM request metrics data
    """
    logger.info("Querying LLM requests metrics (deprecated)")
    
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
    total_input = 0
    total_output = 0
    
    for item in model_usage.items:
        # Ensure total_tokens is correctly calculated if it's zero
        model_total_tokens = item["total_tokens"]
        if model_total_tokens == 0 and (item["input_tokens"] > 0 or item["output_tokens"] > 0):
            model_total_tokens = item["input_tokens"] + item["output_tokens"]
            
        models.append({
            "name": item["model"],
            "input_tokens": item["input_tokens"],
            "output_tokens": item["output_tokens"],
            "total_tokens": model_total_tokens
        })
        
        # Accumulate totals from the model breakdown
        total_input += item["input_tokens"]
        total_output += item["output_tokens"]
    
    # Use the summary values if they're non-zero, otherwise use the calculated totals
    input_tokens = summary["total_input_tokens"] if summary["total_input_tokens"] > 0 else total_input
    output_tokens = summary["total_output_tokens"] if summary["total_output_tokens"] > 0 else total_output
    total_tokens = summary["total_tokens"] if summary["total_tokens"] > 0 else (input_tokens + output_tokens)
    
    # Create the response object
    response = {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
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
    summary="Get overall usage patterns",
    deprecated=True
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
    logger.info(f"Getting usage patterns with pattern: {pattern} (deprecated)")
    
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
        csv_path = os.path.join("resources", "full_llm_models_pricing_08April2025.csv")
        
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
        
        # Extract update date from filename
        update_date = "April 8, 2025"
        
        # Format data to match the UI view
        result = {
            "models": pricing_data,
            "total_count": len(pricing_data),
            "update_date": update_date
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

        # Calculate costs for each model using the pricing service
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
            vendor = model_data.get('vendor', '')

            # Get token counts
            input_tokens = model_data.get('input_tokens', 0) or 0
            output_tokens = model_data.get('output_tokens', 0) or 0
            model_total_tokens = input_tokens + output_tokens

            # Use pricing service to calculate costs
            cost_result = pricing_service.calculate_cost(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                model=model_name,
                vendor=vendor
            )
            
            # Extract costs from result
            input_price = cost_result['input_price_per_1k']
            output_price = cost_result['output_price_per_1k']
            input_cost = cost_result['input_cost']
            output_cost = cost_result['output_cost']
            model_total_cost = cost_result['total_cost']

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
                'input_cost': round(input_cost, 6),  # Total cost for input tokens
                'output_cost': round(output_cost, 6),  # Total cost for output tokens
                'total_cost': round(model_total_cost, 6)  # Total cost for this model
            })

        # Assemble the final response
        result = {
            "token_usage_cost": {
                "breakdown": cost_breakdown,
                "totals": {
                    "input_tokens": total_input_tokens,
                    "output_tokens": total_output_tokens,
                    "total_tokens": total_tokens,
                    "input_cost": round(total_input_cost, 6),
                    "output_cost": round(total_output_cost, 6),
                    "total_cost": round(total_input_cost + total_output_cost, 6)
                }
            },
            "pricing_note": "Input and output prices are per 1,000 tokens. Costs are calculated as (tokens/1000) * price.",
            "update_date": "April 8, 2025"
        }
        
        return result

    except Exception as e:
        logger.error(f"Error calculating token usage cost: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calculating token usage cost: {str(e)}"
        )

# New LLM analytics endpoints
@router.get(
    "/metrics/llm/analytics",
    response_model=LLMMetricsBreakdownResponse,
    summary="Get comprehensive LLM usage analytics"
)
async def get_llm_analytics(
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    model_name: Optional[str] = Query(None, description="Filter by model name"),
    from_time: Optional[datetime] = Query(None, description="Start time (ISO format)"),
    to_time: Optional[datetime] = Query(None, description="End time (ISO format)"),
    granularity: TimeGranularity = Query(TimeGranularity.DAY, description="Time granularity (minute, hour, day)"),
    breakdown_by: LLMMetricsBreakdown = Query(LLMMetricsBreakdown.NONE, description="Dimension to break down by (none, agent, model, time)"),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive LLM usage analytics with flexible filtering and breakdowns.
    
    This endpoint consolidates metrics across all LLM interactions, including:
    - Request counts and success/error rates
    - Response time metrics (avg, p95)
    - Token usage and cost estimations
    - First/last seen timestamps
    
    The response can be broken down by agent, model, or time to provide detailed analytics.
    
    Returns:
        LLMMetricsBreakdownResponse: Comprehensive LLM analytics data
    """
    logger.info(f"Getting LLM analytics with breakdown by {breakdown_by}")
    
    try:
        # Create filter object
        filters = LLMMetricsFilter(
            agent_id=agent_id,
            model_name=model_name,
            from_time=from_time,
            to_time=to_time,
            granularity=granularity
        )
        
        logger.info(f"Created filters: {filters}")
        
        # Get analytics data
        logger.info(f"Creating LLMAnalytics instance")
        llm_analytics = LLMAnalytics(db)
        
        logger.info(f"Calling get_metrics with breakdown_by={breakdown_by}")
        analytics_data = llm_analytics.get_metrics(filters, breakdown_by)
        
        logger.info(f"Successfully retrieved analytics data")
        return analytics_data
        
    except Exception as e:
        logger.error(f"Error getting LLM analytics: {str(e)}", exc_info=True)
        logger.error(f"Exception type: {type(e)}")
        logger.error(f"Exception args: {e.args}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving LLM analytics: {str(e)}"
        )

@router.get(
    "/metrics/llm/models",
    response_model=LLMMetricsBreakdownResponse,
    summary="Get LLM model performance comparison"
)
async def get_llm_model_comparison(
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    from_time: Optional[datetime] = Query(None, description="Start time (ISO format)"),
    to_time: Optional[datetime] = Query(None, description="End time (ISO format)"),
    db: Session = Depends(get_db)
):
    """
    Get a comparison of different LLM models' performance metrics.
    
    This endpoint provides a breakdown of LLM analytics by model,
    allowing users to compare different models' performance, cost,
    and usage patterns.
    
    Returns:
        LLMMetricsBreakdownResponse: Model comparison data
    """
    logger.info("Getting LLM model comparison")
    
    try:
        # Create filter object
        filters = LLMMetricsFilter(
            agent_id=agent_id,
            from_time=from_time,
            to_time=to_time
        )
        
        # Get analytics with model breakdown
        llm_analytics = LLMAnalytics(db)
        analytics_data = llm_analytics.get_metrics(filters, LLMMetricsBreakdown.MODEL)
        
        return analytics_data
        
    except Exception as e:
        logger.error(f"Error getting LLM model comparison: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving LLM model comparison: {str(e)}"
        )

@router.get(
    "/metrics/llm/usage_trends",
    response_model=LLMMetricsBreakdownResponse,
    summary="Get LLM usage trends over time"
)
async def get_llm_usage_trends(
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    model_name: Optional[str] = Query(None, description="Filter by model name"),
    from_time: Optional[datetime] = Query(None, description="Start time (ISO format)"),
    to_time: Optional[datetime] = Query(None, description="End time (ISO format)"),
    granularity: TimeGranularity = Query(TimeGranularity.DAY, description="Time granularity (minute, hour, day)"),
    db: Session = Depends(get_db)
):
    """
    Get LLM usage trends over time with flexible time granularity.
    
    This endpoint provides a breakdown of LLM analytics by time buckets,
    showing trends in usage, performance, and costs over the specified period.
    
    Returns:
        LLMMetricsBreakdownResponse: Time-based trend data
    """
    logger.info(f"Getting LLM usage trends with granularity {granularity}")
    
    try:
        # Create filter object
        filters = LLMMetricsFilter(
            agent_id=agent_id,
            model_name=model_name,
            from_time=from_time,
            to_time=to_time,
            granularity=granularity
        )
        
        # Get analytics with time breakdown
        llm_analytics = LLMAnalytics(db)
        analytics_data = llm_analytics.get_metrics(filters, LLMMetricsBreakdown.TIME)
        
        return analytics_data
        
    except Exception as e:
        logger.error(f"Error getting LLM usage trends: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving LLM usage trends: {str(e)}"
        )

@router.get(
    "/metrics/llm/agent_usage",
    response_model=LLMMetricsBreakdownResponse,
    summary="Get LLM usage by agent"
)
async def get_llm_agent_usage(
    model_name: Optional[str] = Query(None, description="Filter by model name"),
    from_time: Optional[datetime] = Query(None, description="Start time (ISO format)"),
    to_time: Optional[datetime] = Query(None, description="End time (ISO format)"),
    db: Session = Depends(get_db)
):
    """
    Get LLM usage broken down by agent.
    
    This endpoint provides a breakdown of LLM analytics by agent,
    showing which agents are using LLMs the most and their performance metrics.
    
    Returns:
        LLMMetricsBreakdownResponse: Agent usage data
    """
    logger.info("Getting LLM usage by agent")
    
    try:
        # Create filter object
        filters = LLMMetricsFilter(
            model_name=model_name,
            from_time=from_time,
            to_time=to_time
        )
        
        # Get analytics with agent breakdown
        llm_analytics = LLMAnalytics(db)
        analytics_data = llm_analytics.get_metrics(filters, LLMMetricsBreakdown.AGENT)
        
        return analytics_data
        
    except Exception as e:
        logger.error(f"Error getting LLM agent usage: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving LLM agent usage: {str(e)}"
        )

@router.get(
    "/metrics/llm/agent_model_relationships",
    response_model=LLMMetricsBreakdownResponse,
    summary="Get agent-model relationship analytics"
)
async def get_agent_model_relationships(
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    model_name: Optional[str] = Query(None, description="Filter by model name"),
    from_time: Optional[datetime] = Query(None, description="Start time (ISO format)"),
    to_time: Optional[datetime] = Query(None, description="End time (ISO format)"),
    granularity: TimeGranularity = Query(TimeGranularity.DAY, description="Time granularity (minute, hour, day)"),
    include_distributions: bool = Query(False, description="Whether to include time and token distributions"),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive analytics on agent-model relationships.
    
    This endpoint provides rich data about which agents used which models, when they were used,
    and usage statistics. Results can be visualized as histograms, trends, and other charts.
    
    The response includes:
    - For each agent, what models it used
    - When the models were used (with time granularity)
    - Usage metrics (request count, tokens, cost, etc.)
    - Optional time and token distributions for histograms
    
    Args:
        agent_id: Optional agent ID to filter by
        model_name: Optional model name to filter by
        from_time: Start time in ISO format
        to_time: End time in ISO format
        granularity: Time resolution (minute, hour, day)
        include_distributions: Whether to include time and token distributions for visualization
    
    Returns:
        Comprehensive breakdown of agent-model relationships
    """
    logger.info("Querying agent-model relationship analytics")
    
    try:
        # Parse time range
        start_time, end_time = parse_time_range(from_time, to_time)
        
        # Create filter object
        filters = LLMMetricsFilter(
            agent_id=agent_id,
            model_name=model_name,
            from_time=start_time,
            to_time=end_time,
            granularity=granularity
        )
        
        # Initialize analytics service
        llm_analytics = LLMAnalytics(db)
        
        # Get metrics with nested breakdown (first by agent, then by model)
        # This is a special case - we want to see for each agent, what models it used
        agent_metrics = llm_analytics.get_metrics(filters, breakdown_by=LLMMetricsBreakdown.AGENT)
        
        # For each agent, get a breakdown by model
        result_breakdown = []
        
        if agent_id:
            # If agent_id is specified, only get model breakdown for that agent
            model_filters = LLMMetricsFilter(
                agent_id=agent_id,
                from_time=start_time,
                to_time=end_time,
                granularity=granularity
            )
            model_metrics = llm_analytics.get_metrics(model_filters, breakdown_by=LLMMetricsBreakdown.MODEL)
            
            # Format the response with a single agent's model usage
            for model_item in model_metrics.breakdown:
                model_name = model_item.key
                
                # Determine if this is likely the primary or fallback model
                # (Simple heuristic: highest token count is primary)
                token_count = model_item.metrics.token_count_total
                relation_type = "primary" if token_count > 1000 else "secondary"
                
                # Create the item with basic metrics
                breakdown_item = LLMMetricsBreakdownItem(
                    key=f"{agent_id}:{model_name}",
                    metrics=model_item.metrics,
                    relation_type=relation_type
                )
                
                # Optionally add distribution data
                if include_distributions:
                    # Add time distribution for visualizing when this model was used
                    time_distribution = llm_analytics.get_agent_model_time_distribution(
                        agent_id, model_name, filters
                    )
                    breakdown_item.time_distribution = time_distribution
                    
                    # Add token distribution for visualizing token usage patterns
                    token_distribution = llm_analytics.get_agent_model_token_distribution(
                        agent_id, model_name, filters
                    )
                    breakdown_item.token_distribution = token_distribution
                
                result_breakdown.append(breakdown_item)
        else:
            # Otherwise, get model breakdowns for each agent
            for agent_item in agent_metrics.breakdown:
                current_agent_id = agent_item.key
                
                # Get models used by this agent
                agent_filter = LLMMetricsFilter(
                    agent_id=current_agent_id,
                    from_time=start_time,
                    to_time=end_time,
                    granularity=granularity
                )
                
                agent_model_metrics = llm_analytics.get_metrics(
                    agent_filter, 
                    breakdown_by=LLMMetricsBreakdown.MODEL
                )
                
                # Add each agent-model combination to the results
                for model_item in agent_model_metrics.breakdown:
                    model_name = model_item.key
                    
                    # Determine if this is likely the primary or fallback model
                    token_count = model_item.metrics.token_count_total
                    relation_type = "primary" if token_count > 1000 else "secondary"
                    
                    # Create the item with basic metrics
                    breakdown_item = LLMMetricsBreakdownItem(
                        key=f"{current_agent_id}:{model_name}",
                        metrics=model_item.metrics,
                        relation_type=relation_type
                    )
                    
                    # Optionally add distribution data
                    if include_distributions:
                        # Add time distribution for visualizing when this model was used
                        time_distribution = llm_analytics.get_agent_model_time_distribution(
                            current_agent_id, model_name, filters
                        )
                        breakdown_item.time_distribution = time_distribution
                        
                        # Add token distribution for visualizing token usage patterns
                        token_distribution = llm_analytics.get_agent_model_token_distribution(
                            current_agent_id, model_name, filters
                        )
                        breakdown_item.token_distribution = token_distribution
                    
                    result_breakdown.append(breakdown_item)
        
        # Create final response
        response = LLMMetricsBreakdownResponse(
            total=agent_metrics.total,
            breakdown=result_breakdown,
            from_time=start_time,
            to_time=end_time,
            filters=filters,
            breakdown_by=LLMMetricsBreakdown.AGENT
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error getting agent-model relationship metrics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving agent-model relationship metrics: {str(e)}"
        )

@router.get(
    "/metrics/tool/success_rate/detailed",
    response_model=Dict[str, Any],
    summary="Get detailed tool success rate metrics with per-tool breakdown"
)
async def get_tool_success_rate_detailed(
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    from_time: Optional[datetime] = Query(None, description="Start time (ISO format)"),
    to_time: Optional[datetime] = Query(None, description="End time (ISO format)"),
    time_range: Optional[str] = Query("1d", description="Predefined time range (1h, 1d, 7d, 30d)"),
    db: Session = Depends(get_db)
):
    """
    Get detailed tool success rate metrics with breakdown by tool and overall statistics.
    
    This endpoint provides:
    - Success rate for each individual tool
    - Total calls for each tool
    - Success/failure counts per tool
    - Overall success rate across all tools
    - Aggregated statistics
    
    Returns:
        Dict[str, Any]: Detailed tool success rate metrics
    """
    logger.info("Querying detailed tool success rate metrics")
    
    # Validate time_range if provided
    if time_range and time_range not in ["1h", "1d", "7d", "30d"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid time_range value: {time_range}. Valid values are: 1h, 1d, 7d, 30d"
        )
    
    try:
        from src.models.event import Event
        from src.models.tool_interaction import ToolInteraction
        from sqlalchemy import func, case
        
        # Calculate time range
        to_time_value = to_time or (datetime.utcnow() + timedelta(hours=2))
        
        if from_time is None and time_range:
            if time_range == "1h":
                from_time_value = to_time_value - timedelta(hours=1)
            elif time_range == "1d":
                from_time_value = to_time_value - timedelta(days=1)
            elif time_range == "7d":
                from_time_value = to_time_value - timedelta(days=7)
            elif time_range == "30d":
                from_time_value = to_time_value - timedelta(days=30)
        else:
            from_time_value = from_time
            
        if from_time_value is None or to_time_value is None:
            raise ValueError("Time range is required. Provide either from_time and to_time, or time_range.")
        
        # Base query for tool-specific metrics
        tool_query = db.query(
            ToolInteraction.tool_name,
            func.count().label('total_calls'),
            func.sum(case((ToolInteraction.status == 'success', 1), else_=0)).label('successful_calls'),
            func.sum(case((ToolInteraction.status == 'error', 1), else_=0)).label('failed_calls'),
            func.avg(
                case((ToolInteraction.duration_ms > 0, ToolInteraction.duration_ms), else_=None)
            ).label('avg_duration_ms'),
            func.min(
                case((ToolInteraction.duration_ms > 0, ToolInteraction.duration_ms), else_=None)
            ).label('min_duration_ms'),
            func.max(
                case((ToolInteraction.duration_ms > 0, ToolInteraction.duration_ms), else_=None)
            ).label('max_duration_ms')
        ).join(
            Event, ToolInteraction.event_id == Event.id
        ).filter(
            Event.timestamp >= from_time_value,
            Event.timestamp <= to_time_value
        )
        
        # Apply agent filter if provided
        if agent_id:
            tool_query = tool_query.filter(Event.agent_id == agent_id)
            
        # Group by tool name and order by total calls descending
        tool_query = tool_query.group_by(ToolInteraction.tool_name)
        tool_query = tool_query.order_by(func.count().desc())
        
        # Execute the query
        tool_results = tool_query.all()
        
        # Overall metrics query
        overall_query = db.query(
            func.count().label('total_calls'),
            func.sum(case((ToolInteraction.status == 'success', 1), else_=0)).label('successful_calls'),
            func.sum(case((ToolInteraction.status == 'error', 1), else_=0)).label('failed_calls'),
            func.avg(
                case((ToolInteraction.duration_ms > 0, ToolInteraction.duration_ms), else_=None)
            ).label('avg_duration_ms')
        ).join(
            Event, ToolInteraction.event_id == Event.id
        ).filter(
            Event.timestamp >= from_time_value,
            Event.timestamp <= to_time_value
        )
        
        # Apply agent filter if provided
        if agent_id:
            overall_query = overall_query.filter(Event.agent_id == agent_id)
            
        # Execute the overall query
        overall_result = overall_query.first()
        
        # Format the results
        tool_metrics = []
        for tool in tool_results:
            success_rate = 0
            if tool.total_calls > 0:
                success_rate = round((tool.successful_calls / tool.total_calls) * 100, 2)
                
            tool_metrics.append({
                'tool_name': tool.tool_name,
                'total_calls': tool.total_calls,
                'successful_calls': tool.successful_calls,
                'failed_calls': tool.failed_calls,
                'success_rate': success_rate,
                'avg_duration_ms': round(tool.avg_duration_ms) if tool.avg_duration_ms is not None and tool.avg_duration_ms > 0 else None,
                'min_duration_ms': tool.min_duration_ms if tool.min_duration_ms is not None and tool.min_duration_ms > 0 else None,
                'max_duration_ms': tool.max_duration_ms if tool.max_duration_ms is not None and tool.max_duration_ms > 0 else None
            })
        
        # Calculate overall success rate
        overall_success_rate = 0
        if overall_result and overall_result.total_calls > 0:
            overall_success_rate = round((overall_result.successful_calls / overall_result.total_calls) * 100, 2)
        
        # Prepare response
        response = {
            'time_range': {
                'from': from_time_value.isoformat(),
                'to': to_time_value.isoformat(),
                'duration': time_range
            },
            'agent_id': agent_id,
            'overall': {
                'total_calls': overall_result.total_calls if overall_result else 0,
                'successful_calls': overall_result.successful_calls if overall_result else 0,
                'failed_calls': overall_result.failed_calls if overall_result else 0,
                'success_rate': overall_success_rate,
                'avg_duration_ms': round(overall_result.avg_duration_ms) if overall_result and overall_result.avg_duration_ms is not None and overall_result.avg_duration_ms > 0 else None
            },
            'tools': tool_metrics,
            'unique_tools': len(tool_metrics)
        }
        
        return response
        
    except Exception as e:
        logger.error(f"Error getting detailed tool success rate metrics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving detailed tool success rate metrics: {str(e)}"
        )

@router.get(
    "/metrics/llm/requests",
    response_model=LLMRequestListResponse,
    summary="Get LLM requests with agent information"
)
async def get_llm_requests(
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    model: Optional[str] = Query(None, description="Filter by model"),
    from_time: Optional[datetime] = Query(None, description="Start time (ISO format)"),
    to_time: Optional[datetime] = Query(None, description="End time (ISO format)"),
    page: int = Query(1, description="Page number"),
    page_size: int = Query(20, description="Items per page"),
    db: Session = Depends(get_db)
):
    """
    Get a list of LLM requests with agent information included.
    
    This endpoint returns all LLM requests with detailed information including:
    - Basic request properties (ID, timestamp, duration, tokens)
    - Agent information (ID, name)
    - Model information
    - Request status
    
    Results can be filtered by agent_id, model, and time range.
    """
    logger.info(f"Getting LLM requests with agent info. Agent: {agent_id}, Model: {model}")
    
    # Local import to avoid circular dependency
    from src.services.conversation_service import get_conversation_service
    conversation_service = get_conversation_service(db)
    
    try:
        requests, pagination = conversation_service.get_llm_requests(
            agent_id=agent_id,
            model=model,
            from_time=from_time,
            to_time=to_time,
            page=page,
            page_size=page_size
        )
        
        return LLMRequestListResponse(
            items=requests,
            pagination=pagination
        )
        
    except Exception as e:
        logger.error(f"Error getting LLM requests: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving LLM requests: {str(e)}"
        )

@router.get(
    "/metrics/llm/requests/{request_id}",
    response_model=LLMRequestDetail,
    summary="Get detailed information about a specific LLM request"
)
async def get_llm_request_details(
    request_id: str = Path(..., description="Request ID in format '{event_id}_{interaction_id}'"),
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific LLM request.
    
    This endpoint returns all available information about a specific LLM request, including:
    - Request properties (ID, timestamp, duration, tokens)
    - Agent information (ID, name)
    - Model information
    - Full request and response content
    - Status and error information if applicable
    """
    logger.info(f"Getting LLM request details for request_id: {request_id}")
    
    # Local import to avoid circular dependency
    from src.services.conversation_service import get_conversation_service
    conversation_service = get_conversation_service(db)
    
    try:
        request_details = conversation_service.get_request_details(request_id)
        
        if not request_details:
            raise HTTPException(
                status_code=404,
                detail=f"LLM request with ID {request_id} not found"
            )
            
        return request_details
        
    except ValueError as e:
        logger.error(f"Invalid request ID format: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid request ID format: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error getting LLM request details: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving LLM request details: {str(e)}"
        )

@router.get(
    "/metrics/llm/conversations",
    response_model=ConversationListResponse,
    summary="Get list of LLM conversations"
)
async def get_llm_conversations(
    query: Optional[str] = Query(None, description="Full-text search across conversation content"),
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    status: Optional[str] = Query(None, description="Filter by status (success, error, mixed)"),
    from_time: Optional[datetime] = Query(None, description="Start time (ISO format)"),
    to_time: Optional[datetime] = Query(None, description="End time (ISO format)"),
    token_min: Optional[int] = Query(None, description="Minimum token count"),
    token_max: Optional[int] = Query(None, description="Maximum token count"),
    has_error: Optional[bool] = Query(None, description="Filter for conversations with errors"),
    page: int = Query(1, description="Page number"),
    page_size: int = Query(20, description="Items per page"),
    db: Session = Depends(get_db)
):
    """
    Get a list of LLM conversations with metadata and summary.
    
    This endpoint returns conversations (grouped requests with the same trace_id) with
    metadata including timestamps, agent information, request counts, and a summary
    derived from the first user message.
    
    Results can be filtered using a variety of criteria and support full-text search
    across conversation content.
    """
    logger.info("Getting LLM conversations list")
    
    # Create search parameters object
    search_params = ConversationSearchParams(
        query=query,
        agent_id=agent_id,
        status=status,
        from_time=from_time,
        to_time=to_time,
        token_min=token_min,
        token_max=token_max,
        has_error=has_error,
        page=page,
        page_size=page_size
    )
    
    # Local import to avoid circular dependency
    from src.services.conversation_service import get_conversation_service
    conversation_service = get_conversation_service(db)
    
    try:
        conversations, pagination = conversation_service.get_conversations(search_params)
        
        return ConversationListResponse(
            items=conversations,
            pagination=pagination
        )
        
    except Exception as e:
        logger.error(f"Error getting LLM conversations: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving LLM conversations: {str(e)}"
        )

@router.get(
    "/metrics/llm/conversations/{trace_id}",
    response_model=ConversationDetailResponse,
    summary="Get detailed conversation messages"
)
async def get_llm_conversation_detail(
    trace_id: str = Path(..., description="Trace ID of the conversation"),
    page: int = Query(1, description="Page number"),
    page_size: int = Query(50, description="Items per page"),
    db: Session = Depends(get_db)
):
    """
    Get detailed messages for a specific conversation.
    
    This endpoint returns all messages in a conversation, identified by trace_id,
    in chronological order. It includes:
    - Full message content for user and assistant messages
    - Message metadata (timestamps, tokens, etc.)
    - Agent information
    - Status and other properties
    
    For very long conversations, the results are paginated.
    """
    logger.info(f"Getting conversation detail for trace_id: {trace_id}")
    
    # Local import to avoid circular dependency
    from src.services.conversation_service import get_conversation_service
    conversation_service = get_conversation_service(db)
    
    try:
        messages, pagination = conversation_service.get_conversation_messages(
            trace_id=trace_id,
            page=page,
            page_size=page_size
        )
        
        if not messages and page == 1:
            # No messages found and we're on the first page
            raise HTTPException(
                status_code=404,
                detail=f"Conversation with trace_id {trace_id} not found"
            )
            
        return ConversationDetailResponse(
            items=messages,
            pagination=pagination
        )
        
    except Exception as e:
        logger.error(f"Error getting conversation detail: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving conversation detail: {str(e)}"
        )