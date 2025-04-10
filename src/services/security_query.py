"""
Security Alert Query Service

This module provides methods for querying security alerts with flexible filtering
and analytical capabilities for investigations.
"""
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple

from sqlalchemy import func, and_, or_, desc, String
from sqlalchemy.orm import Session, joinedload

from src.models.security_alert import SecurityAlert
from src.models.event import Event


class SecurityQueryService:
    """Service for querying and analyzing security alerts."""
    
    @staticmethod
    def get_alerts(
        db: Session,
        time_start: Optional[datetime] = None,
        time_end: Optional[datetime] = None,
        severity: Optional[List[str]] = None,
        category: Optional[List[str]] = None,
        alert_level: Optional[List[str]] = None,
        llm_vendor: Optional[List[str]] = None,
        agent_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        span_id: Optional[str] = None,
        pattern: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[SecurityAlert], int]:
        """
        Query security alerts with flexible filtering.
        
        Args:
            db: Database session
            time_start: Start time for filtering
            time_end: End time for filtering
            severity: List of severity levels to include
            category: List of categories to include
            alert_level: List of alert levels to include
            llm_vendor: List of LLM vendors to include
            agent_id: Filter by specific agent
            trace_id: Filter by trace ID
            span_id: Filter by span ID
            pattern: Search for specific pattern in keywords
            page: Page number (1-indexed)
            page_size: Number of items per page
            
        Returns:
            Tuple of (list of alerts, total count)
        """
        query = db.query(SecurityAlert).join(
            Event, SecurityAlert.event_id == Event.id
        )
        
        # Apply time filters
        if time_start:
            query = query.filter(SecurityAlert.timestamp >= time_start)
        if time_end:
            query = query.filter(SecurityAlert.timestamp <= time_end)
        
        # Apply security property filters
        if severity and len(severity) > 0:
            query = query.filter(SecurityAlert.severity.in_(severity))
        
        if category and len(category) > 0:
            query = query.filter(SecurityAlert.category.in_(category))
        
        if alert_level and len(alert_level) > 0:
            query = query.filter(SecurityAlert.alert_level.in_(alert_level))
        
        if llm_vendor and len(llm_vendor) > 0:
            query = query.filter(SecurityAlert.llm_vendor.in_(llm_vendor))
        
        # Apply agent filter
        if agent_id:
            query = query.filter(Event.agent_id == agent_id)
        
        # Apply trace/span filters for correlation
        if trace_id:
            query = query.filter(SecurityAlert.trace_id == trace_id)
        
        if span_id:
            query = query.filter(SecurityAlert.span_id == span_id)
        
        # Apply pattern search on keywords JSON field
        if pattern:
            # This is PostgreSQL-specific JSON search
            query = query.filter(
                SecurityAlert.keywords.cast(String).ilike(f'%{pattern}%')
            )
        
        # Get total count for pagination
        total_count = query.count()
        
        # Apply pagination
        query = query.order_by(desc(SecurityAlert.timestamp))
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        return query.all(), total_count
    
    @staticmethod
    def get_related_events(db: Session, alert_id: int) -> List[Dict[str, Any]]:
        """
        Get events related to a security alert by span_id.
        
        Args:
            db: Database session
            alert_id: ID of the security alert
            
        Returns:
            List of related events
        """
        # Get the alert
        alert = db.query(SecurityAlert).filter(SecurityAlert.id == alert_id).first()
        if not alert:
            return []
            
        # Find events with the same span_id
        events = db.query(Event).filter(
            Event.span_id == alert.span_id
        ).order_by(Event.timestamp).all()
        
        return [event.to_dict() for event in events]
    
    @staticmethod
    def get_alert_metrics(
        db: Session,
        time_start: datetime,
        time_end: datetime,
        agent_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get security alert metrics.
        
        Args:
            db: Database session
            time_start: Start time
            time_end: End time
            agent_id: Optional agent ID filter
            
        Returns:
            Dictionary of metrics
        """
        metrics = {}
        
        # Base query
        base_query = db.query(SecurityAlert).join(
            Event, SecurityAlert.event_id == Event.id
        ).filter(
            SecurityAlert.timestamp >= time_start,
            SecurityAlert.timestamp <= time_end
        )
        
        if agent_id:
            base_query = base_query.filter(Event.agent_id == agent_id)
        
        # Total count
        metrics["total_count"] = base_query.count()
        
        # Severity breakdown
        severity_counts = {}
        severity_query = db.query(
            SecurityAlert.severity,
            func.count(SecurityAlert.id).label("count")
        ).filter(
            SecurityAlert.timestamp >= time_start,
            SecurityAlert.timestamp <= time_end
        )
        
        if agent_id:
            severity_query = severity_query.join(
                Event, SecurityAlert.event_id == Event.id
            ).filter(Event.agent_id == agent_id)
            
        severity_query = severity_query.group_by(SecurityAlert.severity)
        
        for row in severity_query.all():
            severity_counts[row.severity] = row.count
            
        metrics["by_severity"] = severity_counts
        
        # Category breakdown
        category_counts = {}
        category_query = db.query(
            SecurityAlert.category,
            func.count(SecurityAlert.id).label("count")
        ).filter(
            SecurityAlert.timestamp >= time_start,
            SecurityAlert.timestamp <= time_end
        )
        
        if agent_id:
            category_query = category_query.join(
                Event, SecurityAlert.event_id == Event.id
            ).filter(Event.agent_id == agent_id)
            
        category_query = category_query.group_by(SecurityAlert.category)
        
        for row in category_query.all():
            category_counts[row.category] = row.count
            
        metrics["by_category"] = category_counts
        
        # Alert level breakdown
        level_counts = {}
        level_query = db.query(
            SecurityAlert.alert_level,
            func.count(SecurityAlert.id).label("count")
        ).filter(
            SecurityAlert.timestamp >= time_start,
            SecurityAlert.timestamp <= time_end
        )
        
        if agent_id:
            level_query = level_query.join(
                Event, SecurityAlert.event_id == Event.id
            ).filter(Event.agent_id == agent_id)
            
        level_query = level_query.group_by(SecurityAlert.alert_level)
        
        for row in level_query.all():
            level_counts[row.alert_level] = row.count
            
        metrics["by_alert_level"] = level_counts
        
        # LLM vendor breakdown
        vendor_counts = {}
        vendor_query = db.query(
            SecurityAlert.llm_vendor,
            func.count(SecurityAlert.id).label("count")
        ).filter(
            SecurityAlert.timestamp >= time_start,
            SecurityAlert.timestamp <= time_end
        )
        
        if agent_id:
            vendor_query = vendor_query.join(
                Event, SecurityAlert.event_id == Event.id
            ).filter(Event.agent_id == agent_id)
            
        vendor_query = vendor_query.group_by(SecurityAlert.llm_vendor)
        
        for row in vendor_query.all():
            vendor_counts[row.llm_vendor or "unknown"] = row.count
            
        metrics["by_llm_vendor"] = vendor_counts
        
        return metrics
    
    @staticmethod
    def get_time_series(
        db: Session,
        time_start: datetime,
        time_end: datetime,
        interval: str = "1d",
        agent_id: Optional[str] = None,
        category: Optional[str] = None,
        severity: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get time series data for security alerts.
        
        Args:
            db: Database session
            time_start: Start time
            time_end: End time
            interval: Time bucket interval (e.g., '1h', '1d')
            agent_id: Optional agent ID filter
            category: Optional category filter
            severity: Optional severity filter
            
        Returns:
            List of time series data points
        """
        from src.analysis.utils import sql_time_bucket
        
        # Base query
        query = db.query(
            sql_time_bucket(SecurityAlert.timestamp, interval).label("bucket"),
            func.count(SecurityAlert.id).label("count")
        ).filter(
            SecurityAlert.timestamp >= time_start,
            SecurityAlert.timestamp <= time_end
        )
        
        # Apply filters
        if agent_id:
            query = query.join(
                Event, SecurityAlert.event_id == Event.id
            ).filter(Event.agent_id == agent_id)
            
        if category:
            query = query.filter(SecurityAlert.category == category)
            
        if severity:
            query = query.filter(SecurityAlert.severity == severity)
        
        # Group by time bucket
        query = query.group_by("bucket").order_by("bucket")
        
        # Format the results
        result = []
        for row in query.all():
            # Make sure we have a valid timestamp that can be serialized
            if row.bucket:
                timestamp = row.bucket
                if isinstance(timestamp, datetime):
                    timestamp = timestamp.isoformat()
                elif not isinstance(timestamp, str):
                    timestamp = str(timestamp)
            else:
                # Use current time as fallback
                timestamp = datetime.utcnow().isoformat()
                
            result.append({
                "timestamp": timestamp,
                "count": row.count
            })
            
        return result 