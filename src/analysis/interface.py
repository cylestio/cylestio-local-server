"""
Core query interface for the analysis layer.

This module provides the base query interface and parameter structures for
analyzing telemetry data from the database.
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Union, Tuple, TypeVar, Generic

from sqlalchemy import func, text, and_, or_, desc, asc
from sqlalchemy.orm import Session

# Import logging
import logging

# Set up logger
logger = logging.getLogger(__name__)

# Type variable for generic return types
T = TypeVar('T')


class TimeResolution(str, Enum):
    """Time resolutions for time-series queries."""
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


class SortDirection(str, Enum):
    """Sort directions for query results."""
    ASC = "asc"
    DESC = "desc"


class TimeRange(str, Enum):
    """Common time ranges for metrics."""
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


@dataclass
class TimeRangeParams:
    """
    Time range parameters for filtering events by time.
    
    Attributes:
        start: Start time (inclusive)
        end: End time (inclusive)
    """
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    
    @classmethod
    def last_hour(cls) -> 'TimeRangeParams':
        """Create a time range for the last hour."""
        now = datetime.utcnow()
        return cls(start=now - timedelta(hours=1), end=now)
    
    @classmethod
    def last_day(cls) -> 'TimeRangeParams':
        """Create a time range for the last 24 hours."""
        now = datetime.utcnow()
        return cls(start=now - timedelta(days=1), end=now)
    
    @classmethod
    def last_week(cls) -> 'TimeRangeParams':
        """Create a time range for the last 7 days."""
        now = datetime.utcnow()
        return cls(start=now - timedelta(days=7), end=now)
    
    @classmethod
    def last_month(cls) -> 'TimeRangeParams':
        """Create a time range for the last 30 days."""
        now = datetime.utcnow()
        return cls(start=now - timedelta(days=30), end=now)


@dataclass
class PaginationParams:
    """
    Pagination parameters for query results.
    
    Attributes:
        page: Page number (1-indexed)
        page_size: Number of items per page
    """
    page: int = 1
    page_size: int = 50
    
    @property
    def offset(self) -> int:
        """Get the SQL offset for the current page."""
        return (self.page - 1) * self.page_size
    
    @property
    def limit(self) -> int:
        """Get the SQL limit for the current page."""
        return self.page_size


# Alias for backwards compatibility
Pagination = PaginationParams


@dataclass
class SortParams:
    """
    Sort parameters for query results.
    
    Attributes:
        field: Field to sort by
        direction: Sort direction
    """
    field: str
    direction: SortDirection = SortDirection.DESC


@dataclass
class QueryResult(Generic[T]):
    """
    Generic container for query results with pagination.
    
    Attributes:
        items: List of result items
        total: Total number of items (without pagination)
        page: Current page number
        page_size: Number of items per page
        total_pages: Total number of pages
    """
    items: List[T]
    total: int
    page: int
    page_size: int
    
    @property
    def total_pages(self) -> int:
        """Get the total number of pages."""
        return (self.total + self.page_size - 1) // self.page_size
    
    @property
    def has_next(self) -> bool:
        """Check if there is a next page."""
        return self.page < self.total_pages
    
    @property
    def has_prev(self) -> bool:
        """Check if there is a previous page."""
        return self.page > 1


@dataclass
class BaseQueryParams:
    """
    Base parameters for telemetry data queries.
    
    Attributes:
        time_range: Time range filter
        agent_ids: Filter by agent IDs
        session_ids: Filter by session IDs
        trace_ids: Filter by trace IDs
        pagination: Pagination parameters
        sort: Sort parameters
    """
    time_range: Optional[TimeRangeParams] = None
    agent_ids: List[str] = field(default_factory=list)
    session_ids: List[str] = field(default_factory=list)
    trace_ids: List[str] = field(default_factory=list)
    pagination: PaginationParams = field(default_factory=PaginationParams)
    sort: Optional[SortParams] = None


@dataclass
class TimeSeriesParams(BaseQueryParams):
    """
    Parameters for time-series queries.
    
    Attributes:
        resolution: Time resolution for grouping
        metric: Metric to calculate
    """
    resolution: TimeResolution = TimeResolution.HOUR
    metric: str = "count"


@dataclass
class MetricParams(BaseQueryParams):
    """
    Parameters for metric queries.
    
    Attributes:
        group_by: Fields to group by
        filters: Additional filters as key-value pairs
    """
    group_by: List[str] = field(default_factory=list)
    filters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RelationQueryParams(BaseQueryParams):
    """
    Parameters for queries across event relationships.
    
    Attributes:
        relation_type: Type of relation to query
        include_related: Whether to include related events in results
    """
    relation_type: str = ""
    include_related: bool = False


@dataclass
class MetricDataPoint:
    """
    A single data point for a metric.
    
    Attributes:
        timestamp: Timestamp for the data point
        value: Value of the metric
        dimensions: Optional dimension values
    """
    timestamp: datetime
    value: Union[int, float]
    dimensions: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MetricSummary:
    """
    Summary of a metric with trend information.
    
    Attributes:
        metric: Name of the metric
        value: Current value
        change: Percentage change from previous period
        trend: Trend direction (up, down, flat)
    """
    metric: str
    value: Union[int, float]
    change: Optional[float] = None
    trend: Optional[str] = None


@dataclass
class MetricQuery:
    """
    Query parameters for fetching metrics.
    
    Attributes:
        metric: Metric name to fetch
        from_time: Start time for the query
        to_time: End time for the query
        time_range: Predefined time range (1h, 1d, 7d, 30d) or TimeRange enum
        interval: Time resolution for the results
        agent_id: Optional agent ID to filter by
        dimensions: Optional dimensions to break down by
    """
    metric: str
    from_time: Optional[datetime] = None
    to_time: Optional[datetime] = None
    time_range: Optional[Union[str, TimeRange]] = None
    interval: Optional[TimeResolution] = None
    agent_id: Optional[str] = None
    dimensions: List[str] = field(default_factory=list)


@dataclass
class MetricResponse:
    """
    Response containing metric data.
    
    Attributes:
        metric: Name of the metric
        from_time: Start time of the data
        to_time: End time of the data
        interval: Time resolution of the data
        data: List of data points
    """
    metric: str
    from_time: datetime
    to_time: datetime
    interval: Optional[str] = None
    data: List[MetricDataPoint] = field(default_factory=list)


@dataclass
class DashboardResponse:
    """
    Response containing dashboard metrics.
    
    Attributes:
        period: Description of the time period
        metrics: List of metric summaries
    """
    period: str
    metrics: List[MetricSummary] = field(default_factory=list)


class AnalysisInterface:
    """
    Base interface for analysis queries.
    
    This class provides the foundation for implementing specific metric
    and analysis queries against the telemetry database.
    """
    
    def __init__(self, db_session: Session):
        """
        Initialize the analysis interface.
        
        Args:
            db_session: SQLAlchemy database session
        """
        self.db_session = db_session
    
    def apply_time_filters(self, query, time_range: Optional[TimeRangeParams], timestamp_column):
        """
        Apply time range filters to a query.
        
        Args:
            query: SQLAlchemy query object
            time_range: Time range to filter by
            timestamp_column: Column to filter on
            
        Returns:
            The modified query
        """
        if time_range:
            if time_range.start:
                query = query.filter(timestamp_column >= time_range.start)
            if time_range.end:
                query = query.filter(timestamp_column <= time_range.end)
        return query
    
    def apply_filters(self, query, params: BaseQueryParams, model):
        """
        Apply common filters from query parameters.
        
        Args:
            query: SQLAlchemy query object
            params: Query parameters
            model: SQLAlchemy model class
            
        Returns:
            The modified query
        """
        # Apply time range filter
        if params.time_range:
            query = self.apply_time_filters(query, params.time_range, model.timestamp)
        
        # Filter by agent IDs
        if params.agent_ids:
            query = query.filter(model.agent_id.in_(params.agent_ids))
        
        # Filter by session IDs
        if params.session_ids:
            query = query.filter(model.session_id.in_(params.session_ids))
        
        # Filter by trace IDs
        if params.trace_ids:
            query = query.filter(model.trace_id.in_(params.trace_ids))
        
        return query
    
    def apply_sorting(self, query, params: BaseQueryParams, model):
        """
        Apply sorting to a query.
        
        Args:
            query: SQLAlchemy query object
            params: Query parameters
            model: SQLAlchemy model class
            
        Returns:
            The modified query
        """
        if params.sort:
            # Get the column to sort by
            if hasattr(model, params.sort.field):
                column = getattr(model, params.sort.field)
                
                # Apply sort direction
                if params.sort.direction == SortDirection.DESC:
                    query = query.order_by(desc(column))
                else:
                    query = query.order_by(asc(column))
        
        return query
    
    def apply_pagination(self, query, pagination: PaginationParams):
        """
        Apply pagination to a query.
        
        Args:
            query: SQLAlchemy query object
            pagination: Pagination parameters
            
        Returns:
            The modified query
        """
        return query.offset(pagination.offset).limit(pagination.limit)
    
    def get_total_count(self, query):
        """
        Get the total count for a query (without pagination).
        
        Args:
            query: SQLAlchemy query object
            
        Returns:
            The total count
        """
        count_query = query.with_entities(func.count())
        return count_query.scalar()
    
    def execute_paginated_query(
        self, 
        query, 
        params: BaseQueryParams,
        count_query=None
    ) -> QueryResult:
        """
        Execute a paginated query and return the results.
        
        Args:
            query: SQLAlchemy query object
            params: Query parameters
            count_query: Optional separate query for counting total items
            
        Returns:
            QueryResult with the results and pagination info
        """
        # Apply pagination
        paginated_query = self.apply_pagination(query, params.pagination)
        
        # Get the results
        items = paginated_query.all()
        
        # Get the total count
        if count_query is None:
            # Use the original query to get the count
            total = self.get_total_count(query)
        else:
            # Use the provided count query
            total = count_query.scalar()
        
        # Return the results with pagination info
        return QueryResult(
            items=items,
            total=total,
            page=params.pagination.page,
            page_size=params.pagination.page_size
        )

def get_metric(query: MetricQuery, db: Session) -> MetricResponse:
    """
    Get metric data based on the query
    
    Args:
        query: Metric query parameters
        db: Database session
        
    Returns:
        MetricResponse: Metric data response
        
    Raises:
        ValueError: If the metric type is invalid or required parameters are missing
    """
    logger.info(f"Getting metric: {query.metric}")
    
    # Calculate time range if using predefined range
    from_time = query.from_time
    to_time = query.to_time
    
    if query.time_range:
        to_time = datetime.utcnow()
        time_range_str = query.time_range.value if isinstance(query.time_range, TimeRange) else query.time_range
        
        if time_range_str == "1h":
            from_time = to_time - timedelta(hours=1)
        elif time_range_str == "1d":
            from_time = to_time - timedelta(days=1)
        elif time_range_str == "7d":
            from_time = to_time - timedelta(days=7)
        elif time_range_str == "30d":
            from_time = to_time - timedelta(days=30)
        else:
            raise ValueError(f"Invalid time range value: {time_range_str}. Valid values are: 1h, 1d, 7d, 30d")
    
    # Validate time range
    if from_time is None or to_time is None:
        raise ValueError("Time range is required. Provide either from_time and to_time, or time_range.")
        
    # Switch based on metric type
    if query.metric == "llm_request_count":
        data = get_llm_request_count(db, from_time, to_time, query.agent_id, query.interval, query.dimensions)
    elif query.metric == "llm_token_usage":
        data = get_llm_token_usage(db, from_time, to_time, query.agent_id, query.interval, query.dimensions)
    elif query.metric == "llm_response_time":
        data = get_llm_response_time(db, from_time, to_time, query.agent_id, query.interval, query.dimensions)
    elif query.metric == "tool_execution_count":
        data = get_tool_execution_count(db, from_time, to_time, query.agent_id, query.interval, query.dimensions)
    elif query.metric == "tool_success_rate":
        data = get_tool_success_rate(db, from_time, to_time, query.agent_id, query.interval, query.dimensions)
    elif query.metric == "error_count":
        data = get_error_count(db, from_time, to_time, query.agent_id, query.interval, query.dimensions)
    elif query.metric == "session_count":
        data = get_session_count(db, from_time, to_time, query.agent_id, query.interval, query.dimensions)
    else:
        raise ValueError(f"Invalid metric type: {query.metric}")
        
    # Create response
    return MetricResponse(
        metric=query.metric,
        from_time=from_time,
        to_time=to_time,
        interval=query.interval if isinstance(query.interval, str) else (query.interval.value if query.interval else None),
        data=data
    )

def get_dashboard_metrics(time_range: TimeRange, agent_id: Optional[str], db: Session) -> DashboardResponse:
    """
    Get dashboard metrics summary
    
    Args:
        time_range: Time range for the metrics
        agent_id: Optional agent ID to filter by
        db: Database session
        
    Returns:
        DashboardResponse: Dashboard metrics summary
    """
    logger.info(f"Getting dashboard metrics for time range: {time_range}")
    
    # Calculate time range
    to_time = datetime.utcnow()
    
    # Handle all possible time range values
    if time_range == TimeRange.HOUR:
        from_time = to_time - timedelta(hours=1)
        prev_from_time = from_time - timedelta(hours=1)
        period = "1 hour"
    elif time_range == TimeRange.DAY:
        from_time = to_time - timedelta(days=1)
        prev_from_time = from_time - timedelta(days=1)
        period = "24 hours"
    elif time_range == TimeRange.WEEK:
        from_time = to_time - timedelta(days=7)
        prev_from_time = from_time - timedelta(days=7)
        period = "7 days"
    elif time_range == TimeRange.MONTH:
        from_time = to_time - timedelta(days=30)
        prev_from_time = from_time - timedelta(days=30)
        period = "30 days"
    else:
        # Default to 24 hours if an unknown time range is provided
        logger.warning(f"Unknown time range: {time_range}, defaulting to 24 hours")
        from_time = to_time - timedelta(days=1)
        prev_from_time = from_time - timedelta(days=1)
        period = "24 hours"
    
    # Get current metrics
    metrics = []
    
    # LLM request count
    request_count = get_llm_request_total(db, from_time, to_time, agent_id)
    prev_request_count = get_llm_request_total(db, prev_from_time, from_time, agent_id)
    metrics.append(create_metric_summary("llm_request_count", request_count, prev_request_count))
    
    # Token usage
    token_usage = get_llm_token_total(db, from_time, to_time, agent_id)
    prev_token_usage = get_llm_token_total(db, prev_from_time, from_time, agent_id)
    metrics.append(create_metric_summary("llm_token_usage", token_usage, prev_token_usage))
    
    # Average response time
    avg_response_time = get_llm_avg_response_time(db, from_time, to_time, agent_id)
    prev_avg_response_time = get_llm_avg_response_time(db, prev_from_time, from_time, agent_id)
    metrics.append(create_metric_summary("llm_avg_response_time", avg_response_time, prev_avg_response_time))
    
    # Tool execution count
    tool_count = get_tool_execution_total(db, from_time, to_time, agent_id)
    prev_tool_count = get_tool_execution_total(db, prev_from_time, from_time, agent_id)
    metrics.append(create_metric_summary("tool_execution_count", tool_count, prev_tool_count))
    
    # Error count
    error_count = get_error_total(db, from_time, to_time, agent_id)
    prev_error_count = get_error_total(db, prev_from_time, from_time, agent_id)
    metrics.append(create_metric_summary("error_count", error_count, prev_error_count))
    
    # Session count
    session_count = get_session_total(db, from_time, to_time, agent_id)
    prev_session_count = get_session_total(db, prev_from_time, from_time, agent_id)
    metrics.append(create_metric_summary("session_count", session_count, prev_session_count))
    
    return DashboardResponse(
        period=period,
        metrics=metrics
    )

def create_metric_summary(metric: str, value: Union[int, float], prev_value: Union[int, float]) -> MetricSummary:
    """
    Create a metric summary with change and trend
    
    Args:
        metric: Metric name
        value: Current value
        prev_value: Previous value
        
    Returns:
        MetricSummary: Metric summary
    """
    # Calculate change percentage
    if prev_value and prev_value > 0:
        change = ((value - prev_value) / prev_value) * 100
    else:
        change = None
        
    # Determine trend
    if change is None:
        trend = None
    elif change > 5:
        trend = "up"
    elif change < -5:
        trend = "down"
    else:
        trend = "flat"
        
    return MetricSummary(
        metric=metric,
        value=value,
        change=change,
        trend=trend
    )

# Placeholder implementations for metric calculation functions
# These would be replaced with actual implementations using the database models

def get_llm_request_count(db: Session, from_time: datetime, to_time: datetime, 
                        agent_id: Optional[str] = None, interval: Optional[str] = None, 
                        dimensions: Optional[List[str]] = None) -> List[MetricDataPoint]:
    """Placeholder for LLM request count metrics"""
    # Placeholder implementation
    return [
        MetricDataPoint(timestamp=datetime.utcnow(), value=100)
    ]

def get_llm_token_usage(db: Session, from_time: datetime, to_time: datetime, 
                      agent_id: Optional[str] = None, interval: Optional[str] = None, 
                      dimensions: Optional[List[str]] = None) -> List[MetricDataPoint]:
    """Placeholder for LLM token usage metrics"""
    # Placeholder implementation
    return [
        MetricDataPoint(timestamp=datetime.utcnow(), value=10000)
    ]

def get_llm_response_time(db: Session, from_time: datetime, to_time: datetime, 
                        agent_id: Optional[str] = None, interval: Optional[str] = None, 
                        dimensions: Optional[List[str]] = None) -> List[MetricDataPoint]:
    """Placeholder for LLM response time metrics"""
    # Placeholder implementation
    return [
        MetricDataPoint(timestamp=datetime.utcnow(), value=1500)
    ]

def get_tool_execution_count(db: Session, from_time: datetime, to_time: datetime, 
                           agent_id: Optional[str] = None, interval: Optional[str] = None, 
                           dimensions: Optional[List[str]] = None) -> List[MetricDataPoint]:
    """Placeholder for tool execution count metrics"""
    # Placeholder implementation
    return [
        MetricDataPoint(timestamp=datetime.utcnow(), value=50)
    ]

def get_tool_success_rate(db: Session, from_time: datetime, to_time: datetime, 
                        agent_id: Optional[str] = None, interval: Optional[str] = None, 
                        dimensions: Optional[List[str]] = None) -> List[MetricDataPoint]:
    """Placeholder for tool success rate metrics"""
    # Placeholder implementation
    return [
        MetricDataPoint(timestamp=datetime.utcnow(), value=0.95)
    ]

def get_error_count(db: Session, from_time: datetime, to_time: datetime, 
                  agent_id: Optional[str] = None, interval: Optional[str] = None, 
                  dimensions: Optional[List[str]] = None) -> List[MetricDataPoint]:
    """Placeholder for error count metrics"""
    # Placeholder implementation
    return [
        MetricDataPoint(timestamp=datetime.utcnow(), value=5)
    ]

def get_session_count(db: Session, from_time: datetime, to_time: datetime, 
                    agent_id: Optional[str] = None, interval: Optional[str] = None, 
                    dimensions: Optional[List[str]] = None) -> List[MetricDataPoint]:
    """
    Get session count metrics with optional filtering by agent.
    
    Args:
        db: Database session
        from_time: Start time for the query range
        to_time: End time for the query range
        agent_id: Optional agent ID to filter by
        interval: Optional time interval for aggregation
        dimensions: Optional dimensions to group by
        
    Returns:
        List[MetricDataPoint]: Session count data points
    """
    from src.models.session import Session as SessionModel
    from sqlalchemy import or_
    
    # Base query to count sessions
    query = db.query(SessionModel)
    
    # Apply filters
    if agent_id:
        query = query.filter(SessionModel.agent_id == agent_id)
    
    # Filter by time range
    query = query.filter(SessionModel.start_timestamp >= from_time)
    query = query.filter(
        or_(SessionModel.end_timestamp <= to_time, SessionModel.end_timestamp.is_(None))
    )
    
    # Get session count
    session_count = query.count()
    
    # Return as a data point
    return [
        MetricDataPoint(timestamp=datetime.utcnow(), value=session_count)
    ]

# Placeholder implementations for total calculation functions

def get_llm_request_total(db: Session, from_time: datetime, to_time: datetime, 
                        agent_id: Optional[str] = None) -> int:
    """Placeholder for total LLM request count"""
    # Placeholder implementation
    return 100

def get_llm_token_total(db: Session, from_time: datetime, to_time: datetime, 
                      agent_id: Optional[str] = None) -> int:
    """Placeholder for total LLM token usage"""
    # Placeholder implementation
    return 10000

def get_llm_avg_response_time(db: Session, from_time: datetime, to_time: datetime, 
                            agent_id: Optional[str] = None) -> float:
    """Placeholder for average LLM response time"""
    # Placeholder implementation
    return 1500.0

def get_tool_execution_total(db: Session, from_time: datetime, to_time: datetime, 
                           agent_id: Optional[str] = None) -> int:
    """Placeholder for total tool execution count"""
    # Placeholder implementation
    return 50

def get_error_total(db: Session, from_time: datetime, to_time: datetime, 
                  agent_id: Optional[str] = None) -> int:
    """Placeholder for total error count"""
    # Placeholder implementation
    return 5

def get_session_total(db: Session, from_time: datetime, to_time: datetime, 
                    agent_id: Optional[str] = None) -> int:
    """Placeholder for total session count"""
    # Placeholder implementation
    return 25 