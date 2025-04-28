"""
LLM Analytics service.

This module provides centralized analytics for LLM usage, including:
- Request counts and success rates
- Response times and percentiles
- Token usage and cost estimations
- Breakdowns by agent, model, and time

It focuses on real-world analytics for AI engineers.
"""
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime, timedelta

from sqlalchemy import func, and_, or_, desc, text, case
from sqlalchemy.orm import Session, aliased

from src.models.event import Event
from src.models.llm_interaction import LLMInteraction
from src.analysis.interface import AnalysisInterface
from src.api.schemas.metrics import (
    LLMMetricsFilter, 
    LLMMetricsResponse, 
    LLMMetricsBreakdownItem,
    LLMMetricsBreakdownResponse,
    LLMMetricsBreakdown,
    TimeGranularity
)
from src.analysis.utils import (
    calculate_token_cost,
    sql_time_bucket
)
from src.services.pricing_service import pricing_service


class LLMAnalytics(AnalysisInterface):
    """
    LLM Analytics service for comprehensive metrics.
    
    This class provides methods for analyzing LLM usage patterns,
    performance metrics, and costs with flexible breakdowns.
    """
    
    def get_metrics(
        self,
        filters: LLMMetricsFilter,
        breakdown_by: LLMMetricsBreakdown = LLMMetricsBreakdown.NONE
    ) -> LLMMetricsBreakdownResponse:
        """
        Get comprehensive LLM metrics with optional breakdown.
        
        Args:
            filters: Query filters for agents, models, and time range
            breakdown_by: Dimension to break down metrics by
            
        Returns:
            LLM metrics with optional breakdown
        """
        print("DEBUG: Entering get_metrics method")
        
        # Fill in default time range if not provided
        if filters.from_time is None or filters.to_time is None:
            if filters.from_time is None:
                # Default to last 30 days if not specified
                filters.from_time = filters.to_time - timedelta(days=30) if filters.to_time else datetime.utcnow() - timedelta(days=30) + timedelta(hours=2)
                
            if filters.to_time is None:
                filters.to_time = datetime.utcnow() + timedelta(hours=2)
        
        # Get aggregated metrics
        print("DEBUG: About to call _get_aggregated_metrics")
        total_metrics = self._get_aggregated_metrics(filters)
        print("DEBUG: Got aggregated metrics successfully")
        
        # Initialize breakdown items list
        breakdown_items = []
        
        # Apply breakdown if requested
        if breakdown_by != LLMMetricsBreakdown.NONE:
            print(f"DEBUG: Applying breakdown: {breakdown_by}")
            if breakdown_by == LLMMetricsBreakdown.AGENT:
                breakdown_items = self._get_metrics_by_agent(filters)
            elif breakdown_by == LLMMetricsBreakdown.MODEL:
                breakdown_items = self._get_metrics_by_model(filters)
            elif breakdown_by == LLMMetricsBreakdown.TIME:
                breakdown_items = self._get_metrics_by_time(filters)
        
        # Create the response
        print("DEBUG: Creating response")
        try:
            response = LLMMetricsBreakdownResponse(
                total=total_metrics,
                breakdown=breakdown_items,
                from_time=filters.from_time,
                to_time=filters.to_time,
                filters=filters,
                breakdown_by=breakdown_by
            )
            print("DEBUG: Successfully created response")
            return response
        except Exception as e:
            print(f"DEBUG ERROR in response creation: {str(e)}")
            import traceback
            print(f"DEBUG TRACEBACK: {traceback.format_exc()}")
            raise
    
    def _get_aggregated_metrics(self, filters: LLMMetricsFilter) -> LLMMetricsResponse:
        """
        Get aggregated metrics for the given filters.
        
        Args:
            filters: Query filters
            
        Returns:
            Aggregated metrics
        """
        print("DEBUG: Entered _get_aggregated_metrics")
        
        # Base query for counts, rates, and token usage
        query = self.db_session.query(
            func.count().label('request_count'),
            func.avg(LLMInteraction.duration_ms).label('response_time_avg'),
            func.sum(case((LLMInteraction.stop_reason == 'end_turn', 1), else_=0)).label('success_count'),
            func.sum(case((and_(LLMInteraction.stop_reason != None, LLMInteraction.stop_reason != 'end_turn'), 1), else_=0)).label('error_count'),
            func.sum(LLMInteraction.input_tokens).label('token_count_input'),
            func.sum(LLMInteraction.output_tokens).label('token_count_output'),
            func.sum(LLMInteraction.total_tokens).label('token_count_total'),
            func.min(Event.timestamp).label('first_seen'),
            func.max(Event.timestamp).label('last_seen')
        ).join(
            Event, LLMInteraction.event_id == Event.id
        )
        
        print("DEBUG: Created base query")
        
        # Apply filters
        query = self._apply_filters(query, filters)
        
        print("DEBUG: Applied filters")
        
        # Execute the query
        result = query.first()
        
        print(f"DEBUG: Query executed, result = {result}")
        
        # Handle empty results
        if not result or not result.request_count:
            print("DEBUG: No results found, returning zeros")
            return LLMMetricsResponse(
                request_count=0,
                response_time_avg=0,
                response_time_p95=0,
                success_rate=0,
                error_rate=0,
                token_count_input=0,
                token_count_output=0,
                token_count_total=0,
                estimated_cost_usd=0,
                first_seen=None,
                last_seen=None
            )
        
        print(f"DEBUG: Found {result.request_count} requests")    
            
        # Calculate percentiles separately 
        percentiles_query = self.db_session.query(
            LLMInteraction.duration_ms
        ).join(
            Event, LLMInteraction.event_id == Event.id
        )
        
        # Apply same filters
        percentiles_query = self._apply_filters(percentiles_query, filters)
        
        # Execute percentiles query
        response_times = [r[0] for r in percentiles_query.all() if r[0] is not None]
        print(f"DEBUG: Found {len(response_times)} response times")
        
        p95 = 0
        if response_times:
            try:
                import numpy as np
                p95 = float(np.percentile(response_times, 95))
                print(f"DEBUG: Calculated p95 = {p95} using numpy")
            except (ImportError, TypeError, ValueError) as e:
                print(f"DEBUG: Error using numpy: {str(e)}")
                # Fallback if numpy is not available or other error
                response_times.sort()
                idx = int(len(response_times) * 0.95)
                p95 = float(response_times[idx] if idx < len(response_times) else response_times[-1])
                print(f"DEBUG: Calculated p95 = {p95} using fallback method")
        
        # Calculate success and error rates
        total_requests = result.request_count or 1  # Avoid division by zero
        success_rate = result.success_count / total_requests if result.success_count else 0
        error_rate = result.error_count / total_requests if result.error_count else 0
        
        print(f"DEBUG: Calculated rates: success={success_rate}, error={error_rate}")
        
        # Get model breakdown for cost calculation
        model_query = self.db_session.query(
            LLMInteraction.model,
            func.sum(LLMInteraction.input_tokens).label('input_tokens'),
            func.sum(LLMInteraction.output_tokens).label('output_tokens')
        ).join(
            Event, LLMInteraction.event_id == Event.id
        )
        
        # Apply filters
        model_query = self._apply_filters(model_query, filters)
        
        # Group by model
        model_query = model_query.group_by(LLMInteraction.model)
        
        # Execute
        model_costs = model_query.all()
        
        print(f"DEBUG: Got model costs: {len(model_costs)} records")
        
        # Calculate total cost using pricing service
        total_cost = 0
        for cost in model_costs:
            try:
                model = cost.model
                input_tokens = cost.input_tokens or 0
                output_tokens = cost.output_tokens or 0
                
                # Use pricing service to calculate cost
                cost_result = pricing_service.calculate_cost(input_tokens, output_tokens, model)
                model_cost = cost_result['total_cost']
                
                total_cost += model_cost
                print(f"DEBUG: Added cost {model_cost} for model {model}")
            except Exception as e:
                print(f"DEBUG: Error calculating cost: {str(e)}")
                # Continue with next model
        
        # If no model breakdown is available but we have token counts, use default pricing
        if not model_costs and (result.token_count_input or result.token_count_output):
            # Use pricing service with default model
            cost_result = pricing_service.calculate_cost(
                result.token_count_input or 0,
                result.token_count_output or 0,
                "default"
            )
            total_cost = cost_result['total_cost']
        
        print(f"DEBUG: Total cost = {total_cost}")
        
        # Build response
        print("DEBUG: Creating response object")
        try:
            response = LLMMetricsResponse(
                request_count=result.request_count or 0,
                response_time_avg=result.response_time_avg or 0,
                response_time_p95=p95,
                success_rate=success_rate,
                error_rate=error_rate,
                token_count_input=result.token_count_input or 0,
                token_count_output=result.token_count_output or 0,
                token_count_total=(result.token_count_total or 0) if (result.token_count_total or 0) > 0 
                    else (result.token_count_input or 0) + (result.token_count_output or 0),
                estimated_cost_usd=total_cost,
                first_seen=result.first_seen,
                last_seen=result.last_seen
            )
            print("DEBUG: Successfully created response")
            return response
        except Exception as e:
            print(f"DEBUG: Error creating response: {str(e)}")
            import traceback
            print(f"DEBUG: {traceback.format_exc()}")
            raise
    
    def _get_metrics_by_agent(self, filters: LLMMetricsFilter) -> List[LLMMetricsBreakdownItem]:
        """
        Get metrics broken down by agent.
        
        Args:
            filters: Query filters
            
        Returns:
            List of breakdown items by agent
        """
        # Base query with agent grouping
        query = self.db_session.query(
            Event.agent_id.label('key'),
            func.count().label('request_count'),
            func.avg(LLMInteraction.duration_ms).label('response_time_avg'),
            func.sum(case((LLMInteraction.stop_reason == 'end_turn', 1), else_=0)).label('success_count'),
            func.sum(case((and_(LLMInteraction.stop_reason != None, LLMInteraction.stop_reason != 'end_turn'), 1), else_=0)).label('error_count'),
            func.sum(LLMInteraction.input_tokens).label('token_count_input'),
            func.sum(LLMInteraction.output_tokens).label('token_count_output'),
            func.sum(LLMInteraction.total_tokens).label('token_count_total'),
            func.min(Event.timestamp).label('first_seen'),
            func.max(Event.timestamp).label('last_seen')
        ).join(
            Event, LLMInteraction.event_id == Event.id
        )
        
        # Apply filters
        query = self._apply_filters(query, filters)
        
        # Group by agent
        query = query.group_by(Event.agent_id)
        
        # Sort by request count descending
        query = query.order_by(desc('request_count'))
        
        # Execute the query
        results = query.all()
        
        # Process results
        breakdown_items = []
        
        for result in results:
            # Skip entries with no agent ID
            if not result.key:
                continue
                
            # Calculate rates
            total_requests = result.request_count or 1
            success_rate = result.success_count / total_requests if result.success_count else 0
            error_rate = result.error_count / total_requests if result.error_count else 0
            
            # Calculate p95 for this agent
            agent_filter = LLMMetricsFilter(
                agent_id=result.key,
                model_name=filters.model_name,
                from_time=filters.from_time,
                to_time=filters.to_time
            )
            p95 = self._calculate_response_time_percentile(agent_filter, 95)
            
            # Calculate cost for this agent
            agent_cost = self._calculate_cost_for_agent(result.key, filters)
            
            # Create metrics for this agent
            metrics = LLMMetricsResponse(
                request_count=result.request_count or 0,
                response_time_avg=result.response_time_avg or 0,
                response_time_p95=p95,
                success_rate=success_rate,
                error_rate=error_rate,
                token_count_input=result.token_count_input or 0,
                token_count_output=result.token_count_output or 0,
                token_count_total=(result.token_count_total or 0) if (result.token_count_total or 0) > 0 
                    else (result.token_count_input or 0) + (result.token_count_output or 0),
                estimated_cost_usd=agent_cost,
                first_seen=result.first_seen,
                last_seen=result.last_seen
            )
            
            # Add to breakdown items
            breakdown_items.append(
                LLMMetricsBreakdownItem(
                    key=result.key,
                    metrics=metrics
                )
            )
        
        return breakdown_items
    
    def _get_metrics_by_model(self, filters: LLMMetricsFilter) -> List[LLMMetricsBreakdownItem]:
        """
        Get metrics broken down by model.
        
        Args:
            filters: Query filters
            
        Returns:
            List of breakdown items by model
        """
        # Base query with model grouping
        query = self.db_session.query(
            LLMInteraction.model.label('key'),
            func.count().label('request_count'),
            func.avg(LLMInteraction.duration_ms).label('response_time_avg'),
            func.sum(case((LLMInteraction.stop_reason == 'end_turn', 1), else_=0)).label('success_count'),
            func.sum(case((and_(LLMInteraction.stop_reason != None, LLMInteraction.stop_reason != 'end_turn'), 1), else_=0)).label('error_count'),
            func.sum(LLMInteraction.input_tokens).label('token_count_input'),
            func.sum(LLMInteraction.output_tokens).label('token_count_output'),
            func.sum(LLMInteraction.total_tokens).label('token_count_total'),
            func.min(Event.timestamp).label('first_seen'),
            func.max(Event.timestamp).label('last_seen')
        ).join(
            Event, LLMInteraction.event_id == Event.id
        )
        
        # Apply filters
        query = self._apply_filters(query, filters)
        
        # Group by model
        query = query.group_by(LLMInteraction.model)
        
        # Sort by request count descending
        query = query.order_by(desc('request_count'))
        
        # Execute the query
        results = query.all()
        
        # Process results
        breakdown_items = []
        
        for result in results:
            # Skip entries with no model
            if not result.key:
                continue
                
            # Calculate rates
            total_requests = result.request_count or 1
            success_rate = result.success_count / total_requests if result.success_count else 0
            error_rate = result.error_count / total_requests if result.error_count else 0
            
            # Calculate p95 for this model
            model_filter = LLMMetricsFilter(
                agent_id=filters.agent_id,
                model_name=result.key,
                from_time=filters.from_time,
                to_time=filters.to_time
            )
            p95 = self._calculate_response_time_percentile(model_filter, 95)
            
            # Calculate cost for this model
            model_cost = calculate_token_cost(
                result.token_count_input or 0,
                result.token_count_output or 0,
                result.key
            )
            
            # Create metrics for this model
            metrics = LLMMetricsResponse(
                request_count=result.request_count or 0,
                response_time_avg=result.response_time_avg or 0,
                response_time_p95=p95,
                success_rate=success_rate,
                error_rate=error_rate,
                token_count_input=result.token_count_input or 0,
                token_count_output=result.token_count_output or 0,
                token_count_total=(result.token_count_total or 0) if (result.token_count_total or 0) > 0 
                    else (result.token_count_input or 0) + (result.token_count_output or 0),
                estimated_cost_usd=model_cost,
                first_seen=result.first_seen,
                last_seen=result.last_seen
            )
            
            # Add to breakdown items
            breakdown_items.append(
                LLMMetricsBreakdownItem(
                    key=result.key,
                    metrics=metrics
                )
            )
        
        return breakdown_items
    
    def _get_metrics_by_time(self, filters: LLMMetricsFilter) -> List[LLMMetricsBreakdownItem]:
        """
        Get metrics broken down by time buckets.
        
        Args:
            filters: Query filters
            
        Returns:
            List of breakdown items by time
        """
        # Use raw SQL for time bucketing for more reliable results
        from sqlalchemy import text
        
        # Build time format string based on granularity
        time_format = '%Y-%m-%d'  # Default to day
        if filters.granularity == TimeGranularity.MINUTE:
            time_format = '%Y-%m-%d %H:%M'
        elif filters.granularity == TimeGranularity.HOUR:
            time_format = '%Y-%m-%d %H'
        
        # Build the SQL query with time bucketing
        query_str = """
        SELECT 
            strftime(:time_format, events.timestamp) as time_bucket,
            COUNT(*) as request_count,
            AVG(llm_interactions.duration_ms) as response_time_avg,
            SUM(CASE WHEN llm_interactions.stop_reason = 'end_turn' THEN 1 ELSE 0 END) as success_count,
            SUM(CASE WHEN llm_interactions.stop_reason IS NOT NULL AND llm_interactions.stop_reason != 'end_turn' THEN 1 ELSE 0 END) as error_count,
            SUM(llm_interactions.input_tokens) as token_count_input,
            SUM(llm_interactions.output_tokens) as token_count_output,
            SUM(llm_interactions.total_tokens) as token_count_total
        FROM 
            llm_interactions 
        JOIN 
            events ON llm_interactions.event_id = events.id
        WHERE 
            llm_interactions.interaction_type = 'finish'
        """
        
        # Add filters to the query
        params = {"time_format": time_format}
        
        if filters.from_time and filters.to_time:
            query_str += " AND events.timestamp >= :from_time AND events.timestamp <= :to_time"
            params["from_time"] = filters.from_time
            params["to_time"] = filters.to_time
            
        if filters.agent_id:
            query_str += " AND events.agent_id = :agent_id"
            params["agent_id"] = filters.agent_id
            
        if filters.model_name:
            query_str += " AND llm_interactions.model = :model_name"
            params["model_name"] = filters.model_name
        
        # Group by time bucket and order by it
        query_str += """
        GROUP BY time_bucket
        ORDER BY time_bucket
        """
        
        # Execute the query
        results = self.db_session.execute(text(query_str), params).fetchall()
        
        # Process results
        breakdown_items = []
        
        for result in results:
            if not result.time_bucket:
                continue
                
            # Calculate rates
            total_requests = result.request_count or 1
            success_rate = result.success_count / total_requests if result.success_count else 0
            error_rate = result.error_count / total_requests if result.error_count else 0
            
            # Format timestamp as string key
            key = str(result.time_bucket)
            
            # Calculate cost for this time bucket
            bucket_cost = self._calculate_cost_for_bucket(
                key, 
                result.token_count_input or 0, 
                result.token_count_output or 0,
                filters
            )
            
            # p95 calculation would be complex for time buckets, use average * 2 as approximation
            p95 = (result.response_time_avg or 0) * 2
            
            # Create metrics for this time bucket
            metrics = LLMMetricsResponse(
                request_count=result.request_count or 0,
                response_time_avg=result.response_time_avg or 0,
                response_time_p95=p95,
                success_rate=success_rate,
                error_rate=error_rate,
                token_count_input=result.token_count_input or 0,
                token_count_output=result.token_count_output or 0,
                token_count_total=(result.token_count_total or 0) if (result.token_count_total or 0) > 0
                    else (result.token_count_input or 0) + (result.token_count_output or 0),
                estimated_cost_usd=bucket_cost,
                first_seen=None,  # Time bucket is already represented by key
                last_seen=None    # Time bucket is already represented by key
            )
            
            # Add to breakdown items
            breakdown_items.append(
                LLMMetricsBreakdownItem(
                    key=key,
                    metrics=metrics
                )
            )
        
        return breakdown_items
    
    def _apply_filters(self, query, filters: LLMMetricsFilter):
        """Apply common filters to a query."""
        # Filter by time range
        if filters.from_time and filters.to_time:
            query = query.filter(Event.timestamp >= filters.from_time)
            query = query.filter(Event.timestamp <= filters.to_time)
            
        # Filter by agent ID
        if filters.agent_id:
            query = query.filter(Event.agent_id == filters.agent_id)
            
        # Filter by model name
        if filters.model_name:
            query = query.filter(LLMInteraction.model == filters.model_name)
            
        # Only include finished requests to avoid double-counting
        query = query.filter(LLMInteraction.interaction_type == 'finish')
        
        return query
    
    def _get_model_cost_query(self, filters: LLMMetricsFilter):
        """Get query for model costs."""
        query = self.db_session.query(
            LLMInteraction.model,
            func.sum(LLMInteraction.input_tokens).label('input_tokens'),
            func.sum(LLMInteraction.output_tokens).label('output_tokens')
        ).join(
            Event, LLMInteraction.event_id == Event.id
        )
        
        # Apply filters
        query = self._apply_filters(query, filters)
        
        # Group by model
        query = query.group_by(LLMInteraction.model)
        
        return query
    
    def _calculate_response_time_percentile(self, filters: LLMMetricsFilter, percentile: int) -> float:
        """Calculate response time percentile for the given filters."""
        query = self.db_session.query(
            LLMInteraction.duration_ms
        ).join(
            Event, LLMInteraction.event_id == Event.id
        )
        
        # Apply filters
        query = self._apply_filters(query, filters)
        
        # Get all response times
        response_times = [r[0] for r in query.all() if r[0] is not None]
        
        # Calculate percentile
        if response_times:
            try:
                import numpy as np
                return float(np.percentile(response_times, percentile))
            except (ImportError, TypeError, ValueError):
                # Fallback if numpy is not available or other error
                response_times.sort()
                idx = int(len(response_times) * (percentile / 100))
                return float(response_times[idx] if idx < len(response_times) else response_times[-1])
        else:
            return 0.0
    
    def _calculate_cost_for_agent(self, agent_id: str, filters: LLMMetricsFilter) -> float:
        """
        Calculate cost for a specific agent based on their model usage.
        
        Args:
            agent_id: Agent ID
            filters: Query filters
            
        Returns:
            Estimated cost for this agent
        """
        # Get model distribution for this agent
        model_query = self.db_session.query(
            LLMInteraction.model,
            func.sum(LLMInteraction.input_tokens).label('input_tokens'),
            func.sum(LLMInteraction.output_tokens).label('output_tokens')
        ).join(
            Event, LLMInteraction.event_id == Event.id
        ).filter(
            Event.agent_id == agent_id
        )
        
        # Apply time filters
        if filters.from_time:
            model_query = model_query.filter(Event.timestamp >= filters.from_time)
        if filters.to_time:
            model_query = model_query.filter(Event.timestamp <= filters.to_time)
        
        # Group by model
        model_query = model_query.group_by(LLMInteraction.model)
        
        # Execute
        models = model_query.all()
        
        # Calculate cost for each model
        total_cost = 0
        for model_row in models:
            model = model_row.model
            model_input = model_row.input_tokens or 0
            model_output = model_row.output_tokens or 0
            
            # Use the pricing service to calculate costs
            cost_result = pricing_service.calculate_cost(model_input, model_output, model)
            total_cost += cost_result['total_cost']
        
        return total_cost
    
    def _calculate_cost_for_bucket(
        self, 
        bucket: str, 
        input_tokens: int, 
        output_tokens: int,
        filters: LLMMetricsFilter
    ) -> float:
        """
        Calculate cost for a time bucket based on model usage within that bucket.
        
        Args:
            bucket: Time bucket string
            input_tokens: Number of input tokens in this bucket
            output_tokens: Number of output tokens in this bucket
            filters: Query filters
            
        Returns:
            Estimated cost for this bucket
        """
        # Query to get model distribution in this bucket
        model_query = self.db_session.query(
            LLMInteraction.model,
            func.sum(LLMInteraction.input_tokens).label('input_tokens'),
            func.sum(LLMInteraction.output_tokens).label('output_tokens')
        ).join(
            Event, LLMInteraction.event_id == Event.id
        ).filter(
            sql_time_bucket(Event.timestamp, filters.granularity) == bucket
        )
        
        # Apply base filters
        model_query = self._apply_filters(model_query, filters)
        
        # Group by model
        model_query = model_query.group_by(LLMInteraction.model)
        
        # Execute
        models = model_query.all()
        
        # If no model breakdown is available, use the aggregate cost calculation
        if not models:
            # Use the pricing service to calculate costs
            cost_result = pricing_service.calculate_cost(input_tokens, output_tokens, "default")
            return cost_result['total_cost']
        
        # Calculate cost for each model
        total_cost = 0
        for model_row in models:
            model = model_row.model
            model_input = model_row.input_tokens or 0
            model_output = model_row.output_tokens or 0
            
            # Use the pricing service to calculate costs
            cost_result = pricing_service.calculate_cost(model_input, model_output, model)
            total_cost += cost_result['total_cost']
        
        return total_cost

    def get_agent_model_time_distribution(
        self,
        agent_id: str,
        model_name: str,
        filters: LLMMetricsFilter
    ) -> List[Dict[str, Any]]:
        """
        Get time-based distribution data for a specific agent-model combination.
        
        This method provides time-series data that can be used to create histograms
        showing when an agent used a particular model.
        
        Args:
            agent_id: Agent ID to analyze
            model_name: Model name to analyze
            filters: General query filters
            
        Returns:
            List of time buckets with usage metrics
        """
        # Base time bucket query
        time_bucket_sql = sql_time_bucket(filters.granularity)
        
        query = self.db_session.query(
            text(time_bucket_sql).label('time_bucket'),
            func.count().label('request_count'),
            func.sum(LLMInteraction.input_tokens).label('input_tokens'),
            func.sum(LLMInteraction.output_tokens).label('output_tokens'),
            func.sum(LLMInteraction.total_tokens).label('total_tokens'),
            func.avg(LLMInteraction.duration_ms).label('avg_duration')
        ).join(
            Event, LLMInteraction.event_id == Event.id
        ).filter(
            and_(
                Event.timestamp >= filters.from_time,
                Event.timestamp <= filters.to_time,
                Event.agent_id == agent_id,
                LLMInteraction.model == model_name
            )
        ).group_by(
            text('time_bucket')
        ).order_by(
            text('time_bucket')
        )
        
        # Execute query
        results = query.all()
        
        # Format results
        distribution = []
        for row in results:
            if row.time_bucket is None:
                continue
            
            distribution.append({
                'timestamp': row.time_bucket,
                'request_count': row.request_count or 0,
                'input_tokens': row.input_tokens or 0,
                'output_tokens': row.output_tokens or 0,
                'total_tokens': (row.total_tokens or 0) if (row.total_tokens or 0) > 0
                    else (row.input_tokens or 0) + (row.output_tokens or 0),
                'avg_duration': row.avg_duration or 0
            })
        
        return distribution

    def get_agent_model_token_distribution(
        self,
        agent_id: str,
        model_name: str,
        filters: LLMMetricsFilter
    ) -> List[Dict[str, Any]]:
        """
        Get token usage distribution data for a specific agent-model combination.
        
        This method provides token usage data that can be used to create histograms
        showing token consumption patterns.
        
        Args:
            agent_id: Agent ID to analyze
            model_name: Model name to analyze
            filters: General query filters
            
        Returns:
            List of token usage buckets with metrics
        """
        # Create buckets for token counts (0-100, 100-500, 500-1000, etc.)
        token_buckets = [
            (0, 100),
            (100, 500),
            (500, 1000),
            (1000, 2000),
            (2000, 5000),
            (5000, 10000),
            (10000, float('inf'))
        ]
        
        distribution = []
        
        # Query the DB for each bucket range
        for lower, upper in token_buckets:
            upper_filter = LLMInteraction.total_tokens < upper if upper != float('inf') else True
            
            query = self.db_session.query(
                func.count().label('request_count'),
                func.sum(LLMInteraction.input_tokens).label('input_tokens'),
                func.sum(LLMInteraction.output_tokens).label('output_tokens'),
                func.sum(LLMInteraction.total_tokens).label('total_tokens'),
                func.avg(LLMInteraction.duration_ms).label('avg_duration')
            ).join(
                Event, LLMInteraction.event_id == Event.id
            ).filter(
                and_(
                    Event.timestamp >= filters.from_time,
                    Event.timestamp <= filters.to_time,
                    Event.agent_id == agent_id,
                    LLMInteraction.model == model_name,
                    LLMInteraction.total_tokens >= lower,
                    upper_filter
                )
            )
            
            result = query.first()
            
            if result and result.request_count:
                distribution.append({
                    'bucket_range': f"{lower}-{upper if upper != float('inf') else 'inf'}",
                    'lower_bound': lower,
                    'upper_bound': upper if upper != float('inf') else None,
                    'request_count': result.request_count or 0,
                    'input_tokens': result.input_tokens or 0,
                    'output_tokens': result.output_tokens or 0,
                    'total_tokens': result.total_tokens or 0,
                    'avg_duration': result.avg_duration or 0
                })
        
        return distribution 