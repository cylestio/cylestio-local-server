"""
Security API endpoints.

This module provides API endpoints for querying security alerts,
retrieving metrics, and analyzing security data.
"""
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any

from fastapi import APIRouter, Depends, Query, HTTPException, status, Path
from sqlalchemy.orm import Session

from src.database.session import get_db
from src.models.security_alert import SecurityAlert
from src.services.security_query import SecurityQueryService
from src.analysis.security_analysis import format_alert_for_response, get_security_overview
from src.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get(
    "/alerts",
    response_model=Dict[str, Any],
    summary="Get security alerts with flexible filtering"
)
async def get_security_alerts(
    from_time: Optional[datetime] = Query(None, description="Start time (ISO format)"),
    to_time: Optional[datetime] = Query(None, description="End time (ISO format)"),
    time_range: Optional[str] = Query("7d", description="Predefined time range (1h, 1d, 7d, 30d)"),
    severity: Optional[List[str]] = Query(None, description="Filter by alert severity (low, medium, high, critical)"),
    category: Optional[List[str]] = Query(None, description="Filter by category (sensitive_data, prompt_injection, etc.)"),
    alert_level: Optional[List[str]] = Query(None, description="Filter by alert level (none, suspicious, dangerous, critical)"),
    llm_vendor: Optional[List[str]] = Query(None, description="Filter by LLM vendor (openai, anthropic, etc.)"),
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    trace_id: Optional[str] = Query(None, description="Filter by trace ID for correlation"),
    span_id: Optional[str] = Query(None, description="Filter by span ID for correlation"),
    pattern: Optional[str] = Query(None, description="Search for specific pattern in detected keywords"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=1000, description="Items per page"),
    db: Session = Depends(get_db)
):
    """
    Get security alerts with detailed filtering options.
    
    This endpoint provides flexible querying of security alerts with pagination,
    filtering by various criteria, and support for correlation via trace_id and span_id.
    
    Returns:
        Dict[str, Any]: Security alerts data and metrics
    """
    logger.info("Querying security alerts with filters")
    
    # Validate time_range if provided
    if time_range and time_range not in ["1h", "1d", "7d", "30d"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid time_range value: {time_range}. Valid values are: 1h, 1d, 7d, 30d"
        )
    
    try:
        # Determine time range based on parameters
        time_start, time_end = None, None
        if from_time and to_time:
            # Use explicit from/to time if provided
            time_start, time_end = from_time, to_time
        else:
            # Otherwise calculate from time_range
            time_end = datetime.utcnow()
            if time_range == "1h":
                time_start = time_end - timedelta(hours=1)
            elif time_range == "1d":
                time_start = time_end - timedelta(days=1)
            elif time_range == "7d":
                time_start = time_end - timedelta(days=7)
            else:  # Default to 30d
                time_start = time_end - timedelta(days=30)
        
        # Query alerts with all filters
        alerts, total_count = SecurityQueryService.get_alerts(
            db=db,
            time_start=time_start,
            time_end=time_end,
            severity=severity,
            category=category,
            alert_level=alert_level,
            llm_vendor=llm_vendor,
            agent_id=agent_id,
            trace_id=trace_id,
            span_id=span_id,
            pattern=pattern,
            page=page,
            page_size=page_size
        )
        
        # Format alerts for response
        alerts_data = [format_alert_for_response(alert) for alert in alerts]
        
        # Get basic metrics for the filtered set
        metrics = {}
        if total_count > 0:
            metrics = SecurityQueryService.get_alert_metrics(
                db=db,
                time_start=time_start,
                time_end=time_end,
                agent_id=agent_id
            )
        
        # Construct response
        response = {
            "alerts": alerts_data,
            "total_count": total_count,
            "metrics": metrics,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total_count,
                "pages": (total_count + page_size - 1) // page_size
            },
            "time_range": {
                "from": time_start.isoformat() if time_start else None,
                "to": time_end.isoformat() if time_end else None,
                "description": f"Last {time_range}" if not (from_time and to_time) else "Custom range"
            },
            "filters": {
                "severity": severity,
                "category": category,
                "alert_level": alert_level,
                "llm_vendor": llm_vendor,
                "agent_id": agent_id,
                "trace_id": trace_id,
                "span_id": span_id,
                "pattern": pattern
            }
        }
        
        return response
        
    except Exception as e:
        logger.error(f"Error getting security alerts: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving security alerts: {str(e)}"
        )


