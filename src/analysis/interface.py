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


@dataclass
class TimeRange:
    """
    Time range parameters for filtering events by time.
    
    Attributes:
        start: Start time (inclusive)
        end: End time (inclusive)
    """
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    
    @classmethod
    def last_hour(cls) -> 'TimeRange':
        """Create a time range for the last hour."""
        now = datetime.utcnow()
        return cls(start=now - timedelta(hours=1), end=now)
    
    @classmethod
    def last_day(cls) -> 'TimeRange':
        """Create a time range for the last 24 hours."""
        now = datetime.utcnow()
        return cls(start=now - timedelta(days=1), end=now)
    
    @classmethod
    def last_week(cls) -> 'TimeRange':
        """Create a time range for the last 7 days."""
        now = datetime.utcnow()
        return cls(start=now - timedelta(days=7), end=now)
    
    @classmethod
    def last_month(cls) -> 'TimeRange':
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
    time_range: Optional[TimeRange] = None
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
    
    def apply_time_filters(self, query, time_range: Optional[TimeRange], timestamp_column):
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