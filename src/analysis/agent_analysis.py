"""
Agent analysis functions for the Cylestio dashboard.

This module provides functions for analyzing agent data and their performance metrics.
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple

from sqlalchemy import func, and_, or_, desc, asc, extract, text
from sqlalchemy.orm import Session, joinedload

from src.models.agent import Agent
from src.models.event import Event
from src.models.session import Session as SessionModel
from src.models.trace import Trace
from src.models.llm_interaction import LLMInteraction
from src.models.tool_interaction import ToolInteraction
from src.models.security_alert import SecurityAlert

from src.analysis.interface import (
    TimeRangeParams, 
    PaginationParams, 
    SortParams, 
    QueryResult,
    BaseQueryParams,
    SortDirection,
    MetricSummary,
    TimeRange,
    TimeResolution
)

import logging
logger = logging.getLogger(__name__)


@dataclass
class AgentQueryParams(BaseQueryParams):
    """
    Parameters for agent queries.
    
    Attributes:
        status: Filter by agent status
        agent_type: Filter by agent type
        created_after: Filter by creation date
    """
    status: Optional[str] = None
    agent_type: Optional[str] = None
    created_after: Optional[datetime] = None


def get_agents(
    db: Session,
    filters: Dict[str, Any],
    pagination_params: PaginationParams,
    sort_by: str = "created_at",
    sort_dir: str = "desc"
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Get a list of agents with optional filtering, sorting, and pagination.
    
    Args:
        db: Database session
        filters: Filtering parameters
        pagination_params: Pagination parameters
        sort_by: Field to sort by
        sort_dir: Sort direction (asc, desc)
        
    Returns:
        Tuple[List[Dict], int]: List of agents and total count
    """
    # Start with base query for agents
    query = db.query(Agent)
    
    # Apply filters
    if "status" in filters and filters["status"]:
        query = query.filter(Agent.is_active == (filters["status"].lower() == "active"))
        
    if "type" in filters and filters["type"]:
        # Since type is determined dynamically, we can't filter it at the DB level
        # We'll filter it after getting results
        pass
        
    if "created_at_min" in filters and filters["created_at_min"]:
        query = query.filter(Agent.first_seen >= filters["created_at_min"])
    
    # Count total matching records
    total = query.count()
    
    # Apply sorting
    if sort_by == "created_at":
        if sort_dir.lower() == "asc":
            query = query.order_by(Agent.first_seen.asc())
        else:
            query = query.order_by(Agent.first_seen.desc())
    elif sort_by == "updated_at":
        if sort_dir.lower() == "asc":
            query = query.order_by(Agent.last_seen.asc())
        else:
            query = query.order_by(Agent.last_seen.desc())
    elif sort_by == "name":
        if sort_dir.lower() == "asc":
            query = query.order_by(Agent.name.asc())
        else:
            query = query.order_by(Agent.name.desc())
    
    # Apply pagination
    offset = pagination_params.offset
    limit = pagination_params.limit
    query = query.offset(offset).limit(limit)
    
    # Execute query
    agents = query.all()
    
    # Prepare result items
    items = []
    for agent in agents:
        # Get recent time for summary metrics
        recent_time = datetime.utcnow() - timedelta(days=30)
        
        # Get metrics for this agent
        request_count = db.query(func.count(Event.id)).filter(
            Event.agent_id == agent.agent_id,
            Event.timestamp >= recent_time,
            Event.name.startswith("llm.")
        ).scalar() or 0
        
        # Extract the total token count from the token usage dictionary
        token_usage_dict = agent.get_token_usage(db, recent_time) if hasattr(agent, 'get_token_usage') else {}
        total_tokens = 0
        for model_data in token_usage_dict.values():
            total_tokens += model_data.get('total_tokens', 0)
        
        error_count = db.query(func.count(Event.id)).filter(
            Event.agent_id == agent.agent_id,
            Event.timestamp >= recent_time,
            Event.level == "error"
        ).scalar() or 0
        
        # Determine agent type based on events
        agent_type = "other"
        if db.query(Event).filter(
            Event.agent_id == agent.agent_id,
            Event.name.like("framework.assistant%")
        ).first():
            agent_type = "assistant"
        elif db.query(Event).filter(
            Event.agent_id == agent.agent_id,
            Event.name.like("framework.chatbot%")
        ).first():
            agent_type = "chatbot"
        elif db.query(Event).filter(
            Event.agent_id == agent.agent_id,
            Event.name.like("framework.autonomous%")
        ).first():
            agent_type = "autonomous"
        elif db.query(Event).filter(
            Event.agent_id == agent.agent_id,
            Event.name.like("framework.function%")
        ).first():
            agent_type = "function"
        
        # Apply type filter after determining agent_type
        if "type" in filters and filters["type"] and agent_type != filters["type"]:
            continue
        
        items.append({
            "agent_id": agent.agent_id,
            "name": agent.name,
            "type": agent_type,
            "status": "active" if agent.is_active else "inactive",
            "created_at": agent.first_seen,
            "updated_at": agent.last_seen,
            "request_count": request_count,
            "token_usage": total_tokens,
            "error_count": error_count
        })
    
    # If we filtered by type after the query, recalculate total
    if "type" in filters and filters["type"]:
        total = len(items)
    
    return items, total