@router.get(
    "/alerts/{alert_id}",
    response_model=Dict[str, Any],
    summary="Get detailed information about a specific security alert"
)
async def get_security_alert_details(
    alert_id: int = Path(..., description="Security alert ID"),
    include_related_events: bool = Query(False, description="Include related events by span_id"),
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific security alert.
    
    Returns all data for a security alert, with optional inclusion of related events.
    
    Returns:
        Dict[str, Any]: Detailed alert data
    """
    logger.info(f"Getting details for security alert {alert_id}")
    
    try:
        # Get the alert
        alert = db.query(SecurityAlert).filter(SecurityAlert.id == alert_id).first()
        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Security alert with ID {alert_id} not found"
            )
        
        # Format the alert
        alert_data = format_alert_for_response(alert)
        
        # Include related events if requested
        if include_related_events:
            related_events = SecurityQueryService.get_related_events(db, alert_id)
            alert_data["related_events"] = related_events
        
        return alert_data
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error getting security alert details: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving security alert details: {str(e)}"
        )


@router.get(
    "/alerts/timeseries",
    response_model=Dict[str, Any],
    summary="Get security alerts time series data"
)
async def get_security_alerts_timeseries(
    from_time: Optional[datetime] = Query(None, description="Start time (ISO format)"),
    to_time: Optional[datetime] = Query(None, description="End time (ISO format)"),
    time_range: Optional[str] = Query("7d", description="Predefined time range (1h, 1d, 7d, 30d)"),
    interval: Optional[str] = Query("1d", description="Aggregation interval (1m, 1h, 1d, 7d)"),
    severity: Optional[str] = Query(None, description="Filter by alert severity"),
    category: Optional[str] = Query(None, description="Filter by category"),
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    db: Session = Depends(get_db)
):
    """
    Get time series data for security alerts.
    
    This endpoint provides time-bucketed counts of security alerts for trend analysis.
    
    Returns:
        Dict[str, Any]: Time series data
    """
    logger.info("Getting security alerts time series data")
    
    try:
        # Determine time range
        time_start, time_end = None, None
        if from_time and to_time:
            # Use explicit from/to time if provided
            time_start, time_end = from_time, to_time
        else:
            # Otherwise calculate from time_range
            time_end = datetime.utcnow()
            if time_range == "1h":
                time_start = time_end - timedelta(hours=1)
            elif time_range == "1d":
                time_start = time_end - timedelta(days=1)
            elif time_range == "7d":
                time_start = time_end - timedelta(days=7)
            else:  # Default to 30d
                time_start = time_end - timedelta(days=30)
        
        # Get time series data
        time_series = SecurityQueryService.get_time_series(
            db=db,
            time_start=time_start,
            time_end=time_end,
            interval=interval,
            agent_id=agent_id,
            category=category,
            severity=severity
        )
        
        # Construct response
        response = {
            "time_series": time_series,
            "time_range": {
                "from": time_start.isoformat() if time_start else None,
                "to": time_end.isoformat() if time_end else None,
                "description": f"Last {time_range}" if not (from_time and to_time) else "Custom range"
            },
            "interval": interval,
            "filters": {
                "severity": severity,
                "category": category,
                "agent_id": agent_id
            }
        }
            
        return response
        
    except Exception as e:
        logger.error(f"Error getting security alerts time series: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving security alerts time series: {str(e)}"
        )


@router.get(
    "/overview",
    response_model=Dict[str, Any],
    summary="Get security overview for dashboards"
)
async def get_security_dashboard_overview(
    time_range: str = Query("7d", description="Time range (1h, 1d, 7d, 30d)"),
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    db: Session = Depends(get_db)
):
    """
    Get a comprehensive security overview for dashboards.
    
    This endpoint provides aggregated metrics, recent alerts, and trends
    for building security dashboards.
    
    Returns:
        Dict[str, Any]: Security overview data
    """
    logger.info("Getting security overview")
    
    try:
        # Get security overview data
        overview = get_security_overview(
            db=db,
            time_range=time_range,
            agent_id=agent_id
        )
        
        return overview
        
    except Exception as e:
        logger.error(f"Error getting security overview: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving security overview: {str(e)}"
        ) 