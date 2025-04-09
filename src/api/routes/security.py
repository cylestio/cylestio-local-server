from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Union

from fastapi import APIRouter, Depends, Query, HTTPException, status, Path
from sqlalchemy.orm import Session
from sqlalchemy import func

from src.database.session import get_db
from src.api.schemas.metrics import MetricResponse, MetricDataPoint
from src.models.security_alert import SecurityAlert
from src.models.event import Event
from src.analysis.utils import sql_time_bucket
from src.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

@router.get(
    "/alerts",
    response_model=Dict[str, Any],
    summary="Get security alerts with count and details"
)
async def get_security_alerts(
    from_time: Optional[datetime] = Query(None, description="Start time (ISO format)"),
    to_time: Optional[datetime] = Query(None, description="End time (ISO format)"),
    time_range: Optional[str] = Query("30d", description="Predefined time range (1h, 1d, 7d, 30d)"),
    severity: Optional[str] = Query(None, description="Filter by alert severity (low, medium, high)"),
    alert_type: Optional[str] = Query(None, description="Filter by alert type"),
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    status: Optional[str] = Query(None, description="Filter by alert status (OPEN, RESOLVED, etc.)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=1000, description="Items per page"),
    db: Session = Depends(get_db)
):
    """
    Get security alerts with details and metrics.
    
    This endpoint provides detailed information about security alerts including count, 
    filtering by various criteria, and pagination.
    
    Returns:
        Dict[str, Any]: Security alerts data and metrics
    """
    logger.info("Querying security alerts")
    
    # Validate time_range if provided
    if time_range and time_range not in ["1h", "1d", "7d", "30d"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid time_range value: {time_range}. Valid values are: 1h, 1d, 7d, 30d"
        )
    
    try:
        # Determine time range based on parameters
        if from_time and to_time:
            # Use explicit from/to time if provided
            time_start, time_end = from_time, to_time
        else:
            # Otherwise calculate from time_range
            if time_range == "1h":
                time_start = datetime.utcnow() - timedelta(hours=1)
            elif time_range == "1d":
                time_start = datetime.utcnow() - timedelta(days=1)
            elif time_range == "7d":
                time_start = datetime.utcnow() - timedelta(days=7)
            else:  # Default to 30d
                time_start = datetime.utcnow() - timedelta(days=30)
                
            time_end = datetime.utcnow()
        
        # Base query for alerts
        query = db.query(SecurityAlert).join(
            Event, SecurityAlert.event_id == Event.id
        )
        
        # Apply time filter
        query = query.filter(SecurityAlert.timestamp >= time_start, 
                            SecurityAlert.timestamp <= time_end)
        
        # Apply other filters if provided
        if severity:
            query = query.filter(SecurityAlert.severity == severity.upper())
        
        if alert_type:
            query = query.filter(SecurityAlert.alert_type == alert_type)
        
        if agent_id:
            query = query.filter(Event.agent_id == agent_id)
            
        if status:
            query = query.filter(SecurityAlert.status == status.upper())
            
        # Get total count for pagination
        total_count = query.count()
        
        # Apply pagination
        query = query.order_by(SecurityAlert.timestamp.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        # Execute query
        alerts = query.all()
        
        # Format alerts for response
        alerts_data = []
        for alert in alerts:
            event = alert.event
            alerts_data.append({
                "id": alert.id,
                "alert_type": alert.alert_type,
                "severity": alert.severity,
                "description": alert.description,
                "timestamp": alert.timestamp.isoformat(),
                "status": alert.status,
                "agent_id": event.agent_id if event else None,
                "event_id": alert.event_id,
                "detection_source": alert.detection_source,
                "confidence_score": alert.confidence_score,
                "affected_component": alert.affected_component
            })
        
        # Get summary metrics
        severity_counts = {}
        severity_query = db.query(
            SecurityAlert.severity, 
            func.count().label('count')
        ).join(
            Event, SecurityAlert.event_id == Event.id
        ).filter(
            SecurityAlert.timestamp >= time_start,
            SecurityAlert.timestamp <= time_end
        )
        
        if agent_id:
            severity_query = severity_query.filter(Event.agent_id == agent_id)
            
        if alert_type:
            severity_query = severity_query.filter(SecurityAlert.alert_type == alert_type)
            
        severity_query = severity_query.group_by(SecurityAlert.severity)
        severity_results = severity_query.all()
        
        for result in severity_results:
            severity_counts[result.severity] = result.count
            
        # Get alert type counts
        type_counts = {}
        type_query = db.query(
            SecurityAlert.alert_type, 
            func.count().label('count')
        ).join(
            Event, SecurityAlert.event_id == Event.id
        ).filter(
            SecurityAlert.timestamp >= time_start,
            SecurityAlert.timestamp <= time_end
        )
        
        if agent_id:
            type_query = type_query.filter(Event.agent_id == agent_id)
            
        if severity:
            type_query = type_query.filter(SecurityAlert.severity == severity.upper())
            
        type_query = type_query.group_by(SecurityAlert.alert_type)
        type_results = type_query.all()
        
        for result in type_results:
            type_counts[result.alert_type] = result.count
        
        # Construct response
        response = {
            "alerts": alerts_data,
            "total_count": total_count,
            "metrics": {
                "by_severity": severity_counts,
                "by_type": type_counts
            },
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total_count,
                "pages": (total_count + page_size - 1) // page_size
            },
            "time_range": {
                "from": time_start.isoformat(),
                "to": time_end.isoformat(),
                "description": f"Last {time_range}" if not (from_time and to_time) else "Custom range"
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
    "/alerts/count",
    response_model=Dict[str, Any],
    summary="Get security alerts count"
)
async def get_security_alerts_count(
    from_time: Optional[datetime] = Query(None, description="Start time (ISO format)"),
    to_time: Optional[datetime] = Query(None, description="End time (ISO format)"),
    time_range: Optional[str] = Query("30d", description="Predefined time range (1h, 1d, 7d, 30d)"),
    severity: Optional[str] = Query(None, description="Filter by alert severity (low, medium, high)"),
    alert_type: Optional[str] = Query(None, description="Filter by alert type"),
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    db: Session = Depends(get_db)
):
    """
    Get security alerts count with optional filtering.
    
    This endpoint provides a simple count of security alerts.
    
    Returns:
        Dict[str, Any]: Count of security alerts
    """
    logger.info("Querying security alerts count")
    
    # Validate time_range if provided
    if time_range and time_range not in ["1h", "1d", "7d", "30d"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid time_range value: {time_range}. Valid values are: 1h, 1d, 7d, 30d"
        )
    
    try:
        # Determine time range based on parameters
        if from_time and to_time:
            # Use explicit from/to time if provided
            time_start, time_end = from_time, to_time
        else:
            # Otherwise calculate from time_range
            if time_range == "1h":
                time_start = datetime.utcnow() - timedelta(hours=1)
            elif time_range == "1d":
                time_start = datetime.utcnow() - timedelta(days=1)
            elif time_range == "7d":
                time_start = datetime.utcnow() - timedelta(days=7)
            else:  # Default to 30d
                time_start = datetime.utcnow() - timedelta(days=30)
                
            time_end = datetime.utcnow()
        
        # Base query for alerts count
        query = db.query(func.count(SecurityAlert.id)).join(
            Event, SecurityAlert.event_id == Event.id
        )
        
        # Apply time filter
        query = query.filter(SecurityAlert.timestamp >= time_start, 
                            SecurityAlert.timestamp <= time_end)
        
        # Apply other filters if provided
        if severity:
            query = query.filter(SecurityAlert.severity == severity.upper())
        
        if alert_type:
            query = query.filter(SecurityAlert.alert_type == alert_type)
        
        if agent_id:
            query = query.filter(Event.agent_id == agent_id)
            
        # Execute query
        total_count = query.scalar() or 0
        
        # Construct response
        response = {
            "count": total_count,
            "time_range": {
                "from": time_start.isoformat(),
                "to": time_end.isoformat(),
                "description": f"Last {time_range}" if not (from_time and to_time) else "Custom range"
            }
        }
        
        return response
        
    except Exception as e:
        logger.error(f"Error getting security alerts count: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving security alerts count: {str(e)}"
        )

@router.get(
    "/alerts/timeseries",
    response_model=MetricResponse,
    summary="Get security alerts time series data"
)
async def get_security_alerts_timeseries(
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
    Get security alerts as time series data with optional filtering.
    
    This endpoint provides time-bucketed alert data for trend analysis.
    
    Returns:
        MetricResponse: Time series data for security alerts
    """
    logger.info("Querying security alerts time series")
    
    # Validate time_range if provided
    if time_range and time_range not in ["1h", "1d", "7d", "30d"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid time_range value: {time_range}. Valid values are: 1h, 1d, 7d, 30d"
        )
    
    try:
        # Determine time range based on parameters
        if from_time and to_time:
            # Use explicit from/to time if provided
            time_start, time_end = from_time, to_time
        else:
            # Otherwise calculate from time_range
            if time_range == "1h":
                time_start = datetime.utcnow() - timedelta(hours=1)
            elif time_range == "1d":
                time_start = datetime.utcnow() - timedelta(days=1)
            elif time_range == "7d":
                time_start = datetime.utcnow() - timedelta(days=7)
            else:  # Default to 30d
                time_start = datetime.utcnow() - timedelta(days=30)
                
            time_end = datetime.utcnow()
        
        # Determine interval for time bucketing
        time_interval = "day"
        if interval == "1m":
            time_interval = "minute"
        elif interval == "1h":
            time_interval = "hour"
        elif interval == "1d":
            time_interval = "day"
        elif interval == "7d":
            time_interval = "week"
        
        # Base query for alerts time series
        query = db.query(
            sql_time_bucket(SecurityAlert.timestamp, time_interval).label('time_bucket'),
            func.count().label('alert_count')
        ).join(
            Event, SecurityAlert.event_id == Event.id
        )
        
        # Apply time filter
        query = query.filter(SecurityAlert.timestamp >= time_start, 
                            SecurityAlert.timestamp <= time_end)
        
        # Apply other filters if provided
        if severity:
            query = query.filter(SecurityAlert.severity == severity.upper())
        
        if alert_type:
            query = query.filter(SecurityAlert.alert_type == alert_type)
        
        if agent_id:
            query = query.filter(Event.agent_id == agent_id)
            
        # Group by time bucket
        query = query.group_by('time_bucket')
        
        # Order by time bucket
        query = query.order_by('time_bucket')
        
        # Execute query
        results = query.all()
        
        # Format the response
        data_points = []
        for result in results:
            data_points.append(
                MetricDataPoint(
                    timestamp=result.time_bucket,
                    value=result.alert_count,
                    dimensions={}
                )
            )
            
        # If no data points were found, return a single data point with count 0
        if not data_points:
            data_points.append(
                MetricDataPoint(
                    timestamp=time_start + (time_end - time_start) / 2,
                    value=0,
                    dimensions={}
                )
            )
            
        # Create response
        response = MetricResponse(
            metric="security_alert_count",
            from_time=time_start,
            to_time=time_end,
            interval=interval,
            data=data_points
        )
            
        return response
        
    except Exception as e:
        logger.error(f"Error getting security alerts time series: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving security alerts time series: {str(e)}"
        ) 