def get_agent_by_id(db: Session, agent_id: str) -> Optional[Dict[str, Any]]:
    """
    Get detailed information about a specific agent.
    
    Args:
        db: Database session
        agent_id: Agent ID
        
    Returns:
        Dict: Agent details or None if not found
    """
    # Query the agent
    agent = db.query(Agent).filter(Agent.agent_id == agent_id).first()
    
    if not agent:
        return None
    
    # Get agent statistics
    stats = agent.get_statistics(db)
    
    # Calculate additional metrics based on events
    recent_time = datetime.utcnow() - timedelta(days=30)  # Last 30 days by default
    
    # Token usage
    token_usage = agent.get_token_usage(db, recent_time)
    
    # Get tool usage
    tool_usage = agent.get_tool_usage(db, recent_time)
    
    # Calculate average response time
    avg_response_time = db.query(
        func.avg(
            func.extract('epoch', LLMInteraction.response_timestamp) - 
            func.extract('epoch', LLMInteraction.request_timestamp)
        ) * 1000  # Convert to milliseconds
    ).join(Event).filter(
        Event.agent_id == agent.agent_id,
        Event.timestamp >= recent_time,
        LLMInteraction.request_timestamp.isnot(None),
        LLMInteraction.response_timestamp.isnot(None)
    ).scalar() or 0

    # If no response time calculated, try using duration_ms
    if avg_response_time == 0:
        avg_response_time = db.query(
            func.avg(LLMInteraction.duration_ms)
        ).join(Event).filter(
            Event.agent_id == agent.agent_id,
            Event.timestamp >= recent_time,
            LLMInteraction.duration_ms.isnot(None)
        ).scalar() or 0
    
    # Determine agent type based on events
    agent_type = "other"
    if db.query(Event).filter(
        Event.agent_id == agent.agent_id,
        Event.name.like("framework.assistant%")
    ).first():
        agent_type = "assistant"
    elif db.query(Event).filter(
        Event.agent_id == agent.agent_id,
        Event.name.like("framework.chatbot%")
    ).first():
        agent_type = "chatbot"
    elif db.query(Event).filter(
        Event.agent_id == agent.agent_id,
        Event.name.like("framework.autonomous%")
    ).first():
        agent_type = "autonomous"
    elif db.query(Event).filter(
        Event.agent_id == agent.agent_id,
        Event.name.like("framework.function%")
    ).first():
        agent_type = "function"
    
    # Get configuration from recent events
    config_event = db.query(Event).filter(
        Event.agent_id == agent.agent_id,
        Event.name == "framework.config"
    ).order_by(Event.timestamp.desc()).first()
    
    configuration = {}
    if config_event and config_event.raw_data:
        config_data = config_event.raw_data.get("data", {})
        if isinstance(config_data, dict):
            configuration = config_data
    
    return {
        "agent_id": agent.agent_id,
        "name": agent.name,
        "type": agent_type,
        "status": "active" if agent.is_active else "inactive",
        "description": f"Agent running {agent.system_info}" if agent.system_info else None,
        "created_at": agent.first_seen,
        "updated_at": agent.last_seen,
        "configuration": configuration,
        "metrics": {
            "request_count": stats.get("event_count", 0),
            "token_usage": token_usage.get("total_tokens", 0),
            "avg_response_time_ms": avg_response_time,
            "tool_usage": sum(tool_usage.values()),
            "error_count": db.query(func.count(Event.id)).filter(
                Event.agent_id == agent.agent_id,
                Event.level == "error"
            ).scalar() or 0
        }
    }


