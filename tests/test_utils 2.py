"""
Test utilities for Cylestio Local Server tests.

This module provides utility functions for test data generation,
validation, and common testing operations.
"""
import datetime
import json
import os
import random
import time
import uuid
from typing import Dict, Any, List, Tuple, Optional

import pytest
import psutil
from sqlalchemy import func
from sqlalchemy.orm import Session

from src.models.agent import Agent
from src.models.event import Event
from src.models.framework_event import FrameworkEvent
from src.models.llm_interaction import LLMInteraction
from src.models.security_alert import SecurityAlert
from src.models.session import Session as SessionModel
from src.models.span import Span
from src.models.tool_interaction import ToolInteraction
from src.models.trace import Trace


# --- Test Data Generators ---

def generate_agent(db_session: Session, agent_id: str = None) -> Agent:
    """Create and return a test agent."""
    if agent_id is None:
        agent_id = f"test-agent-{uuid.uuid4()}"
    
    agent = Agent(
        agent_id=agent_id,
        name=f"Test Agent {agent_id}",
        first_seen=datetime.datetime.utcnow(),
        last_seen=datetime.datetime.utcnow(),
        is_active=True
    )
    db_session.add(agent)
    db_session.commit()
    return agent


def generate_event(db_session: Session, agent: Agent = None, 
                  event_name: str = "test.event", 
                  event_type: str = "test") -> Event:
    """Create and return a test event."""
    if agent is None:
        agent = generate_agent(db_session)
        
    event = Event(
        agent_id=agent.id,
        timestamp=datetime.datetime.utcnow(),
        schema_version="1.0",
        name=event_name,
        level="INFO",
        event_type=event_type
    )
    db_session.add(event)
    db_session.commit()
    return event


