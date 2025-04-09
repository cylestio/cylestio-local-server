"""
Security alert metrics endpoints.
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from src.database.session import get_db
from src.models.security_alert import SecurityAlert
from src.models.event import Event
from src.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

@router.get(
    "/security-metrics/alerts/stats",
    response_model=Dict[str, Any],
    summary="Get security alerts statistics"
)
async def get_security_alerts_stats(
    from_time: Optional[datetime] = Query(None, description="Start time (ISO format)"),
    to_time: Optional[datetime] = Query(None, description="End time (ISO format)"),
    time_range: Optional[str] = Query("30d", description="Predefined time range (1h, 1d, 7d, 30d)"),
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    db: Session = Depends(get_db)
):
    """
    Get security alerts statistics including count and breakdown by severity and type.
    
    Returns:
        Dict[str, Any]: Security alerts statistics
    """
    logger.info("Querying security alert statistics")
    
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
        
        # Get total count
        count_query = db.query(func.count(SecurityAlert.id)).join(
            Event, SecurityAlert.event_id == Event.id
        ).filter(
            SecurityAlert.timestamp >= time_start,
            SecurityAlert.timestamp <= time_end
        )
        
        if agent_id:
            count_query = count_query.filter(Event.agent_id == agent_id)
            
        total_count = count_query.scalar() or 0
        
        # Get severity breakdown
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
            
        severity_query = severity_query.group_by(SecurityAlert.severity)
        severity_results = severity_query.all()
        
        severity_counts = {result.severity: result.count for result in severity_results}
        
        # Get alert type breakdown
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
            
        type_query = type_query.group_by(SecurityAlert.alert_type)
        type_results = type_query.all()
        
        type_counts = {result.alert_type: result.count for result in type_results}
        
        # Construct response
        return {
            "count": total_count,
            "by_severity": severity_counts,
            "by_type": type_counts,
            "time_range": {
                "from": time_start.isoformat(),
                "to": time_end.isoformat(),
                "description": f"Last {time_range}" if not (from_time and to_time) else "Custom range"
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting security alert statistics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving security alert statistics: {str(e)}"
        ) 