def get_agent_dashboard_metrics(db: Session, agent_id: str, time_range: TimeRange) -> List[MetricSummary]:
    """
    Get dashboard metrics for a specific agent.
    
    Args:
        db: Database session
        agent_id: Agent ID
        time_range: Time range for metrics
        
    Returns:
        List[MetricSummary]: List of metrics with trend information
    """
    # Convert TimeRange to TimeRangeParams
    if time_range == TimeRange.HOUR:
        current_period = TimeRangeParams.last_hour()
        previous_period = TimeRangeParams(
            start=current_period.start - timedelta(hours=1),
            end=current_period.start
        )
    elif time_range == TimeRange.DAY:
        current_period = TimeRangeParams.last_day()
        previous_period = TimeRangeParams(
            start=current_period.start - timedelta(days=1),
            end=current_period.start
        )
    elif time_range == TimeRange.WEEK:
        current_period = TimeRangeParams.last_week()
        previous_period = TimeRangeParams(
            start=current_period.start - timedelta(days=7),
            end=current_period.start
        )
    else:  # TimeRange.MONTH
        current_period = TimeRangeParams.last_month()
        previous_period = TimeRangeParams(
            start=current_period.start - timedelta(days=30),
            end=current_period.start
        )
    
    # Check if agent exists
    agent = db.query(Agent).filter(Agent.agent_id == agent_id).first()
    if not agent:
        return []
    
    # Calculate metrics
    metrics = []
    
    # LLM Request Count
    current_llm_count = db.query(func.count(Event.id)).join(LLMInteraction).filter(
        Event.agent_id == agent_id,
        Event.timestamp >= current_period.start,
        Event.timestamp <= current_period.end
    ).scalar() or 0
    
    previous_llm_count = db.query(func.count(Event.id)).join(LLMInteraction).filter(
        Event.agent_id == agent_id,
        Event.timestamp >= previous_period.start,
        Event.timestamp <= previous_period.end
    ).scalar() or 0
    
    llm_change = calculate_percent_change(previous_llm_count, current_llm_count)
    metrics.append(MetricSummary(
        metric="llm_request_count",
        value=current_llm_count,
        change=llm_change,
        trend="up" if llm_change > 0 else "down" if llm_change < 0 else "flat"
    ))
    
    # Token Usage
    token_usage = agent.get_token_usage(db, current_period.start, current_period.end)
    current_token_count = token_usage.get("total_tokens", 0)
    
    previous_token_usage = agent.get_token_usage(db, previous_period.start, previous_period.end)
    previous_token_count = previous_token_usage.get("total_tokens", 0)
    
    token_change = calculate_percent_change(previous_token_count, current_token_count)
    metrics.append(MetricSummary(
        metric="token_usage",
        value=current_token_count,
        change=token_change,
        trend="up" if token_change > 0 else "down" if token_change < 0 else "flat"
    ))
    
    # Avg Response Time
    current_resp_time = db.query(
        func.avg(
            func.extract('epoch', LLMInteraction.response_timestamp) - 
            func.extract('epoch', LLMInteraction.request_timestamp)
        ) * 1000  # Convert to milliseconds
    ).join(Event).filter(
        Event.agent_id == agent_id,
        Event.timestamp >= current_period.start,
        Event.timestamp <= current_period.end,
        LLMInteraction.request_timestamp.isnot(None),
        LLMInteraction.response_timestamp.isnot(None)
    ).scalar() or 0
    
    previous_resp_time = db.query(
        func.avg(
            func.extract('epoch', LLMInteraction.response_timestamp) - 
            func.extract('epoch', LLMInteraction.request_timestamp)
        ) * 1000  # Convert to milliseconds
    ).join(Event).filter(
        Event.agent_id == agent_id,
        Event.timestamp >= previous_period.start,
        Event.timestamp <= previous_period.end,
        LLMInteraction.request_timestamp.isnot(None),
        LLMInteraction.response_timestamp.isnot(None)
    ).scalar() or 0
    
    # Alternatively, we can use the duration_ms field if it's populated
    if current_resp_time == 0:
        current_resp_time = db.query(
            func.avg(LLMInteraction.duration_ms)
        ).join(Event).filter(
            Event.agent_id == agent_id,
            Event.timestamp >= current_period.start,
            Event.timestamp <= current_period.end,
            LLMInteraction.duration_ms.isnot(None)
        ).scalar() or 0
        
    if previous_resp_time == 0:
        previous_resp_time = db.query(
            func.avg(LLMInteraction.duration_ms)
        ).join(Event).filter(
            Event.agent_id == agent_id,
            Event.timestamp >= previous_period.start,
            Event.timestamp <= previous_period.end,
            LLMInteraction.duration_ms.isnot(None)
        ).scalar() or 0
    
    resp_time_change = calculate_percent_change(previous_resp_time, current_resp_time)
    metrics.append(MetricSummary(
        metric="avg_response_time",
        value=current_resp_time,
        change=resp_time_change,
        trend="up" if resp_time_change > 0 else "down" if resp_time_change < 0 else "flat"
    ))
    
    # Tool Usage
    current_tool_count = db.query(func.count(Event.id)).join(ToolInteraction).filter(
        Event.agent_id == agent_id,
        Event.timestamp >= current_period.start,
        Event.timestamp <= current_period.end
    ).scalar() or 0
    
    previous_tool_count = db.query(func.count(Event.id)).join(ToolInteraction).filter(
        Event.agent_id == agent_id,
        Event.timestamp >= previous_period.start,
        Event.timestamp <= previous_period.end
    ).scalar() or 0
    
    tool_change = calculate_percent_change(previous_tool_count, current_tool_count)
    metrics.append(MetricSummary(
        metric="tool_execution_count",
        value=current_tool_count,
        change=tool_change,
        trend="up" if tool_change > 0 else "down" if tool_change < 0 else "flat"
    ))
    
    # Error Count
    current_error_count = db.query(func.count(Event.id)).filter(
        Event.agent_id == agent_id,
        Event.level == "error",
        Event.timestamp >= current_period.start,
        Event.timestamp <= current_period.end
    ).scalar() or 0
    
    previous_error_count = db.query(func.count(Event.id)).filter(
        Event.agent_id == agent_id,
        Event.level == "error",
        Event.timestamp >= previous_period.start,
        Event.timestamp <= previous_period.end
    ).scalar() or 0
    
    error_change = calculate_percent_change(previous_error_count, current_error_count)
    metrics.append(MetricSummary(
        metric="error_count",
        value=current_error_count,
        change=error_change,
        trend="up" if error_change > 0 else "down" if error_change < 0 else "flat"
    ))
    
    return metrics


def get_agent_llm_usage(
    db: Session, 
    agent_id: str,
    time_range_params: TimeRangeParams
) -> Dict[str, Any]:
    """
    Get LLM usage overview for a specific agent.
    
    Args:
        db: Database session
        agent_id: Agent ID
        time_range_params: Time range parameters
        
    Returns:
        Dict: LLM usage information
    """
    # Add debug logging to trace function execution
    logger.debug(f"Inside get_agent_llm_usage function, agent_id={agent_id}, time_range={time_range_params}")
    
    # Check if agent exists
    agent = db.query(Agent).filter(Agent.agent_id == agent_id).first()
    if not agent:
        logger.debug(f"Agent with ID {agent_id} not found")
        return {"items": [], "total_requests": 0, "total_tokens": 0, "total_cost": 0.0}
    
    # Query LLM interactions for this agent within the time range
    query = db.query(
        LLMInteraction.model,
        LLMInteraction.vendor,
        func.count(LLMInteraction.id).label("request_count"),
        func.sum(LLMInteraction.input_tokens).label("input_tokens"),
        func.sum(LLMInteraction.output_tokens).label("output_tokens")
    ).join(Event).filter(
        Event.agent_id == agent_id,
        Event.timestamp >= time_range_params.start,
        Event.timestamp <= time_range_params.end
    ).group_by(
        LLMInteraction.model,
        LLMInteraction.vendor
    )
    
    llm_usage = query.all()
    
    # Import pricing service
    from src.services.pricing_service import pricing_service
    
    # Prepare result items
    items = []
    total_requests = 0
    total_tokens = 0
    total_cost = 0.0
    
    for usage in llm_usage:
        model = usage.model or "unknown"
        vendor = usage.vendor or "unknown"
        request_count = usage.request_count or 0
        input_tokens = usage.input_tokens or 0
        output_tokens = usage.output_tokens or 0
        total_tokens_model = input_tokens + output_tokens
        
        # Skip models with 0 tokens usage
        if total_tokens_model == 0:
            continue
        
        # Calculate cost using pricing_service instead of hardcoded values
        cost_result = pricing_service.calculate_cost(input_tokens, output_tokens, model, vendor)
        estimated_cost = cost_result["total_cost"]
        
        items.append({
            "model": model,
            "vendor": vendor,
            "request_count": request_count,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens_model,
            "estimated_cost": round(estimated_cost, 3)
        })
        
        total_requests += request_count
        total_tokens += total_tokens_model
        total_cost += estimated_cost
    
    # Add debug log at the end
    logger.debug(f"Returning LLM usage data for agent {agent_id} with {len(items)} models and {total_requests} total requests")
    
    return {
        "items": items,
        "total_requests": total_requests,
        "total_tokens": total_tokens,
        "total_cost": round(total_cost, 3)
    }


