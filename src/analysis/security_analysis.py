"""
Security Alert Analysis Functions

This module provides functions for analyzing security alerts and
transforming the raw data into useful metrics and insights.
"""
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from sqlalchemy.orm import Session

from src.services.security_query import SecurityQueryService


def format_alert_for_response(alert) -> Dict[str, Any]:
    """
    Format a security alert for API response.
    
    Args:
        alert: SecurityAlert instance
        
    Returns:
        Dictionary representation of the alert
    """
    return {
        "id": alert.id,
        "timestamp": alert.timestamp.isoformat(),
        "schema_version": alert.schema_version,
        "trace_id": alert.trace_id,
        "span_id": alert.span_id,
        "parent_span_id": alert.parent_span_id,
        "event_name": alert.event_name,
        "log_level": alert.log_level,
        "alert_level": alert.alert_level,
        "category": alert.category,
        "severity": alert.severity,
        "description": alert.description,
        "llm_vendor": alert.llm_vendor,
        "content_sample": alert.content_sample,
        "detection_time": alert.detection_time.isoformat() if alert.detection_time else None,
        "keywords": alert.keywords,
        "event_id": alert.event_id,
        "agent_id": alert.event.agent_id if alert.event else None,
    }


def get_security_overview(
    db: Session,
    time_range: str = "7d",
    agent_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get a security overview for dashboards.
    
    Args:
        db: Database session
        time_range: Time range string (1h, 1d, 7d, 30d)
        agent_id: Optional agent ID filter
        
    Returns:
        Security overview data
    """
    # Calculate time range
    # Adding 2 hours to use Madrid time (UTC+2)
    now = datetime.utcnow() + timedelta(hours=2)
    if time_range == "1h":
        time_start = now - timedelta(hours=1)
    elif time_range == "1d":
        time_start = now - timedelta(days=1)
    elif time_range == "7d":
        time_start = now - timedelta(days=7)
    elif time_range == "30d":
        time_start = now - timedelta(days=30)
    else:
        # Default to 7 days
        time_start = now - timedelta(days=7)
    
    # Get metrics
    metrics = SecurityQueryService.get_alert_metrics(
        db=db,
        time_start=time_start,
        time_end=now,
        agent_id=agent_id
    )
    
    # Get time series data
    time_series = SecurityQueryService.get_time_series(
        db=db,
        time_start=time_start,
        time_end=now,
        interval="1d" if time_range in ["7d", "30d"] else "1h",
        agent_id=agent_id
    )
    
    # Get recent high severity alerts
    alerts, _ = SecurityQueryService.get_alerts(
        db=db,
        time_start=time_start,
        time_end=now,
        severity=["high", "critical"],
        agent_id=agent_id,
        page=1,
        page_size=5
    )
    
    recent_alerts = [format_alert_for_response(alert) for alert in alerts]
    
    # Construct the response
    return {
        "metrics": metrics,
        "time_series": time_series,
        "recent_alerts": recent_alerts,
        "time_range": {
            "from": time_start.isoformat(),
            "to": now.isoformat(),
            "description": f"Last {time_range}"
        }
    } 