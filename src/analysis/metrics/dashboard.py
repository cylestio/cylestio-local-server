"""
Dashboard metrics implementation.

This module provides high-level, aggregated metrics suitable for
dashboard displays and summary statistics.
"""
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime, timedelta
import json

from sqlalchemy import func, and_, or_, desc, text, case
from sqlalchemy.orm import Session, aliased

from src.models.event import Event
from src.models.llm_interaction import LLMInteraction
from src.models.tool_interaction import ToolInteraction
from src.models.security_alert import SecurityAlert
from src.models.agent import Agent
from src.models.session import Session as SessionModel
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
    calculate_token_cost
)


class DashboardMetrics(AnalysisInterface):
    """
    Dashboard metrics providing an overview of system activity.
    
    This class provides high-level metrics for the dashboard, summarizing
    key information about agents, tokens, tools, and security.
    """
    
    def get_summary_metrics(self, params: MetricParams = None) -> Dict[str, Any]:
        """
        Get a summary of all key metrics for the dashboard.
        
        Args:
            params: Query parameters
            
        Returns:
            Dictionary with summary metrics
        """
        params = params or MetricParams()
        
        # Create summary dictionary
        summary = {
            'agents': {
                'total': 0,
                'active_last_24h': 0,
                'active_last_7d': 0
            },
            'sessions': {
                'total': 0,
                'active': 0,
                'average_duration_ms': 0
            },
            'llm': {
                'total_calls': 0,
                'total_tokens': 0,
                'estimated_cost': 0,
                'unique_models': 0
            },
            'tools': {
                'total_calls': 0,
                'unique_tools': 0,
                'success_rate': 0
            },
            'security': {
                'total_alerts': 0,
                'high_severity': 0,
                'last_24h': 0
            }
        }
        
        # Get agent metrics
        agent_query = self.db_session.query(
            func.count(Agent.agent_id).label('total_agents'),
            func.count(
                func.case([(Agent.last_seen_timestamp >= datetime.utcnow() - timedelta(days=1), 1)])
            ).label('active_last_24h'),
            func.count(
                func.case([(Agent.last_seen_timestamp >= datetime.utcnow() - timedelta(days=7), 1)])
            ).label('active_last_7d')
        )
        
        # Apply agent filter if specified
        if params.agent_ids:
            agent_query = agent_query.filter(Agent.agent_id.in_(params.agent_ids))
        
        # Execute agent query
        agent_result = agent_query.first()
        if agent_result:
            summary['agents']['total'] = agent_result.total_agents
            summary['agents']['active_last_24h'] = agent_result.active_last_24h
            summary['agents']['active_last_7d'] = agent_result.active_last_7d
        
        # Get session metrics
        session_query = self.db_session.query(
            func.count(SessionModel.session_id).label('total_sessions'),
            func.count(
                func.case([(SessionModel.end_timestamp.is_(None), 1)])
            ).label('active_sessions'),
            func.avg(
                func.case([
                    (
                        SessionModel.end_timestamp.isnot(None),
                        func.extract('epoch', SessionModel.end_timestamp - SessionModel.start_timestamp) * 1000
                    )
                ])
            ).label('average_duration_ms')
        )
        
        # Apply agent filter if specified
        if params.agent_ids:
            session_query = session_query.filter(SessionModel.agent_id.in_(params.agent_ids))
        
        # Apply time range filter if specified
        if params.time_range and params.time_range.start:
            session_query = session_query.filter(SessionModel.start_timestamp >= params.time_range.start)
        if params.time_range and params.time_range.end:
            session_query = session_query.filter(
                or_(
                    SessionModel.end_timestamp <= params.time_range.end,
                    SessionModel.end_timestamp.is_(None)
                )
            )
        
        # Execute session query
        session_result = session_query.first()
        if session_result:
            summary['sessions']['total'] = session_result.total_sessions
            summary['sessions']['active'] = session_result.active_sessions
            summary['sessions']['average_duration_ms'] = round(session_result.average_duration_ms or 0, 2)
        
        # Get LLM metrics
        llm_query = self.db_session.query(
            func.count().label('total_calls'),
            func.sum(LLMInteraction.total_tokens).label('total_tokens'),
            func.count(func.distinct(LLMInteraction.model)).label('unique_models')
        ).join(
            Event, LLMInteraction.event_id == Event.id
        ).filter(
            LLMInteraction.interaction_type == 'finish'  # Count only completed calls
        )
        
        # Apply common filters
        llm_query = self.apply_filters(llm_query, params, Event)
        
        # Execute LLM query
        llm_result = llm_query.first()
        if llm_result:
            summary['llm']['total_calls'] = llm_result.total_calls
            summary['llm']['total_tokens'] = llm_result.total_tokens or 0
            summary['llm']['unique_models'] = llm_result.unique_models
        
        # Calculate LLM cost
        if llm_result and llm_result.total_tokens > 0:
            # Get token usage by model for accurate cost calculation
            model_usage_query = self.db_session.query(
                LLMInteraction.model,
                func.sum(LLMInteraction.input_tokens).label('input_tokens'),
                func.sum(LLMInteraction.output_tokens).label('output_tokens')
            ).join(
                Event, LLMInteraction.event_id == Event.id
            ).filter(
                LLMInteraction.interaction_type == 'finish'
            )
            
            # Apply common filters
            model_usage_query = self.apply_filters(model_usage_query, params, Event)
            
            # Group by model
            model_usage_query = model_usage_query.group_by(LLMInteraction.model)
            
            # Execute the query
            model_usage = model_usage_query.all()
            
            # Calculate cost
            total_cost = 0.0
            for usage in model_usage:
                if usage.input_tokens and usage.output_tokens:
                    total_cost += calculate_token_cost(
                        usage.input_tokens,
                        usage.output_tokens,
                        usage.model
                    )
            
            summary['llm']['estimated_cost'] = round(total_cost, 2)
        
        # Get tool metrics
        tool_query = self.db_session.query(
            func.count().label('total_calls'),
            func.count(func.distinct(ToolInteraction.tool_name)).label('unique_tools'),
            func.sum(case((ToolInteraction.status == 'success', 1), else_=0)).label('successful_calls')
        ).join(
            Event, ToolInteraction.event_id == Event.id
        )
        
        # Apply common filters
        tool_query = self.apply_filters(tool_query, params, Event)
        
        # Execute tool query
        tool_result = tool_query.first()
        if tool_result:
            summary['tools']['total_calls'] = tool_result.total_calls
            summary['tools']['unique_tools'] = tool_result.unique_tools
            
            # Calculate success rate
            if tool_result.total_calls > 0:
                success_rate = (tool_result.successful_calls / tool_result.total_calls) * 100
                summary['tools']['success_rate'] = round(success_rate, 2)
        
        # Get security metrics
        security_query = self.db_session.query(
            func.count().label('total_alerts'),
            func.count(
                func.case([(SecurityAlert.alert_level == 'high', 1)])
            ).label('high_severity'),
            func.count(
                func.case([(Event.timestamp >= datetime.utcnow() - timedelta(days=1), 1)])
            ).label('last_24h')
        ).join(
            Event, SecurityAlert.event_id == Event.id
        )
        
        # Apply common filters
        security_query = self.apply_filters(security_query, params, Event)
        
        # Execute security query
        security_result = security_query.first()
        if security_result:
            summary['security']['total_alerts'] = security_result.total_alerts
            summary['security']['high_severity'] = security_result.high_severity
            summary['security']['last_24h'] = security_result.last_24h
        
        return summary
    
    def get_activity_timeline(self, params: TimeSeriesParams = None) -> List[Dict[str, Any]]:
        """
        Get system activity over time as a time series.
        
        Args:
            params: Time series parameters
            
        Returns:
            List of time series data points
        """
        params = params or TimeSeriesParams()
        
        # Get time bucket SQL expression
        time_bucket_expr = sql_time_bucket(params.resolution.value)
        time_bucket = text(time_bucket_expr)
        
        # Create query for activity time series
        # We'll count events by type in each time bucket
        query = self.db_session.query(
            time_bucket.label('time_bucket'),
            Event.event_type,
            func.count().label('count')
        )
        
        # Apply common filters
        if params.time_range:
            query = self.apply_time_filters(query, params.time_range, Event.timestamp)
        
        if params.agent_ids:
            query = query.filter(Event.agent_id.in_(params.agent_ids))
        
        if params.session_ids:
            query = query.filter(Event.session_id.in_(params.session_ids))
        
        if params.trace_ids:
            query = query.filter(Event.trace_id.in_(params.trace_ids))
        
        # Group by time bucket and event type
        query = query.group_by('time_bucket', Event.event_type)
        
        # Order by time bucket
        query = query.order_by('time_bucket')
        
        # Execute the query
        results = query.all()
        
        # Format the results as time series data
        time_series_by_bucket = {}
        for result in results:
            bucket = result.time_bucket
            event_type = result.event_type
            count = result.count
            
            if bucket not in time_series_by_bucket:
                # Initialize new bucket
                time_series_by_bucket[bucket] = {
                    'llm': 0,
                    'tool': 0,
                    'security': 0,
                    'monitoring': 0,
                    'other': 0,
                    'total': 0
                }
            
            # Update counts
            time_series_by_bucket[bucket][event_type] = count
            time_series_by_bucket[bucket]['total'] += count
        
        # Convert to list and format timestamps
        time_series = []
        for bucket, counts in sorted(time_series_by_bucket.items()):
            # Parse the bucket timestamp
            if params.resolution.value == 'minute':
                dt = datetime.strptime(bucket, '%Y-%m-%d %H:%M')
            elif params.resolution.value == 'hour':
                dt = datetime.strptime(bucket, '%Y-%m-%d %H')
            elif params.resolution.value == 'day':
                dt = datetime.strptime(bucket, '%Y-%m-%d')
            elif params.resolution.value == 'week':
                dt = datetime.strptime(bucket, '%Y-%m-%d')
            elif params.resolution.value == 'month':
                dt = datetime.strptime(bucket, '%Y-%m')
            else:
                # Fallback
                dt = datetime.now()
            
            time_series.append({
                'timestamp': dt.isoformat(),
                'llm_count': counts['llm'],
                'tool_count': counts['tool'],
                'security_count': counts['security'],
                'monitoring_count': counts['monitoring'],
                'other_count': counts['other'],
                'total_count': counts['total']
            })
        
        return time_series
    
    def get_recent_sessions(self, params: MetricParams = None) -> QueryResult:
        """
        Get a list of recent sessions.
        
        Args:
            params: Query parameters
            
        Returns:
            QueryResult with recent sessions
        """
        params = params or MetricParams()
        
        # Create query for recent sessions
        query = self.db_session.query(
            SessionModel.session_id,
            SessionModel.agent_id,
            SessionModel.start_timestamp,
            SessionModel.end_timestamp,
            func.count(Event.id).label('event_count'),
            func.count(
                func.case([(Event.event_type == 'llm', 1)])
            ).label('llm_event_count'),
            func.count(
                func.case([(Event.event_type == 'tool', 1)])
            ).label('tool_event_count'),
            func.count(
                func.case([(Event.event_type == 'security', 1)])
            ).label('security_event_count')
        ).join(
            Event, SessionModel.session_id == Event.session_id, isouter=True
        )
        
        # Apply agent filter if specified
        if params.agent_ids:
            query = query.filter(SessionModel.agent_id.in_(params.agent_ids))
        
        # Apply time range filter if specified
        if params.time_range and params.time_range.start:
            query = query.filter(SessionModel.start_timestamp >= params.time_range.start)
        if params.time_range and params.time_range.end:
            query = query.filter(
                or_(
                    SessionModel.end_timestamp <= params.time_range.end,
                    SessionModel.end_timestamp.is_(None)
                )
            )
        
        # Group by session
        query = query.group_by(
            SessionModel.session_id,
            SessionModel.agent_id,
            SessionModel.start_timestamp,
            SessionModel.end_timestamp
        )
        
        # Apply sorting
        if params.sort:
            # Prepare field mapping for sorting
            field_mapping = {
                'start_timestamp': SessionModel.start_timestamp,
                'end_timestamp': SessionModel.end_timestamp,
                'event_count': func.count(Event.id)
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
                # Default sort by start_timestamp if invalid field
                query = query.order_by(desc(SessionModel.start_timestamp))
        else:
            # Default sort by start_timestamp
            query = query.order_by(desc(SessionModel.start_timestamp))
        
        # Get total count before pagination
        count_query = self.db_session.query(func.count(func.distinct(SessionModel.session_id)))
        
        # Apply same filters as main query for count
        if params.agent_ids:
            count_query = count_query.filter(SessionModel.agent_id.in_(params.agent_ids))
        
        if params.time_range and params.time_range.start:
            count_query = count_query.filter(SessionModel.start_timestamp >= params.time_range.start)
        if params.time_range and params.time_range.end:
            count_query = count_query.filter(
                or_(
                    SessionModel.end_timestamp <= params.time_range.end,
                    SessionModel.end_timestamp.is_(None)
                )
            )
        
        # Apply pagination
        query = self.apply_pagination(query, params.pagination)
        
        # Execute the query
        results = query.all()
        
        # Format the results
        items = []
        for result in results:
            # Calculate duration if session has ended
            duration_ms = None
            if result.end_timestamp and result.start_timestamp:
                duration_delta = result.end_timestamp - result.start_timestamp
                duration_ms = duration_delta.total_seconds() * 1000
            
            items.append({
                'session_id': result.session_id,
                'agent_id': result.agent_id,
                'start_timestamp': result.start_timestamp.isoformat() if result.start_timestamp else None,
                'end_timestamp': result.end_timestamp.isoformat() if result.end_timestamp else None,
                'duration_ms': round(duration_ms, 2) if duration_ms else None,
                'status': 'active' if result.end_timestamp is None else 'completed',
                'event_count': result.event_count,
                'llm_event_count': result.llm_event_count,
                'tool_event_count': result.tool_event_count,
                'security_event_count': result.security_event_count
            })
        
        # Return paginated results
        return QueryResult(
            items=items,
            total=count_query.scalar() or 0,
            page=params.pagination.page,
            page_size=params.pagination.page_size
        )
    
    def get_agent_performance(self, params: MetricParams = None) -> QueryResult:
        """
        Get performance metrics for agents.
        
        Args:
            params: Query parameters
            
        Returns:
            QueryResult with agent performance metrics
        """
        params = params or MetricParams()
        
        # Create query for agent performance
        query = self.db_session.query(
            Event.agent_id,
            func.count(
                func.case([(Event.event_type == 'llm', 1)])
            ).label('llm_call_count'),
            func.avg(
                func.case([
                    (
                        and_(
                            Event.event_type == 'llm',
                            LLMInteraction.interaction_type == 'finish'
                        ),
                        LLMInteraction.duration_ms
                    )
                ])
            ).label('avg_llm_duration_ms'),
            func.count(
                func.case([(Event.event_type == 'tool', 1)])
            ).label('tool_call_count'),
            func.avg(
                func.case([
                    (
                        Event.event_type == 'tool',
                        ToolInteraction.duration_ms
                    )
                ])
            ).label('avg_tool_duration_ms'),
            func.count(
                func.case([(Event.event_type == 'security', 1)])
            ).label('security_alert_count')
        ).outerjoin(
            LLMInteraction, and_(
                Event.id == LLMInteraction.event_id,
                Event.event_type == 'llm'
            )
        ).outerjoin(
            ToolInteraction, and_(
                Event.id == ToolInteraction.event_id,
                Event.event_type == 'tool'
            )
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
                'llm_call_count': func.count(func.case([(Event.event_type == 'llm', 1)])),
                'avg_llm_duration_ms': func.avg(func.case([(and_(Event.event_type == 'llm', LLMInteraction.interaction_type == 'finish'), LLMInteraction.duration_ms)])),
                'tool_call_count': func.count(func.case([(Event.event_type == 'tool', 1)])),
                'avg_tool_duration_ms': func.avg(func.case([(Event.event_type == 'tool', ToolInteraction.duration_ms)])),
                'security_alert_count': func.count(func.case([(Event.event_type == 'security', 1)]))
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
                # Default sort by llm_call_count if invalid field
                query = query.order_by(desc(func.count(func.case([(Event.event_type == 'llm', 1)]))))
        else:
            # Default sort by llm_call_count
            query = query.order_by(desc(func.count(func.case([(Event.event_type == 'llm', 1)]))))
        
        # Get total count before pagination
        count_query = self.db_session.query(func.count(func.distinct(Event.agent_id)))
        count_query = self.apply_filters(count_query, params, Event)
        
        # Apply pagination
        query = self.apply_pagination(query, params.pagination)
        
        # Execute the query
        results = query.all()
        
        # Format the results
        items = []
        for result in results:
            # Calculate total events
            total_events = (
                result.llm_call_count +
                result.tool_call_count +
                result.security_alert_count
            )
            
            items.append({
                'agent_id': result.agent_id,
                'llm_call_count': result.llm_call_count,
                'avg_llm_duration_ms': round(result.avg_llm_duration_ms, 2) if result.avg_llm_duration_ms else None,
                'tool_call_count': result.tool_call_count,
                'avg_tool_duration_ms': round(result.avg_tool_duration_ms, 2) if result.avg_tool_duration_ms else None,
                'security_alert_count': result.security_alert_count,
                'total_events': total_events
            })
        
        # Return paginated results
        return QueryResult(
            items=items,
            total=count_query.scalar() or 0,
            page=params.pagination.page,
            page_size=params.pagination.page_size
        ) 