def generate_llm_interaction_data(interaction_type: str = "start") -> Dict[str, Any]:
    """Generate test data for LLM interaction."""
    data = {
        "attributes": {
            "llm.vendor": "anthropic",
            "llm.model": "claude-3-haiku-20240307",
            "llm.request.timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        }
    }
    
    if interaction_type == "start":
        data["attributes"]["llm.request.data"] = {
            "messages": [{"role": "user", "content": "Hello world"}]
        }
        data["attributes"]["llm.config.temperature"] = 0.7
        data["attributes"]["llm.config.max_tokens"] = 1000
    
    if interaction_type == "finish":
        data["attributes"]["llm.response.timestamp"] = datetime.datetime.utcnow().isoformat() + "Z"
        data["attributes"]["llm.response.duration_ms"] = 450
        data["attributes"]["llm.usage.input_tokens"] = 15
        data["attributes"]["llm.usage.output_tokens"] = 45
        data["attributes"]["llm.usage.total_tokens"] = 60
        data["attributes"]["llm.response.content"] = {"type": "text", "text": "Hello, human!"}
        data["attributes"]["llm.response.id"] = f"resp_{uuid.uuid4()}"
        data["attributes"]["llm.response.stop_reason"] = "end_turn"
    
    return data


def generate_security_alert_data() -> Dict[str, Any]:
    """Generate test data for security alert."""
    return {
        "attributes": {
            "security.alert.type": "content_policy_violation",
            "security.alert.severity": "medium",
            "security.alert.details": {
                "policy": "harmful_content",
                "score": 0.85,
                "flagged_content": "This is potentially harmful content"
            },
            "security.alert.source": "content_filter",
            "security.alert.timestamp": datetime.datetime.utcnow().isoformat() + "Z"
        }
    }


def generate_framework_event_data(framework_type: str = "langchain") -> Dict[str, Any]:
    """Generate test data for framework event."""
    data = {
        "attributes": {
            "framework.type": framework_type,
            "framework.version": "0.1.0",
        }
    }
    
    if framework_type == "langchain":
        data["attributes"]["framework.langchain.component_type"] = "Chain"
        data["attributes"]["framework.langchain.component_name"] = "TestChain"
    elif framework_type == "llamaindex":
        data["attributes"]["framework.llamaindex.module"] = "Retriever"
        data["attributes"]["framework.llamaindex.class"] = "TestRetriever"
    
    return data


def generate_tool_interaction_data(interaction_type: str = "start") -> Dict[str, Any]:
    """Generate test data for tool interaction."""
    data = {
        "attributes": {
            "tool.name": "weather_api",
            "tool.description": "Get current weather for a location",
            "tool.timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        }
    }
    
    if interaction_type == "start":
        data["attributes"]["tool.input"] = {"location": "San Francisco, CA"}
    
    if interaction_type == "finish":
        data["attributes"]["tool.output"] = {"temperature": 72, "conditions": "sunny"}
        data["attributes"]["tool.duration_ms"] = 350
        data["attributes"]["tool.status"] = "success"
    
    return data


def generate_span_data(is_root: bool = False) -> Dict[str, Any]:
    """Generate test data for span."""
    span_id = str(uuid.uuid4())
    data = {
        "attributes": {
            "span.id": span_id,
            "span.name": "test_span",
            "span.start_time": datetime.datetime.utcnow().isoformat() + "Z",
        }
    }
    
    if not is_root:
        data["attributes"]["span.parent_id"] = str(uuid.uuid4())
    
    return data, span_id


def generate_session_data() -> Dict[str, Any]:
    """Generate test data for session."""
    session_id = str(uuid.uuid4())
    data = {
        "attributes": {
            "session.id": session_id,
            "session.name": "test_session",
            "session.start_time": datetime.datetime.utcnow().isoformat() + "Z",
        }
    }
    
    return data, session_id


# --- Test Validation Helpers ---

def verify_database_state(db_session: Session, expected_counts: Dict[str, int]) -> Dict[str, bool]:
    """Verify the database contains the expected number of records."""
    results = {}
    
    if "events" in expected_counts:
        count = db_session.query(func.count(Event.id)).scalar()
        results["events"] = count == expected_counts["events"]
    
    if "llm_interactions" in expected_counts:
        count = db_session.query(func.count(LLMInteraction.id)).scalar()
        results["llm_interactions"] = count == expected_counts["llm_interactions"]
    
    if "security_alerts" in expected_counts:
        count = db_session.query(func.count(SecurityAlert.id)).scalar()
        results["security_alerts"] = count == expected_counts["security_alerts"]
    
    if "framework_events" in expected_counts:
        count = db_session.query(func.count(FrameworkEvent.id)).scalar()
        results["framework_events"] = count == expected_counts["framework_events"]
    
    if "tool_interactions" in expected_counts:
        count = db_session.query(func.count(ToolInteraction.id)).scalar()
        results["tool_interactions"] = count == expected_counts["tool_interactions"]
    
    if "sessions" in expected_counts:
        count = db_session.query(func.count(SessionModel.id)).scalar()
        results["sessions"] = count == expected_counts["sessions"]
    
    if "spans" in expected_counts:
        count = db_session.query(func.count(Span.span_id)).scalar()
        results["spans"] = count == expected_counts["spans"]
    
    if "traces" in expected_counts:
        count = db_session.query(func.count(Trace.id)).scalar()
        results["traces"] = count == expected_counts["traces"]
    
    return results


def verify_relationships(db_session: Session, parent_model, parent_id, 
                         child_model, expected_count: int = 1) -> bool:
    """Verify relationship between parent and child models."""
    if hasattr(child_model, 'event_id'):
        # For models related through Event
        parent_event_ids = db_session.query(Event.id).filter(
            getattr(Event, parent_model.__tablename__.lower() + '_id') == parent_id
        ).all()
        parent_event_ids = [id[0] for id in parent_event_ids]
        
        count = db_session.query(func.count(child_model.id)).filter(
            child_model.event_id.in_(parent_event_ids)
        ).scalar()
        
    elif hasattr(child_model, parent_model.__tablename__.lower() + '_id'):
        # For direct relationships
        count = db_session.query(func.count(child_model.id)).filter(
            getattr(child_model, parent_model.__tablename__.lower() + '_id') == parent_id
        ).scalar()
    
    else:
        raise ValueError(f"Cannot determine relationship between {parent_model.__name__} and {child_model.__name__}")
    
    return count == expected_count


# --- Performance Testing Helpers ---

def measure_execution_time(func, *args, **kwargs) -> Tuple[Any, float]:
    """Measure execution time of a function."""
    start_time = time.time()
    result = func(*args, **kwargs)
    end_time = time.time()
    return result, end_time - start_time


def measure_memory_usage(func, *args, **kwargs) -> Tuple[Any, float]:
    """Measure memory usage of a function."""
    process = psutil.Process(os.getpid())
    mem_before = process.memory_info().rss / 1024 / 1024  # MB
    result = func(*args, **kwargs)
    mem_after = process.memory_info().rss / 1024 / 1024  # MB
    return result, mem_after - mem_before


class PerformanceResult:
    """Store and analyze performance test results."""
    
    def __init__(self, name: str):
        self.name = name
        self.execution_times = []
        self.memory_usages = []
    
    def add_result(self, execution_time: float, memory_usage: Optional[float] = None):
        """Add a test result."""
        self.execution_times.append(execution_time)
        if memory_usage is not None:
            self.memory_usages.append(memory_usage)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics for the performance results."""
        if not self.execution_times:
            return {"error": "No results collected"}
        
        exec_times = self.execution_times
        mem_usages = self.memory_usages if self.memory_usages else [0]
        
        return {
            "name": self.name,
            "samples": len(exec_times),
            "execution_time": {
                "min": min(exec_times),
                "max": max(exec_times),
                "avg": sum(exec_times) / len(exec_times),
                "total": sum(exec_times)
            },
            "memory_usage": {
                "min": min(mem_usages),
                "max": max(mem_usages),
                "avg": sum(mem_usages) / len(mem_usages) if mem_usages[0] != 0 else 0
            }
        }
    
    def __str__(self) -> str:
        """String representation of performance results."""
        stats = self.get_stats()
        if "error" in stats:
            return f"Performance test '{self.name}': {stats['error']}"
        
        s = f"Performance test '{self.name}':\n"
        s += f"  Samples: {stats['samples']}\n"
        s += f"  Execution time (seconds):\n"
        s += f"    Min: {stats['execution_time']['min']:.4f}\n"
        s += f"    Max: {stats['execution_time']['max']:.4f}\n"
        s += f"    Avg: {stats['execution_time']['avg']:.4f}\n"
        s += f"    Total: {stats['execution_time']['total']:.4f}\n"
        
        if stats['memory_usage']['avg'] > 0:
            s += f"  Memory usage (MB):\n"
            s += f"    Min: {stats['memory_usage']['min']:.2f}\n"
            s += f"    Max: {stats['memory_usage']['max']:.2f}\n"
            s += f"    Avg: {stats['memory_usage']['avg']:.2f}\n"
        
        return s 