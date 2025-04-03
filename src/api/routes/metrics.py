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
from src.analysis.interface import get_metric

logger = get_logger(__name__)
router = APIRouter()

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