def get_agent_llm_requests(
    db: Session,
    agent_id: str,
    time_range_params: TimeRangeParams,
    filters: Dict[str, Any],
    pagination_params: PaginationParams
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Get detailed LLM requests for a specific agent.
    
    Args:
        db: Database session
        agent_id: Agent ID
        time_range_params: Time range parameters
        filters: Additional filters
        pagination_params: Pagination parameters
        
    Returns:
        Tuple[List[Dict], int]: List of LLM requests and total count
    """
    # Check if agent exists
    agent = db.query(Agent).filter(Agent.agent_id == agent_id).first()
    if not agent:
        return [], 0
    
    # Start with base query
    query = db.query(Event).join(LLMInteraction).filter(
        Event.agent_id == agent_id,
        Event.timestamp >= time_range_params.start,
        Event.timestamp <= time_range_params.end
    )
    
    # Apply additional filters
    if "model" in filters and filters["model"]:
        query = query.filter(LLMInteraction.model == filters["model"])
        
    if "status" in filters and filters["status"]:
        if filters["status"].lower() == "error":
            query = query.filter(LLMInteraction.stop_reason.isnot(None))
        elif filters["status"].lower() == "success":
            query = query.filter(LLMInteraction.stop_reason.is_(None))
    
    # Count total matching records
    total = query.count()
    
    # Apply pagination
    query = query.order_by(Event.timestamp.desc())
    query = query.offset(pagination_params.offset).limit(pagination_params.limit)
    
    # Execute query
    events = query.all()
    
    # Prepare result items
    items = []
    for event in events:
        llm = event.llm_interaction
        if not llm:
            continue
            
        # Extract prompt and response summaries
        prompt_summary = ""
        response_summary = ""
        
        if llm.request_data and isinstance(llm.request_data, dict):
            # Extract from request_data
            messages = llm.request_data.get("messages", [])
            if messages and isinstance(messages, list) and len(messages) > 0:
                # Get last message content for prompt summary
                last_msg = messages[-1]
                if isinstance(last_msg, dict) and "content" in last_msg:
                    prompt_content = last_msg.get("content", "")
                    if prompt_content:
                        prompt_summary = prompt_content[:100] + "..." if len(prompt_content) > 100 else prompt_content
            
            # If no messages, try other request data formats
            if not prompt_summary and "prompt" in llm.request_data:
                prompt = llm.request_data.get("prompt", "")
                if prompt:
                    prompt_summary = prompt[:100] + "..." if len(prompt) > 100 else prompt
        
        # Extract response summary from response_content
        if llm.response_content:
            if isinstance(llm.response_content, dict):
                # Try to get content from various response formats
                if "choices" in llm.response_content:
                    choices = llm.response_content.get("choices", [])
                    if choices and isinstance(choices, list) and len(choices) > 0:
                        first_choice = choices[0]
                        if isinstance(first_choice, dict):
                            if "message" in first_choice:
                                msg = first_choice.get("message", {})
                                if isinstance(msg, dict) and "content" in msg:
                                    content = msg.get("content", "")
                                    response_summary = content[:100] + "..." if len(content) > 100 else content
                            elif "text" in first_choice:
                                text = first_choice.get("text", "")
                                response_summary = text[:100] + "..." if len(text) > 100 else text
                elif "content" in llm.response_content:
                    # Direct content field
                    content = llm.response_content.get("content", "")
                    response_summary = content[:100] + "..." if len(content) > 100 else content
            elif isinstance(llm.response_content, str):
                response_summary = llm.response_content[:100] + "..." if len(llm.response_content) > 100 else llm.response_content
        
        # If we still have no summaries, try the event raw_data as fallback
        if (not prompt_summary or not response_summary) and event.raw_data and isinstance(event.raw_data, dict):
            data = event.raw_data.get("data", {})
            if isinstance(data, dict):
                # Get prompt summary (first 100 chars)
                if not prompt_summary:
                    prompt = data.get("prompt", "")
                    if isinstance(prompt, str) and prompt:
                        prompt_summary = prompt[:100] + "..." if len(prompt) > 100 else prompt
                
                # Get response summary (first 100 chars)
                if not response_summary:
                    response = data.get("response", "")
                    if isinstance(response, str) and response:
                        response_summary = response[:100] + "..." if len(response) > 100 else response
        
        # Ensure prompt_summary and response_summary are strings
        # Convert non-string values to their string representation
        if not isinstance(prompt_summary, str):
            if prompt_summary:
                try:
                    # Try to convert to JSON string or use string representation
                    import json
                    prompt_summary = json.dumps(prompt_summary)[:100] + "..." if len(json.dumps(prompt_summary)) > 100 else json.dumps(prompt_summary)
                except:
                    prompt_summary = str(prompt_summary)[:100] + "..." if len(str(prompt_summary)) > 100 else str(prompt_summary)
            else:
                prompt_summary = ""

        if not isinstance(response_summary, str):
            if response_summary:
                try:
                    # Try to convert to JSON string or use string representation
                    import json
                    response_summary = json.dumps(response_summary)[:100] + "..." if len(json.dumps(response_summary)) > 100 else json.dumps(response_summary)
                except:
                    response_summary = str(response_summary)[:100] + "..." if len(str(response_summary)) > 100 else str(response_summary)
            else:
                response_summary = ""

        # Also handle stop_reason to make sure it's a string
        stop_reason_msg = ""
        if llm.stop_reason:
            if not isinstance(llm.stop_reason, str):
                try:
                    stop_reason_msg = json.dumps(llm.stop_reason)
                except:
                    stop_reason_msg = str(llm.stop_reason)
            else:
                stop_reason_msg = llm.stop_reason

        # Update the final items.append with the guaranteed string values
        items.append({
            "request_id": str(event.id),
            "timestamp": event.timestamp,
            "model": llm.model or "unknown",
            "status": "error" if llm.stop_reason and "error" in (llm.stop_reason or "").lower() else "success",
            "input_tokens": llm.input_tokens or 0,
            "output_tokens": llm.output_tokens or 0,
            "duration_ms": llm.duration_ms or 0,
            "prompt_summary": prompt_summary,
            "response_summary": response_summary if (not llm.stop_reason or "error" not in (llm.stop_reason or "").lower()) else stop_reason_msg
        })
    
    return items, total


def get_agent_token_usage(
    db: Session,
    agent_id: str,
    time_range_params: TimeRangeParams,
    group_by: Optional[str] = None,
    interval: Optional[str] = None,
    pagination_params: Optional[PaginationParams] = None
) -> Dict[str, Any]:
    """
    Get token usage metrics for a specific agent.
    
    Args:
        db: Database session
        agent_id: Agent ID
        time_range_params: Time range parameters
        group_by: Field to group by (model, time)
        interval: Time interval for grouping (1h, 1d)
        pagination_params: Pagination parameters
        
    Returns:
        Dict: Token usage metrics
    """
    # Check if agent exists
    agent = db.query(Agent).filter(Agent.agent_id == agent_id).first()
    if not agent:
        return {
            "items": [],
            "total_input": 0,
            "total_output": 0,
            "total": 0
        }
    
    # Get total token counts for the time period
    total_query = db.query(
        func.sum(LLMInteraction.input_tokens).label("input_tokens"),
        func.sum(LLMInteraction.output_tokens).label("output_tokens")
    ).join(Event).filter(
        Event.agent_id == agent_id,
        Event.timestamp >= time_range_params.start,
        Event.timestamp <= time_range_params.end
    )
    
    total_result = total_query.first()
    total_input = total_result.input_tokens or 0
    total_output = total_result.output_tokens or 0
    total_tokens = total_input + total_output
    
    # Prepare items based on grouping
    items = []
    
    if group_by == "model":
        # Group by model
        model_query = db.query(
            LLMInteraction.model,
            func.sum(LLMInteraction.input_tokens).label("input_tokens"),
            func.sum(LLMInteraction.output_tokens).label("output_tokens")
        ).join(Event).filter(
            Event.agent_id == agent_id,
            Event.timestamp >= time_range_params.start,
            Event.timestamp <= time_range_params.end
        ).group_by(
            LLMInteraction.model
        )
        
        for result in model_query.all():
            model = result.model or "unknown"
            input_tokens = result.input_tokens or 0
            output_tokens = result.output_tokens or 0
            
            items.append({
                "timestamp": time_range_params.end,
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens
            })
    else:
        # Group by time - default to daily if not specified
        interval_seconds = 86400  # Default to daily (1d)
        if interval == "1h":
            interval_seconds = 3600
        
        # Calculate number of intervals
        time_diff = (time_range_params.end - time_range_params.start).total_seconds()
        num_intervals = int(time_diff / interval_seconds) + 1
        
        # Get token usage aggregated by time interval
        if interval == "1h":
            # Group by hour (SQLite compatible)
            time_query = db.query(
                func.strftime('%Y-%m-%d %H:00:00', Event.timestamp).label("interval_time"),
                func.sum(LLMInteraction.input_tokens).label("input_tokens"),
                func.sum(LLMInteraction.output_tokens).label("output_tokens")
            ).join(Event).filter(
                Event.agent_id == agent_id,
                Event.timestamp >= time_range_params.start,
                Event.timestamp <= time_range_params.end
            ).group_by(
                func.strftime('%Y-%m-%d %H:00:00', Event.timestamp)
            ).order_by(
                func.strftime('%Y-%m-%d %H:00:00', Event.timestamp).desc()
            )
        else:
            # Group by day (SQLite compatible)
            time_query = db.query(
                func.strftime('%Y-%m-%d 00:00:00', Event.timestamp).label("interval_time"),
                func.sum(LLMInteraction.input_tokens).label("input_tokens"),
                func.sum(LLMInteraction.output_tokens).label("output_tokens")
            ).join(Event).filter(
                Event.agent_id == agent_id,
                Event.timestamp >= time_range_params.start,
                Event.timestamp <= time_range_params.end
            ).group_by(
                func.strftime('%Y-%m-%d 00:00:00', Event.timestamp)
            ).order_by(
                func.strftime('%Y-%m-%d 00:00:00', Event.timestamp).desc()
            )
        
        # Apply pagination if needed
        if pagination_params:
            time_query = time_query.offset(pagination_params.offset).limit(pagination_params.limit)
        elif num_intervals > 100:  # Limit to 100 data points by default
            time_query = time_query.limit(100)
        
        # Build time series data
        interval_data = {}
        for result in time_query.all():
            # Convert string timestamp to datetime object
            if isinstance(result.interval_time, str):
                interval_time = datetime.strptime(result.interval_time, '%Y-%m-%d %H:%M:%S')
            else:
                interval_time = result.interval_time
                
            input_tokens = result.input_tokens or 0
            output_tokens = result.output_tokens or 0
            
            interval_data[interval_time] = {
                "timestamp": interval_time,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens
            }
        
        # Fill in missing intervals with zeros
        current_time = time_range_params.end
        for _ in range(num_intervals):
            if interval == "1h":
                interval_time = datetime(
                    current_time.year, current_time.month, current_time.day,
                    current_time.hour, 0, 0
                )
            else:
                interval_time = datetime(
                    current_time.year, current_time.month, current_time.day,
                    0, 0, 0
                )
            
            if interval_time not in interval_data and interval_time >= time_range_params.start:
                interval_data[interval_time] = {
                    "timestamp": interval_time,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0
                }
            
            if interval == "1h":
                current_time -= timedelta(hours=1)
            else:
                current_time -= timedelta(days=1)
        
        # Convert to sorted list
        items = list(interval_data.values())
        items.sort(key=lambda x: x["timestamp"], reverse=True)
    
    return {
        "items": items,
        "total_input": total_input,
        "total_output": total_output,
        "total": total_tokens
    }


def get_agent_tool_usage(
    db: Session,
    agent_id: str,
    time_range_params: TimeRangeParams,
    category: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get tool usage overview for a specific agent.
    
    Args:
        db: Database session
        agent_id: Agent ID
        time_range_params: Time range parameters
        category: Filter by tool category
        
    Returns:
        Dict: Tool usage information
    """
    # Check if agent exists
    agent = db.query(Agent).filter(Agent.agent_id == agent_id).first()
    if not agent:
        return {"items": [], "total_executions": 0, "overall_success_rate": 0.0}
    
    # Base query to get tool usage
    query = db.query(
        ToolInteraction.tool_name,
        ToolInteraction.framework_name,
        func.count(ToolInteraction.id).label("execution_count"),
        func.sum(case([(ToolInteraction.error.is_(None), 1)], else_=0)).label("success_count"),
        func.avg(ToolInteraction.duration_ms).label("avg_duration_ms")
    ).join(Event).filter(
        Event.agent_id == agent_id,
        Event.timestamp >= time_range_params.start,
        Event.timestamp <= time_range_params.end
    )
    
    # Apply category filter if provided
    if category:
        query = query.filter(ToolInteraction.framework_name == category)
    
    # Group by tool name and framework name instead of category
    query = query.group_by(
        ToolInteraction.tool_name,
        ToolInteraction.framework_name
    )
    
    # Execute query
    results = query.all()
    
    # Prepare items
    items = []
    total_executions = 0
    total_success = 0
    
    for result in results:
        tool_name = result.tool_name or "unknown"
        # Use framework_name as category
        category = result.framework_name or "other"
        execution_count = result.execution_count or 0
        success_count = result.success_count or 0
        error_count = execution_count - success_count
        success_rate = success_count / execution_count if execution_count > 0 else 0.0
        avg_duration_ms = int(result.avg_duration_ms or 0)
        
        items.append({
            "tool_name": tool_name,
            "category": category,
            "execution_count": execution_count,
            "success_count": success_count,
            "error_count": error_count,
            "success_rate": round(success_rate, 3),
            "avg_duration_ms": avg_duration_ms
        })
        
        total_executions += execution_count
        total_success += success_count
    
    # Calculate overall success rate
    overall_success_rate = total_success / total_executions if total_executions > 0 else 0.0
    
    return {
        "items": items,
        "total_executions": total_executions,
        "overall_success_rate": round(overall_success_rate, 3)
    }


def get_agent_tool_executions(
    db: Session,
    agent_id: str,
    time_range_params: TimeRangeParams,
    filters: Dict[str, Any],
    pagination_params: PaginationParams
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Get detailed tool executions for a specific agent.
    
    Args:
        db: Database session
        agent_id: Agent ID
        time_range_params: Time range parameters
        filters: Additional filters
        pagination_params: Pagination parameters
        
    Returns:
        Tuple[List[Dict], int]: List of tool executions and total count
    """
    # Check if agent exists
    agent = db.query(Agent).filter(Agent.agent_id == agent_id).first()
    if not agent:
        return [], 0
    
    # Start with base query
    query = db.query(Event).join(ToolInteraction).filter(
        Event.agent_id == agent_id,
        Event.timestamp >= time_range_params.start,
        Event.timestamp <= time_range_params.end
    )
    
    # Apply additional filters
    if "tool_name" in filters and filters["tool_name"]:
        query = query.filter(ToolInteraction.tool_name == filters["tool_name"])
        
    if "status" in filters and filters["status"]:
        if filters["status"].lower() == "error":
            query = query.filter(ToolInteraction.error.isnot(None))
        elif filters["status"].lower() == "success":
            query = query.filter(ToolInteraction.error.is_(None))
    
    # Count total matching records
    total = query.count()
    
    # Apply pagination
    query = query.order_by(Event.timestamp.desc())
    query = query.offset(pagination_params.offset).limit(pagination_params.limit)
    
    # Execute query
    events = query.all()
    
    # Prepare result items
    items = []
    for event in events:
        tool = event.tool_interaction
        if not tool:
            continue
        
        # Extract parameters and result summaries
        parameters = {}
        result_summary = ""
        
        if event.raw_data and isinstance(event.raw_data, dict):
            data = event.raw_data.get("data", {})
            if isinstance(data, dict):
                # Get parameters
                params = data.get("parameters", {})
                if isinstance(params, dict):
                    parameters = params
                
                # Get result summary
                result = data.get("result", "")
                if result:
                    if isinstance(result, str):
                        result_summary = result[:100] + "..." if len(result) > 100 else result
                    elif isinstance(result, dict):
                        result_summary = str(result)[:100] + "..." if len(str(result)) > 100 else str(result)
        
        items.append({
            "execution_id": str(event.id),
            "timestamp": event.timestamp,
            "tool_name": tool.tool_name or "unknown",
            "status": "error" if tool.error else "success",
            "duration_ms": int(tool.duration_ms or 0),
            "parameters": parameters,
            "result_summary": result_summary if not tool.error else tool.error
        })
    
    return items, total


def calculate_percent_change(previous: float, current: float) -> float:
    """
    Calculate percent change between two values.
    
    Args:
        previous: Previous value
        current: Current value
        
    Returns:
        float: Percent change, rounded to 1 decimal place
    """
    if previous == 0:
        return 100.0 if current > 0 else 0.0
        
    change = ((current - previous) / previous) * 100
    return round(change, 1)


def case(whens, else_=None):
    """
    Helper function to create a SQL CASE expression.
    
    Args:
        whens: List of conditions and values
        else_: Value for the ELSE clause
        
    Returns:
        A SQL CASE expression
    """
    case_stmt = "CASE "
    for condition, value in whens:
        case_stmt += f"WHEN {condition} THEN {value} "
    if else_ is not None:
        case_stmt += f"ELSE {else_} "
    case_stmt += "END"
    return text(case_stmt)


def get_agent_sessions(
    db: Session,
    agent_id: str,
    time_range_params: TimeRangeParams,
    filters: Dict[str, Any],
    pagination_params: PaginationParams
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Get sessions for a specific agent.
    
    Args:
        db: Database session
        agent_id: Agent ID
        time_range_params: Time range parameters
        filters: Additional filters
        pagination_params: Pagination parameters
        
    Returns:
        Tuple[List[Dict], int]: List of sessions and total count
    """
    # Check if agent exists
    agent = db.query(Agent).filter(Agent.agent_id == agent_id).first()
    if not agent:
        return [], 0
    
    # Start with base query for sessions
    query = db.query(SessionModel).filter(
        SessionModel.agent_id == agent_id,
        SessionModel.start_timestamp >= time_range_params.start,
        SessionModel.start_timestamp <= time_range_params.end
    )
    
    # Apply additional filters
    if "status" in filters and filters["status"]:
        if filters["status"].lower() == "active":
            query = query.filter(SessionModel.end_timestamp.is_(None))
        elif filters["status"].lower() == "completed":
            query = query.filter(SessionModel.end_timestamp.isnot(None))
    
    if "min_duration" in filters and filters["min_duration"] is not None:
        # For active sessions, use current time to calculate duration
        min_duration = filters["min_duration"]
        current_time = datetime.utcnow()
        
        duration_filter = or_(
            # Completed sessions
            and_(
                SessionModel.end_timestamp.isnot(None),
                (func.extract('epoch', SessionModel.end_timestamp) - 
                 func.extract('epoch', SessionModel.start_timestamp)) >= min_duration
            ),
            # Active sessions
            and_(
                SessionModel.end_timestamp.is_(None),
                (func.extract('epoch', func.now()) - 
                 func.extract('epoch', SessionModel.start_timestamp)) >= min_duration
            )
        )
        query = query.filter(duration_filter)
    
    if "max_duration" in filters and filters["max_duration"] is not None:
        # For active sessions, use current time to calculate duration
        max_duration = filters["max_duration"]
        
        duration_filter = or_(
            # Completed sessions
            and_(
                SessionModel.end_timestamp.isnot(None),
                (func.extract('epoch', SessionModel.end_timestamp) - 
                 func.extract('epoch', SessionModel.start_timestamp)) <= max_duration
            ),
            # Active sessions
            and_(
                SessionModel.end_timestamp.is_(None),
                (func.extract('epoch', func.now()) - 
                 func.extract('epoch', SessionModel.start_timestamp)) <= max_duration
            )
        )
        query = query.filter(duration_filter)
    
    # Count total matching records
    total = query.count()
    
    # Apply pagination
    query = query.order_by(SessionModel.start_timestamp.desc())
    query = query.offset(pagination_params.offset).limit(pagination_params.limit)
    
    # Execute query
    sessions = query.all()
    
    # Prepare result items
    items = []
    for session in sessions:
        # Calculate duration
        duration_seconds = None
        if session.end_timestamp:
            duration_seconds = int((session.end_timestamp - session.start_timestamp).total_seconds())
        
        # Count events in this session
        event_count = db.query(func.count(Event.id)).filter(
            Event.session_id == session.session_id
        ).scalar() or 0
        
        # Count LLM requests
        llm_request_count = db.query(func.count(Event.id)).join(LLMInteraction).filter(
            Event.session_id == session.session_id
        ).scalar() or 0
        
        # Count tool executions
        tool_execution_count = db.query(func.count(Event.id)).join(ToolInteraction).filter(
            Event.session_id == session.session_id
        ).scalar() or 0
        
        # Count errors
        error_count = db.query(func.count(Event.id)).filter(
            Event.session_id == session.session_id,
            Event.level == "error"
        ).scalar() or 0
        
        # Determine session status
        status = "active"
        if session.end_timestamp:
            # Check for errors to determine if it was terminated or completed
            if error_count > 0:
                status = "errored"
            else:
                status = "completed"
        
        items.append({
            "session_id": session.session_id,
            "start_time": session.start_timestamp,
            "end_time": session.end_timestamp,
            "duration_seconds": duration_seconds,
            "event_count": event_count,
            "llm_request_count": llm_request_count,
            "tool_execution_count": tool_execution_count,
            "error_count": error_count,
            "status": status
        })
    
    return items, total


def get_agent_traces(
    db: Session,
    agent_id: str,
    time_range_params: TimeRangeParams,
    filters: Dict[str, Any],
    pagination_params: PaginationParams
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Get execution traces for a specific agent.
    
    Args:
        db: Database session
        agent_id: Agent ID
        time_range_params: Time range parameters
        filters: Additional filters
        pagination_params: Pagination parameters
        
    Returns:
        Tuple[List[Dict], int]: List of traces and total count
    """
    # Check if agent exists
    agent = db.query(Agent).filter(Agent.agent_id == agent_id).first()
    if not agent:
        return [], 0
    
    # Start with base query for traces - include NULL timestamps
    query = db.query(Trace).filter(
        Trace.agent_id == agent_id
    )
    
    # If timestamps are not NULL, apply time range filters
    timestamp_filter = or_(
        Trace.start_timestamp.is_(None),  # Include traces with NULL timestamps
        and_(
            Trace.start_timestamp >= time_range_params.start,
            Trace.start_timestamp <= time_range_params.end
        )
    )
    query = query.filter(timestamp_filter)
    
    # Apply additional filters
    if "status" in filters and filters["status"]:
        if filters["status"].lower() == "active":
            query = query.filter(Trace.end_timestamp.is_(None))
        elif filters["status"].lower() == "completed":
            query = query.filter(Trace.end_timestamp.isnot(None))
    
    if "min_duration" in filters and filters["min_duration"] is not None:
        # For active traces, use current time to calculate duration
        min_duration_ms = filters["min_duration"]
        current_time = datetime.utcnow()
        
        duration_filter = or_(
            # Completed traces
            and_(
                Trace.end_timestamp.isnot(None),
                (func.extract('epoch', Trace.end_timestamp) - 
                 func.extract('epoch', Trace.start_timestamp)) * 1000 >= min_duration_ms
            ),
            # Active traces
            and_(
                Trace.end_timestamp.is_(None),
                (func.extract('epoch', func.now()) - 
                 func.extract('epoch', Trace.start_timestamp)) * 1000 >= min_duration_ms
            )
        )
        query = query.filter(duration_filter)
    
    if "max_duration" in filters and filters["max_duration"] is not None:
        # For active traces, use current time to calculate duration
        max_duration_ms = filters["max_duration"]
        
        duration_filter = or_(
            # Completed traces
            and_(
                Trace.end_timestamp.isnot(None),
                (func.extract('epoch', Trace.end_timestamp) - 
                 func.extract('epoch', Trace.start_timestamp)) * 1000 <= max_duration_ms
            ),
            # Active traces
            and_(
                Trace.end_timestamp.is_(None),
                (func.extract('epoch', func.now()) - 
                 func.extract('epoch', Trace.start_timestamp)) * 1000 <= max_duration_ms
            )
        )
        query = query.filter(duration_filter)
    
    # Count total matching records
    total = query.count()
    
    # Apply pagination
    query = query.order_by(Trace.start_timestamp.desc())
    query = query.offset(pagination_params.offset).limit(pagination_params.limit)
    
    # Execute query
    traces = query.all()
    
    # Prepare result items
    items = []
    for trace in traces:
        # Provide default datetime for NULL timestamps
        # The model requires a valid datetime, not None
        start_time = trace.start_timestamp or datetime.utcnow()
        end_time = trace.end_timestamp
        
        # Calculate duration in milliseconds
        duration_ms = None
        if trace.end_timestamp:
            duration_ms = int((trace.end_timestamp - start_time).total_seconds() * 1000)
        
        # Count events in this trace
        event_count = db.query(func.count(Event.id)).filter(
            Event.trace_id == trace.trace_id
        ).scalar() or 0
        
        # Determine trace status
        status = "active"
        if trace.end_timestamp:
            # Check for errors to determine if it was errored or completed
            error_count = db.query(func.count(Event.id)).filter(
                Event.trace_id == trace.trace_id,
                Event.level == "error"
            ).scalar() or 0
            
            if error_count > 0:
                status = "errored"
            else:
                status = "completed"
        
        # Determine initial event type
        initial_event = db.query(Event).filter(
            Event.trace_id == trace.trace_id
        ).order_by(Event.timestamp.asc()).first()
        
        initial_event_type = "unknown"
        if initial_event:
            event_name = initial_event.name
            if event_name.startswith("llm."):
                initial_event_type = "llm_request"
            elif event_name.startswith("tool."):
                initial_event_type = "tool_execution"
            elif event_name.startswith("user."):
                initial_event_type = "user_input"
            elif event_name.startswith("agent."):
                initial_event_type = "agent_response"
        
        items.append({
            "trace_id": trace.trace_id,
            "start_time": start_time,
            "end_time": end_time,
            "duration_ms": duration_ms,
            "event_count": event_count,
            "status": status,
            "initial_event_type": initial_event_type
        })
    
    return items, total


def get_agent_alerts(
    db: Session,
    agent_id: str,
    time_range_params: TimeRangeParams,
    filters: Dict[str, Any],
    pagination_params: PaginationParams
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Get security alerts for a specific agent.
    
    Args:
        db: Database session
        agent_id: Agent ID
        time_range_params: Time range parameters
        filters: Additional filters
        pagination_params: Pagination parameters
        
    Returns:
        Tuple[List[Dict], int]: List of alerts and total count
    """
    # Check if agent exists
    agent = db.query(Agent).filter(Agent.agent_id == agent_id).first()
    if not agent:
        return [], 0
    
    # Start with base query for security alerts
    query = db.query(Event).join(SecurityAlert).filter(
        Event.agent_id == agent_id,
        Event.timestamp >= time_range_params.start,
        Event.timestamp <= time_range_params.end
    )
    
    # Apply additional filters
    if "type" in filters and filters["type"]:
        query = query.filter(SecurityAlert.category == filters["type"])
        
    if "severity" in filters and filters["severity"]:
        query = query.filter(SecurityAlert.severity == filters["severity"])
        
    if "status" in filters and filters["status"]:
        query = query.filter(SecurityAlert.status == filters["status"])
    
    # Count total matching records
    total = query.count()
    
    # Apply pagination
    query = query.order_by(Event.timestamp.desc())
    query = query.offset(pagination_params.offset).limit(pagination_params.limit)
    
    # Execute query
    events = query.all()
    
    # Prepare result items
    items = []
    for event in events:
        alert = event.security_alert
        if not alert:
            continue
        
        items.append({
            "alert_id": str(event.id),
            "timestamp": event.timestamp,
            "type": alert.category or "unknown",
            "severity": alert.severity or "medium",
            "description": alert.description or f"Security alert: {event.name}",
            "status": alert.status or "open",
            "related_event_id": str(event.id)
        })
    
    return items, total 