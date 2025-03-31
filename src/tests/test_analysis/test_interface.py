"""
Tests for analysis interface and core classes.
"""
import pytest
from datetime import datetime, timedelta

from analysis.interface import (
    AnalysisInterface, 
    BaseQueryParams, 
    MetricParams, 
    TimeSeriesParams, 
    TimeRange, 
    TimeResolution, 
    SortDirection, 
    QueryResult,
    Pagination
)
from models.event import Event


class TestAnalysisInterface:
    """Test the analysis interface class."""
    
    def test_apply_time_filters(self, db_session):
        """Test applying time filters to a query."""
        interface = AnalysisInterface(db_session)
        
        # Create a query
        query = db_session.query(Event)
        
        # Create a time range
        now = datetime.utcnow()
        time_range = TimeRange(
            start=now - timedelta(days=7),
            end=now
        )
        
        # Apply time filters
        filtered_query = interface.apply_time_filters(query, time_range, Event.timestamp)
        
        # Execute the query to verify it works
        assert filtered_query.count() >= 0
        
        # Test with only start time
        time_range = TimeRange(start=now - timedelta(days=7))
        filtered_query = interface.apply_time_filters(query, time_range, Event.timestamp)
        assert filtered_query.count() >= 0
        
        # Test with only end time
        time_range = TimeRange(end=now)
        filtered_query = interface.apply_time_filters(query, time_range, Event.timestamp)
        assert filtered_query.count() >= 0
    
    def test_apply_filters(self, db_session, mock_data):
        """Test applying common filters to a query."""
        interface = AnalysisInterface(db_session)
        
        # Create a query
        query = db_session.query(Event)
        
        # Count all events
        total_count = query.count()
        assert total_count > 0
        
        # Apply agent filter
        params = BaseQueryParams(agent_ids=["agent-0"])
        filtered_query = interface.apply_filters(query, params, Event)
        
        # Filtered count should be less than total
        filtered_count = filtered_query.count()
        assert 0 < filtered_count < total_count
        
        # Apply session filter
        params = BaseQueryParams(session_ids=["session-0"])
        filtered_query = interface.apply_filters(query, params, Event)
        
        # Filtered count should be less than total
        filtered_count = filtered_query.count()
        assert 0 < filtered_count < total_count
        
        # Apply trace filter
        params = BaseQueryParams(trace_ids=["trace-0"])
        filtered_query = interface.apply_filters(query, params, Event)
        
        # Filtered count should be less than total
        filtered_count = filtered_query.count()
        assert 0 < filtered_count < total_count
    
    def test_apply_pagination(self, db_session, mock_data):
        """Test applying pagination to a query."""
        interface = AnalysisInterface(db_session)
        
        # Create a query
        query = db_session.query(Event)
        
        # Count all events
        total_count = query.count()
        assert total_count > 0
        
        # Apply pagination for first page
        pagination = Pagination(page=1, page_size=5)
        paginated_query = interface.apply_pagination(query, pagination)
        
        # Should return just 5 events
        results = paginated_query.all()
        assert len(results) == 5
        
        # Apply pagination for second page
        pagination = Pagination(page=2, page_size=5)
        paginated_query = interface.apply_pagination(query, pagination)
        
        # Should return up to 5 events
        results = paginated_query.all()
        assert len(results) <= 5
        
        # Apply pagination with page size larger than total
        pagination = Pagination(page=1, page_size=total_count + 10)
        paginated_query = interface.apply_pagination(query, pagination)
        
        # Should return all events
        results = paginated_query.all()
        assert len(results) == total_count


class TestHelperClasses:
    """Test helper classes in the interface module."""
    
    def test_time_range(self):
        """Test TimeRange class."""
        # Test constructor
        now = datetime.utcnow()
        yesterday = now - timedelta(days=1)
        
        time_range = TimeRange(start=yesterday, end=now)
        assert time_range.start == yesterday
        assert time_range.end == now
        
        # Test factory methods
        last_hour = TimeRange.last_hour()
        assert (now - last_hour.start).total_seconds() <= 3600 + 10  # Allow small difference
        assert last_hour.end is not None
        
        last_day = TimeRange.last_day()
        assert (now - last_day.start).total_seconds() <= 86400 + 10  # Allow small difference
        assert last_day.end is not None
        
        last_week = TimeRange.last_week()
        assert (now - last_week.start).total_seconds() <= 7 * 86400 + 10  # Allow small difference
        assert last_week.end is not None
        
        last_month = TimeRange.last_month()
        assert (now - last_month.start).total_seconds() <= 30 * 86400 + 10  # Allow small difference
        assert last_month.end is not None
    
    def test_pagination_params(self):
        """Test PaginationParams class."""
        # Test default values
        pagination = Pagination()
        assert pagination.page == 1
        assert pagination.page_size == 50
        assert pagination.offset == 0
        assert pagination.limit == 50
        
        # Test custom values
        pagination = Pagination(page=3, page_size=20)
        assert pagination.page == 3
        assert pagination.page_size == 20
        assert pagination.offset == 40  # (3-1) * 20
        assert pagination.limit == 20
    
    def test_query_result(self):
        """Test QueryResult class."""
        # Create a query result
        items = [{"id": 1}, {"id": 2}, {"id": 3}]
        result = QueryResult(
            items=items,
            total=10,
            page=1,
            page_size=3
        )
        
        # Check properties
        assert result.items == items
        assert result.total == 10
        assert result.page == 1
        assert result.page_size == 3
        assert result.total_pages == 4  # Math.ceil(10/3)
        assert result.has_next is True
        assert result.has_prev is False
        
        # Test with different page
        result = QueryResult(
            items=items,
            total=10,
            page=3,
            page_size=3
        )
        
        assert result.has_next is True
        assert result.has_prev is True
        
        # Test edge case
        result = QueryResult(
            items=items,
            total=10,
            page=4,
            page_size=3
        )
        
        assert result.has_next is False
        assert result.has_prev is True 