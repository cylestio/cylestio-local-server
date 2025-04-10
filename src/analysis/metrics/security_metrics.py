"""
Security metrics implementation.

This module provides metrics related to security alerts and issues
detected during AI agent operations.
"""
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime
import json

from sqlalchemy import func, and_, or_, desc, text, case, cast, String, JSON
from sqlalchemy.orm import Session, aliased
from sqlalchemy.sql import label

from src.models.event import Event
from src.models.security_alert import SecurityAlert
from src.models.llm_interaction import LLMInteraction
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
    deep_get,
    parse_json_string
)


class SecurityMetrics(AnalysisInterface):
    """
    Security metrics for security alerts and vulnerabilities.
    
    This class provides methods for analyzing security alerts, trends,
    and potential vulnerabilities in the telemetry data.
    """
    
    def get_security_alerts_summary(
        self, 
        params: MetricParams = None
    ) -> Dict[str, Any]:
        """
        Get a summary of security alerts.
        
        Args:
            params: Query parameters
            
        Returns:
            Dictionary with security alert metrics
        """
        params = params or MetricParams()
        
        # Create query for security alerts
        query = self.db_session.query(
            func.count().label('total_alerts'),
            func.count(func.distinct(Event.agent_id)).label('agents_with_alerts'),
            func.count(func.distinct(SecurityAlert.category)).label('unique_alert_types')
        ).join(
            Event, SecurityAlert.event_id == Event.id
        )
        
        # Apply common filters
        query = self.apply_filters(query, params, Event)
        
        # Execute the query
        result = query.first()
        
        # Get severity level counts
        level_query = self.db_session.query(
            SecurityAlert.severity,
            func.count().label('count')
        ).join(
            Event, SecurityAlert.event_id == Event.id
        )
        
        # Apply common filters
        level_query = self.apply_filters(level_query, params, Event)
        
        # Group by severity level
        level_query = level_query.group_by(SecurityAlert.severity)
        
        # Execute the query
        level_results = level_query.all()
        
        # Create level counts dictionary
        level_counts = {}
        for level_result in level_results:
            level_counts[level_result.severity] = level_result.count
        
        # Get keyword counts from raw_attributes JSON field
        keyword_query = self.db_session.query(
            cast(SecurityAlert.raw_attributes['keywords'], JSON).label('keywords'),
            func.count().label('count')
        ).join(
            Event, SecurityAlert.event_id == Event.id
        )
        
        # Apply common filters
        keyword_query = self.apply_filters(keyword_query, params, Event)
        
        # Filter out null keywords
        keyword_query = keyword_query.filter(SecurityAlert.raw_attributes.isnot(None))
        
        # Group by keywords
        keyword_query = keyword_query.group_by('keywords')
        
        # Sort by count descending
        keyword_query = keyword_query.order_by(desc(func.count()))
        
        # Execute the query
        keyword_results = keyword_query.all()
        
        # Process keywords (they might be stored as JSON strings)
        top_keywords = []
        for keyword_result in keyword_results:
            if keyword_result.keywords is None:
                continue
                
            keywords = keyword_result.keywords
            if isinstance(keywords, str):
                keywords = parse_json_string(keywords, [])
            
            if isinstance(keywords, list):
                for keyword in keywords:
                    top_keywords.append({
                        'keyword': keyword,
                        'count': keyword_result.count
                    })
        
        # Aggregate by keyword
        keyword_counts = {}
        for keyword_info in top_keywords:
            keyword = keyword_info['keyword']
            count = keyword_info['count']
            
            if keyword in keyword_counts:
                keyword_counts[keyword] += count
            else:
                keyword_counts[keyword] = count
        
        # Sort keywords by count
        sorted_keywords = sorted(
            [{'keyword': k, 'count': v} for k, v in keyword_counts.items()],
            key=lambda x: x['count'],
            reverse=True
        )
        
        return {
            'total_alerts': result.total_alerts if result else 0,
            'agents_with_alerts': result.agents_with_alerts if result else 0,
            'unique_alert_types': result.unique_alert_types if result else 0,
            'by_level': level_counts,
            'top_keywords': sorted_keywords[:10]  # Top 10 keywords
        }
    
    def get_security_alerts_by_agent(
        self, 
        params: MetricParams = None
    ) -> QueryResult:
        """
        Get security alerts broken down by agent.
        
        Args:
            params: Query parameters
            
        Returns:
            QueryResult with security alerts by agent
        """
        params = params or MetricParams()
        
        # Create query for alerts by agent
        query = self.db_session.query(
            Event.agent_id,
            func.count().label('alert_count'),
            func.max(Event.timestamp).label('latest_alert')
        ).join(
            SecurityAlert, Event.id == SecurityAlert.event_id
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
                'alert_count': func.count(),
                'latest_alert': func.max(Event.timestamp)
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
                # Default sort by alert count descending
                query = query.order_by(desc(func.count()))
        else:
            # Default sort by alert count descending
            query = query.order_by(desc(func.count()))
        
        # Execute the paginated query
        return self.execute_paginated_query(query, params)
    
    def get_security_alerts_time_series(
        self, 
        params: TimeSeriesParams = None
    ) -> List[Dict[str, Any]]:
        """
        Get security alerts over time as a time series.
        
        Args:
            params: Query parameters
            
        Returns:
            List of time series data points
        """
        params = params or TimeSeriesParams()
        
        # Determine time range
        time_range = params.time_range or TimeRange.last_day()
        
        # Create query for alerts over time
        query = self.db_session.query(
            sql_time_bucket(Event.timestamp, params.resolution).label('bucket'),
            func.count().label('alert_count')
        ).join(
            SecurityAlert, Event.id == SecurityAlert.event_id
        )
        
        # Apply time range filter
        query = self.apply_time_filters(query, time_range, Event.timestamp)
        
        # Filter by agent IDs
        if params.agent_ids:
            query = query.filter(Event.agent_id.in_(params.agent_ids))
        
        # Filter by session IDs
        if params.session_ids:
            query = query.filter(Event.session_id.in_(params.session_ids))
        
        # Group by time bucket
        query = query.group_by('bucket')
        
        # Sort by time bucket
        query = query.order_by('bucket')
        
        # Execute the query
        results = query.all()
        
        # Format the time series data
        return format_time_series_data(
            results, 
            'bucket', 
            [('alert_count', 'sum')],
            time_range,
            params.resolution
        )
    
    def get_security_alerts_by_level(
        self, 
        params: MetricParams = None
    ) -> QueryResult:
        """
        Get security alerts aggregated by alert level.
        
        Args:
            params: Query parameters
            
        Returns:
            QueryResult with security alerts by level
        """
        params = params or MetricParams()
        
        # Create query for alerts by level
        query = self.db_session.query(
            SecurityAlert.severity.label('level'),
            func.count().label('alert_count'),
            func.count(func.distinct(Event.agent_id)).label('agent_count'),
            func.max(Event.timestamp).label('latest_alert')
        ).join(
            Event, SecurityAlert.event_id == Event.id
        )
        
        # Apply common filters
        query = self.apply_filters(query, params, Event)
        
        # Group by level
        query = query.group_by(SecurityAlert.severity)
        
        # Apply sorting
        if params.sort:
            # Prepare field mapping for sorting
            field_mapping = {
                'level': SecurityAlert.severity,
                'alert_count': func.count(),
                'agent_count': func.count(func.distinct(Event.agent_id)),
                'latest_alert': func.max(Event.timestamp)
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
                # Default sort by alert count descending
                query = query.order_by(desc(func.count()))
        else:
            # Default sort by alert count descending
            query = query.order_by(desc(func.count()))
        
        # Execute the paginated query
        return self.execute_paginated_query(query, params)
    
    def get_suspicious_inputs(
        self, 
        params: MetricParams = None
    ) -> QueryResult:
        """
        Get a list of suspicious inputs that triggered alerts.
        
        Args:
            params: Query parameters
            
        Returns:
            QueryResult with suspicious inputs
        """
        params = params or MetricParams()
        
        # Create query for suspicious inputs
        query = self.db_session.query(
            Event.agent_id,
            Event.timestamp,
            SecurityAlert.severity,
            SecurityAlert.category,
            LLMInteraction.request_data.label('input')
        ).join(
            SecurityAlert, Event.id == SecurityAlert.event_id
        ).join(
            LLMInteraction, LLMInteraction.event_id == SecurityAlert.source_event_id
        )
        
        # Apply common filters
        query = self.apply_filters(query, params, Event)
        
        # Apply sorting
        if params.sort:
            # Prepare field mapping for sorting
            field_mapping = {
                'agent_id': Event.agent_id,
                'timestamp': Event.timestamp,
                'severity': SecurityAlert.severity,
                'alert_type': SecurityAlert.category
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
                # Default sort by timestamp descending
                query = query.order_by(desc(Event.timestamp))
        else:
            # Default sort by timestamp descending
            query = query.order_by(desc(Event.timestamp))
        
        # Execute the paginated query
        result = self.execute_paginated_query(query, params)
        
        # Process input data to extract user messages
        processed_items = []
        for item in result.items:
            # Extract input from request data
            input_text = None
            if item.input:
                if isinstance(item.input, str):
                    try:
                        input_data = json.loads(item.input)
                    except json.JSONDecodeError:
                        input_data = {"content": item.input}
                else:
                    input_data = item.input
                    
                # Extract user input based on vendor format
                if isinstance(input_data, dict):
                    # OpenAI format
                    if "messages" in input_data:
                        for msg in input_data["messages"]:
                            if msg.get("role") == "user":
                                input_text = msg.get("content")
                                break
                    # Anthropic format
                    elif "prompt" in input_data:
                        input_text = input_data["prompt"]
                    # Direct content
                    elif "content" in input_data:
                        input_text = input_data["content"]
            
            # Add processed item
            processed_items.append({
                "agent_id": item.agent_id,
                "timestamp": item.timestamp,
                "severity": item.severity,
                "alert_type": item.category,
                "input_text": input_text or "Unknown input"
            })
        
        # Return new QueryResult with processed items
        return QueryResult(
            items=processed_items,
            total=result.total,
            page=result.page,
            page_size=result.page_size
        )