"""
Tool usage metrics implementation.

This module provides metrics related to tool usage, such as tool frequency,
tool success rates, and tool usage patterns.
"""
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime
import json

from sqlalchemy import func, and_, or_, desc, text, case
from sqlalchemy.orm import Session, aliased

from src.models.event import Event
from src.models.tool_interaction import ToolInteraction
from src.analysis.interface import (
    AnalysisInterface, 
    TimeSeriesParams, 
    MetricParams,
    TimeRange,
    QueryResult
)
from src.analysis.utils import (
    format_time_series_data,
    sql_time_bucket,
    calculate_percentiles
)


class ToolMetrics(AnalysisInterface):
    """
    Tool usage metrics for tool interactions.
    
    This class provides methods for analyzing tool usage patterns,
    success rates, and performance.
    """
    
    def __init__(self, db_session, logger=None):
        """
        Initialize ToolMetrics with database session and logger.
        
        Args:
            db_session: Database session
            logger: Optional logger instance
        """
        super().__init__(db_session)
        self.logger = logger
    
    def get_tool_usage_summary(
        self, 
        params: MetricParams = None
    ) -> Dict[str, Any]:
        """
        Get a summary of tool usage.
        
        Args:
            params: Query parameters
            
        Returns:
            Dictionary with tool usage summary metrics
        """
        params = params or MetricParams()
        
        # Create query for tool usage
        query = self.db_session.query(
            func.count().label('total_tool_calls'),
            func.count(func.distinct(ToolInteraction.tool_name)).label('unique_tools'),
            func.sum(case((ToolInteraction.status == 'success', 1), else_=0)).label('successful_calls'),
            func.sum(case((ToolInteraction.status == 'error', 1), else_=0)).label('failed_calls'),
            func.count(func.distinct(Event.agent_id)).label('agents_using_tools')
        ).join(
            Event, ToolInteraction.event_id == Event.id
        )
        
        # Apply common filters
        query = self.apply_filters(query, params, Event)
        
        # Execute the query
        result = query.first()
        
        # Return zero values if no results
        if not result or not result.total_tool_calls:
            return {
                'total_tool_calls': 0,
                'unique_tools': 0,
                'successful_calls': 0,
                'failed_calls': 0,
                'success_rate': 0,
                'agents_using_tools': 0
            }
        
        # Calculate success rate
        success_rate = 0
        if result.total_tool_calls > 0:
            success_rate = round((result.successful_calls / result.total_tool_calls) * 100, 2)
        
        return {
            'total_tool_calls': result.total_tool_calls,
            'unique_tools': result.unique_tools,
            'successful_calls': result.successful_calls,
            'failed_calls': result.failed_calls,
            'success_rate': success_rate,
            'agents_using_tools': result.agents_using_tools
        }
    
    def get_tool_usage_by_name(
        self, 
        params: MetricParams = None
    ) -> QueryResult:
        """
        Get tool usage breakdown by tool name.
        
        Args:
            params: Query parameters
            
        Returns:
            QueryResult with tool usage by tool name
        """
        params = params or MetricParams()
        
        # Create query for tool usage by name
        query = self.db_session.query(
            ToolInteraction.tool_name,
            func.count().label('call_count'),
            func.sum(case((ToolInteraction.status == 'success', 1), else_=0)).label('successful_calls'),
            func.sum(case((ToolInteraction.status == 'error', 1), else_=0)).label('failed_calls'),
            func.count(func.distinct(Event.agent_id)).label('agent_count')
        ).join(
            Event, ToolInteraction.event_id == Event.id
        )
        
        # Apply common filters
        query = self.apply_filters(query, params, Event)
        
        # Group by tool name
        query = query.group_by(ToolInteraction.tool_name)
        
        # Apply sorting
        if params.sort:
            # Prepare field mapping for sorting
            field_mapping = {
                'tool_name': ToolInteraction.tool_name,
                'call_count': func.count(),
                'successful_calls': func.sum(case((ToolInteraction.status == 'success', 1), else_=0)),
                'failed_calls': func.sum(case((ToolInteraction.status == 'error', 1), else_=0)),
                'agent_count': func.count(func.distinct(Event.agent_id))
            }
            
            # Get the column to sort by
            if params.sort.field in field_mapping:
                column = field_mapping[params.sort.field]
                
                # Apply sort direction
                if params.sort.direction.value == 'desc':
                    query = query.order_by(desc(column))
                else:
                    query = query.order_by(column)
            else:
                # Default sort by call_count if invalid field
                query = query.order_by(desc(func.count()))
        else:
            # Default sort by call_count
            query = query.order_by(desc(func.count()))
        
        # Get total count before pagination
        count_query = self.db_session.query(
            func.count(func.distinct(ToolInteraction.tool_name))
        )
        count_query = self.apply_filters(count_query, params, Event)
        
        # Apply pagination
        query = self.apply_pagination(query, params.pagination)
        
        # Execute the query
        results = query.all()
        
        # Format the results
        items = []
        for result in results:
            # Calculate success rate
            success_rate = 0
            if result.call_count > 0:
                success_rate = round((result.successful_calls / result.call_count) * 100, 2)
            
            items.append({
                'tool_name': result.tool_name,
                'call_count': result.call_count,
                'successful_calls': result.successful_calls,
                'failed_calls': result.failed_calls,
                'success_rate': success_rate,
                'agent_count': result.agent_count
            })
        
        # Return paginated results
        return QueryResult(
            items=items,
            total=count_query.scalar() or 0,
            page=params.pagination.page,
            page_size=params.pagination.page_size
        )
    
    def get_tool_usage_by_agent(
        self, 
        params: MetricParams = None
    ) -> QueryResult:
        """
        Get tool usage breakdown by agent.
        
        Args:
            params: Query parameters
            
        Returns:
            QueryResult with tool usage by agent
        """
        params = params or MetricParams()
        
        # Create query for tool usage by agent
        query = self.db_session.query(
            Event.agent_id,
            func.count().label('call_count'),
            func.count(func.distinct(ToolInteraction.tool_name)).label('unique_tools'),
            func.sum(case((ToolInteraction.status == 'success', 1), else_=0)).label('successful_calls'),
            func.sum(case((ToolInteraction.status == 'error', 1), else_=0)).label('failed_calls')
        ).join(
            ToolInteraction, Event.id == ToolInteraction.event_id
        )
        
        # Apply common filters
        query = self.apply_filters(query, params, Event)
        
        # Group by agent ID
        query = query.group_by(Event.agent_id)
        
        # Apply sorting
        if params.sort:
            # Prepare field mapping for sorting
            field_mapping = {
                'agent_id': Event.agent_id,
                'call_count': func.count(),
                'unique_tools': func.count(func.distinct(ToolInteraction.tool_name)),
                'successful_calls': func.sum(case((ToolInteraction.status == 'success', 1), else_=0)),
                'failed_calls': func.sum(case((ToolInteraction.status == 'error', 1), else_=0))
            }
            
            # Get the column to sort by
            if params.sort.field in field_mapping:
                column = field_mapping[params.sort.field]
                
                # Apply sort direction
                if params.sort.direction.value == 'desc':
                    query = query.order_by(desc(column))
                else:
                    query = query.order_by(column)
            else:
                # Default sort by call_count if invalid field
                query = query.order_by(desc(func.count()))
        else:
            # Default sort by call_count
            query = query.order_by(desc(func.count()))
        
        # Get total count before pagination
        count_query = self.db_session.query(
            func.count(func.distinct(Event.agent_id))
        ).join(
            ToolInteraction, Event.id == ToolInteraction.event_id
        )
        count_query = self.apply_filters(count_query, params, Event)
        
        # Apply pagination
        query = self.apply_pagination(query, params.pagination)
        
        # Execute the query
        results = query.all()
        
        # Format the results
        items = []
        for result in results:
            # Calculate success rate
            success_rate = 0
            if result.call_count > 0:
                success_rate = round((result.successful_calls / result.call_count) * 100, 2)
            
            items.append({
                'agent_id': result.agent_id,
                'call_count': result.call_count,
                'unique_tools': result.unique_tools,
                'successful_calls': result.successful_calls,
                'failed_calls': result.failed_calls,
                'success_rate': success_rate
            })
        
        # Return paginated results
        return QueryResult(
            items=items,
            total=count_query.scalar() or 0,
            page=params.pagination.page,
            page_size=params.pagination.page_size
        )
    
    def get_tool_usage_time_series(
        self, 
        params: TimeSeriesParams = None
    ) -> List[Dict[str, Any]]:
        """
        Get tool usage over time as a time series.
        
        Args:
            params: Query parameters
            
        Returns:
            List of time series data points
        """
        params = params or TimeSeriesParams()
        
        # Determine time range
        time_range = params.time_range or TimeRange.last_day()
        
        # Create query for tool usage time series
        query = self.db_session.query(
            sql_time_bucket(Event.timestamp, params.resolution).label('time_bucket'),
            func.count().label('call_count'),
            func.sum(case((ToolInteraction.status == 'success', 1), else_=0)).label('successful_calls'),
            func.sum(case((ToolInteraction.status == 'error', 1), else_=0)).label('failed_calls')
        ).join(
            Event, ToolInteraction.event_id == Event.id
        )
        
        # Apply time range filter
        query = self.apply_time_filters(query, time_range, Event.timestamp)
        
        # Filter by agent IDs
        if params.agent_ids:
            query = query.filter(Event.agent_id.in_(params.agent_ids))
        
        # Filter by session IDs
        if params.session_ids:
            query = query.filter(Event.session_id.in_(params.session_ids))
        
        # Filter by trace IDs
        if params.trace_ids:
            query = query.filter(Event.trace_id.in_(params.trace_ids))
        
        # Group by time bucket
        query = query.group_by('time_bucket')
        
        # Order by time bucket
        query = query.order_by('time_bucket')
        
        # Execute the query
        results = query.all()
        
        # Define fields for time series formatting
        fields = [
            ('call_count', 'sum'),
            ('successful_calls', 'sum'),
            ('failed_calls', 'sum')
        ]
        
        # Format time series data
        time_series_data = format_time_series_data(
            results,
            'time_bucket',
            fields,
            time_range,
            params.resolution
        )
        
        # Calculate success rate for each data point
        for point in time_series_data:
            if point['call_count'] > 0:
                point['success_rate'] = round((point['successful_calls'] / point['call_count']) * 100, 2)
            else:
                point['success_rate'] = 0
        
        return time_series_data
    
    def get_tool_performance_metrics(
        self, 
        params: MetricParams = None
    ) -> Dict[str, Any]:
        """
        Get tool performance metrics, focusing on execution time.
        
        Args:
            params: Query parameters
            
        Returns:
            Dictionary with tool performance metrics
        """
        params = params or MetricParams()
        
        # Create query for tool duration metrics
        # We can only get duration for tool executions that have both start and finish
        query = self.db_session.query(
            ToolInteraction.tool_name,
            func.avg(ToolInteraction.duration_ms).label('avg_duration_ms'),
            func.min(ToolInteraction.duration_ms).label('min_duration_ms'),
            func.max(ToolInteraction.duration_ms).label('max_duration_ms'),
            func.count().label('call_count')
        ).join(
            Event, ToolInteraction.event_id == Event.id
        ).filter(
            ToolInteraction.duration_ms.isnot(None)
        )
        
        # Apply common filters
        query = self.apply_filters(query, params, Event)
        
        # Group by tool name
        query = query.group_by(ToolInteraction.tool_name)
        
        # Apply sorting by average duration
        query = query.order_by(desc(func.avg(ToolInteraction.duration_ms)))
        
        # Execute the query
        results = query.all()
        
        # Format the results
        performance_metrics = []
        for result in results:
            performance_metrics.append({
                'tool_name': result.tool_name,
                'avg_duration_ms': round(result.avg_duration_ms, 2) if result.avg_duration_ms else 0,
                'min_duration_ms': result.min_duration_ms or 0,
                'max_duration_ms': result.max_duration_ms or 0,
                'call_count': result.call_count
            })
        
        # Also get an overall average
        overall_query = self.db_session.query(
            func.avg(ToolInteraction.duration_ms).label('avg_duration_ms'),
            func.min(ToolInteraction.duration_ms).label('min_duration_ms'),
            func.max(ToolInteraction.duration_ms).label('max_duration_ms'),
            func.count().label('call_count')
        ).join(
            Event, ToolInteraction.event_id == Event.id
        ).filter(
            ToolInteraction.duration_ms.isnot(None)
        )
        
        # Apply common filters
        overall_query = self.apply_filters(overall_query, params, Event)
        
        # Execute the query
        overall_result = overall_query.first()
        
        # Create overall metrics
        overall_metrics = {
            'avg_duration_ms': round(overall_result.avg_duration_ms, 2) if overall_result and overall_result.avg_duration_ms else 0,
            'min_duration_ms': overall_result.min_duration_ms if overall_result else 0,
            'max_duration_ms': overall_result.max_duration_ms if overall_result else 0,
            'call_count': overall_result.call_count if overall_result else 0
        }
        
        return {
            'overall': overall_metrics,
            'by_tool': performance_metrics
        }
    
    def get_error_analysis(
        self, 
        params: MetricParams = None
    ) -> Dict[str, Any]:
        """
        Analyze tool errors to identify patterns.
        
        Args:
            params: Query parameters
            
        Returns:
            Dictionary with error analysis results
        """
        params = params or MetricParams()
        
        # Create query for error analysis
        query = self.db_session.query(
            ToolInteraction.tool_name,
            ToolInteraction.status,
            func.count().label('count')
        ).join(
            Event, ToolInteraction.event_id == Event.id
        ).filter(
            ToolInteraction.status == 'error'
        )
        
        # Apply common filters
        query = self.apply_filters(query, params, Event)
        
        # Group by tool name and status
        query = query.group_by(ToolInteraction.tool_name, ToolInteraction.status)
        
        # Sort by count descending
        query = query.order_by(desc(func.count()))
        
        # Execute the query
        results = query.all()
        
        # Group errors by tool
        error_by_tool = {}
        for result in results:
            if result.tool_name not in error_by_tool:
                error_by_tool[result.tool_name] = {
                    'error_count': 0,
                    'percentage': 0
                }
            
            error_by_tool[result.tool_name]['error_count'] = result.count
        
        # Get total calls for each tool to calculate percentages
        total_calls_query = self.db_session.query(
            ToolInteraction.tool_name,
            func.count().label('total_count')
        ).join(
            Event, ToolInteraction.event_id == Event.id
        )
        
        # Apply common filters
        total_calls_query = self.apply_filters(total_calls_query, params, Event)
        
        # Group by tool name
        total_calls_query = total_calls_query.group_by(ToolInteraction.tool_name)
        
        # Execute the query
        total_calls_results = total_calls_query.all()
        
        # Calculate percentages
        for result in total_calls_results:
            if result.tool_name in error_by_tool:
                error_count = error_by_tool[result.tool_name]['error_count']
                total_count = result.total_count
                
                if total_count > 0:
                    percentage = round((error_count / total_count) * 100, 2)
                    error_by_tool[result.tool_name]['percentage'] = percentage
                    error_by_tool[result.tool_name]['total_count'] = total_count
                else:
                    error_by_tool[result.tool_name]['percentage'] = 0
                    error_by_tool[result.tool_name]['total_count'] = 0
        
        # Sort by error count
        sorted_errors = sorted(
            [
                {
                    'tool_name': tool_name,
                    'error_count': data['error_count'],
                    'total_count': data.get('total_count', 0),
                    'error_percentage': data['percentage']
                }
                for tool_name, data in error_by_tool.items()
            ],
            key=lambda x: x['error_count'],
            reverse=True
        )
        
        return {
            'error_count': sum(result.count for result in results),
            'by_tool': sorted_errors
        }
    
    def get_tool_interactions_detailed(
        self,
        from_time: Optional[datetime] = None,
        to_time: Optional[datetime] = None,
        agent_id: Optional[str] = None,
        tool_name: Optional[str] = None,
        status: Optional[str] = None,
        framework_name: Optional[str] = None,
        interaction_type: Optional[str] = None,
        sort_by: Optional[str] = "request_timestamp",
        sort_dir: Optional[str] = "desc",
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """
        Get detailed tool interaction data with pagination support.
        
        Args:
            from_time: Start time for the query range
            to_time: End time for the query range
            agent_id: Optional filter by agent ID
            tool_name: Optional filter by tool name
            status: Optional filter by status (success, error, pending)
            framework_name: Optional filter by framework name
            interaction_type: Optional filter by interaction type (execution, result)
            sort_by: Field to sort by (default: "request_timestamp")
            sort_dir: Sort direction ("asc" or "desc", default: "desc")
            page: Page number (default: 1)
            page_size: Page size (default: 20)
            
        Returns:
            Dictionary with pagination details and list of tool interactions
        """
        # Create base query for tool interactions with all relevant fields
        query = self.db_session.query(
            ToolInteraction,
            Event.span_id,
            Event.trace_id,
            Event.agent_id
        ).join(
            Event, ToolInteraction.event_id == Event.id
        )
        
        # Apply time range filters
        if from_time:
            query = query.filter(Event.timestamp >= from_time)
        if to_time:
            query = query.filter(Event.timestamp <= to_time)
        
        # Apply agent filter if provided
        if agent_id:
            query = query.filter(Event.agent_id == agent_id)
            
        # Apply additional specific filters
        if tool_name:
            query = query.filter(ToolInteraction.tool_name == tool_name)
        
        if status:
            query = query.filter(ToolInteraction.status == status)
            
        if framework_name:
            query = query.filter(ToolInteraction.framework_name == framework_name)
            
        if interaction_type:
            query = query.filter(ToolInteraction.interaction_type == interaction_type)
        
        # Get total count before pagination and sorting
        count_query = query.statement.with_only_columns(func.count()).order_by(None)
        total_count = self.db_session.execute(count_query).scalar() or 0
        
        # Apply sorting with direct parameters
        # Define valid sort fields
        field_mapping = {
            'id': ToolInteraction.id,
            'tool_name': ToolInteraction.tool_name,
            'status': ToolInteraction.status,
            'request_timestamp': ToolInteraction.request_timestamp,
            'response_timestamp': ToolInteraction.response_timestamp,
            'duration_ms': ToolInteraction.duration_ms
        }
        
        # Get the column to sort by
        if sort_by in field_mapping:
            column = field_mapping[sort_by]
            
            # Apply sort direction
            if sort_dir == "desc":
                query = query.order_by(desc(column))
            else:
                query = query.order_by(column)
        else:
            # Default sort by timestamp desc if invalid field
            query = query.order_by(desc(ToolInteraction.request_timestamp))
        
        # Apply pagination directly
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        
        # Execute the query
        results = query.all()
        
        # Format the results
        interactions = []
        for tool_interaction, span_id, trace_id, agent_id in results:
            # Parse JSON fields
            try:
                parameters = json.loads(tool_interaction.parameters) if tool_interaction.parameters else None
            except (json.JSONDecodeError, TypeError):
                parameters = tool_interaction.parameters
                
            try:
                result = json.loads(tool_interaction.result) if tool_interaction.result else None
            except (json.JSONDecodeError, TypeError):
                result = tool_interaction.result
            
            # Find all associated event IDs that share the same span_id
            associated_event_ids = []
            if span_id:
                # Query all events with the same span_id to get their IDs
                event_ids_query = self.db_session.query(Event.id).filter(
                    Event.span_id == span_id
                ).all()
                associated_event_ids = [event_id[0] for event_id in event_ids_query]
            
            # Create interaction data
            interaction_data = {
                'id': tool_interaction.id,
                'associated_event_ids': associated_event_ids,
                'tool_name': tool_interaction.tool_name or "unknown",
                'interaction_type': tool_interaction.interaction_type or "unknown",
                'status': tool_interaction.status or "unknown",
                'status_code': tool_interaction.status_code,
                'parameters': parameters,
                'result': result,
                'error': tool_interaction.error,
                'request_timestamp': tool_interaction.request_timestamp,
                'response_timestamp': tool_interaction.response_timestamp,
                'duration_ms': tool_interaction.duration_ms,
                'framework_name': tool_interaction.framework_name,
                'tool_version': tool_interaction.tool_version,
                'authorization_level': tool_interaction.authorization_level,
                'execution_time_ms': tool_interaction.execution_time_ms,
                'cache_hit': tool_interaction.cache_hit,
                'api_version': tool_interaction.api_version,
                'raw_attributes': tool_interaction.raw_attributes,
                'span_id': span_id,
                'trace_id': trace_id,
                'agent_id': agent_id
            }
            
            interactions.append(interaction_data)
        
        # Return the detailed response
        return {
            'total': total_count,
            'page': page,
            'page_size': page_size,
            'from_time': from_time,
            'to_time': to_time,
            'interactions': interactions
        } 