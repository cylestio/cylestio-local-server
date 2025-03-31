"""
Performance tests for the Cylestio Local Server.

These tests measure processing throughput, memory usage, and database
query performance under various conditions.
"""
import json
import datetime
import os
import uuid
import time
import pytest
import psutil
from pathlib import Path
from sqlalchemy import create_engine, func, text
from sqlalchemy.orm import Session

from models.base import Base
from models.agent import Agent
from models.event import Event
from models.llm_interaction import LLMInteraction
from models.security_alert import SecurityAlert
from models.framework_event import FrameworkEvent
from models.tool_interaction import ToolInteraction
from models.session import Session as SessionModel
from models.span import Span
from models.trace import Trace

from processing.simple_processor import SimpleProcessor
from tests.test_utils import PerformanceResult, measure_execution_time, measure_memory_usage


class TestProcessingPerformance:
    """Test performance characteristics of event processing."""
    
    @pytest.fixture(scope="function")
    def setup_perf_test(self, temp_db_path):
        """Set up a performance test environment with a temporary database."""
        # Create a temporary database
        db_url = f"sqlite:///{temp_db_path}"
        engine = create_engine(db_url, echo=False)
        
        # Create all tables
        Base.metadata.create_all(engine)
        
        # Create a session factory
        def session_factory():
            session = Session(bind=engine)
            try:
                yield session
            finally:
                session.close()
        
        # Create a processor
        processor = SimpleProcessor(session_factory)
        
        # Create basic agents
        session = next(session_factory())
        for i in range(5):
            agent = Agent(
                agent_id=f"perf-agent-{i}",
                name=f"Performance Test Agent {i}",
                first_seen=datetime.datetime.utcnow(),
                last_seen=datetime.datetime.utcnow(),
                is_active=True
            )
            session.add(agent)
        session.commit()
        
        # Return test fixtures
        return engine, session_factory, processor
    
    def generate_performance_test_event(self, event_type="llm", index=0):
        """Generate a test event for performance testing."""
        agent_id = f"perf-agent-{index % 5}"
        timestamp = datetime.datetime.utcnow()
        
        if event_type == "llm":
            return {
                "name": "llm.call.start" if index % 2 == 0 else "llm.call.finish",
                "timestamp": timestamp.isoformat() + "Z",
                "agent_id": agent_id,
                "event_type": "llm",
                "level": "INFO",
                "schema_version": "1.0",
                "attributes": {
                    "llm.vendor": "anthropic",
                    "llm.model": "claude-3-haiku-20240307",
                    "llm.request.timestamp": timestamp.isoformat() + "Z",
                    "llm.request.data": {
                        "messages": [{"role": "user", "content": f"Test message {index}"}]
                    } if index % 2 == 0 else None,
                    "llm.response.content": {
                        "type": "text", 
                        "text": f"Test response {index}"
                    } if index % 2 == 1 else None,
                    "llm.usage.input_tokens": 10 if index % 2 == 1 else None,
                    "llm.usage.output_tokens": 20 if index % 2 == 1 else None,
                    "llm.usage.total_tokens": 30 if index % 2 == 1 else None
                }
            }
        elif event_type == "security":
            return {
                "name": "security.alert.detected",
                "timestamp": timestamp.isoformat() + "Z",
                "agent_id": agent_id,
                "event_type": "security",
                "level": "WARN",
                "schema_version": "1.0",
                "attributes": {
                    "security.alert.type": "content_policy_violation",
                    "security.alert.severity": "medium",
                    "security.alert.details": {
                        "policy": "harmful_content",
                        "score": 0.85,
                        "flagged_content": f"Test content {index}"
                    }
                }
            }
        elif event_type == "span":
            return {
                "name": "span.start" if index % 2 == 0 else "span.end",
                "timestamp": timestamp.isoformat() + "Z",
                "agent_id": agent_id,
                "event_type": "span",
                "level": "INFO",
                "schema_version": "1.0",
                "attributes": {
                    "span.id": f"span-{index//2}",
                    "span.name": f"test_span_{index//2}",
                    "span.start_time": timestamp.isoformat() + "Z" if index % 2 == 0 else None,
                    "span.end_time": timestamp.isoformat() + "Z" if index % 2 == 1 else None,
                    "span.parent_id": f"span-{(index//2)-1}" if index//2 > 0 and index % 3 != 0 else None
                }
            }
        else:  # Default event
            return {
                "name": f"test.event.{index}",
                "timestamp": timestamp.isoformat() + "Z",
                "agent_id": agent_id,
                "event_type": "test",
                "level": "INFO",
                "schema_version": "1.0",
                "attributes": {
                    "test.index": index,
                    "test.value": f"test_value_{index}"
                }
            }
    
    def test_single_event_processing_performance(self, setup_perf_test):
        """Test performance of processing a single event."""
        engine, session_factory, processor = setup_perf_test
        
        # Create test events of different types
        event_types = ["llm", "security", "span"]
        events = [self.generate_performance_test_event(event_type) for event_type in event_types]
        
        # Test processing performance for each event type
        for i, event in enumerate(events):
            event_type = event_types[i]
            
            # Measure execution time
            result, execution_time = measure_execution_time(processor.process_event, event)
            
            # Verify success
            assert result["success"] is True
            
            # Record performance results
            print(f"\nProcessing time for {event_type} event: {execution_time:.6f} seconds")
    
    def test_batch_processing_performance(self, setup_perf_test):
        """Test performance of batch processing with different batch sizes."""
        engine, session_factory, processor = setup_perf_test
        
        # Test with different batch sizes
        batch_sizes = [10, 50, 100]
        
        for batch_size in batch_sizes:
            # Generate test events
            events = [self.generate_performance_test_event(
                event_type=["llm", "security", "span"][i % 3], 
                index=i
            ) for i in range(batch_size)]
            
            # Measure execution time and memory
            result, execution_time = measure_execution_time(processor.process_batch, events)
            
            # Calculate throughput
            throughput = batch_size / execution_time
            
            # Verify success
            assert result["successful"] == batch_size
            
            # Record performance results
            print(f"\nBatch size: {batch_size}")
            print(f"Total processing time: {execution_time:.6f} seconds")
            print(f"Throughput: {throughput:.2f} events/second")
            
            # Verify database state
            session = next(session_factory())
            events_count = session.query(func.count(Event.id)).scalar()
            assert events_count >= batch_size
    
    @pytest.mark.skipif("SKIP_HEAVY_TESTS" in os.environ, reason="Skipping heavy performance test")
    def test_large_scale_processing(self, setup_perf_test):
        """Test processing a large number of events to assess scaling."""
        engine, session_factory, processor = setup_perf_test
        
        # Number of events to process
        event_count = 1000
        
        # Generate test events - mix of different types
        events = []
        for i in range(event_count):
            event_type = ["llm", "security", "span"][i % 3]
            events.append(self.generate_performance_test_event(event_type, i))
        
        # Process in batches for better performance
        batch_size = 100
        total_start_time = time.time()
        total_successful = 0
        
        for i in range(0, event_count, batch_size):
            batch = events[i:i+batch_size]
            result = processor.process_batch(batch)
            total_successful += result["successful"]
        
        total_end_time = time.time()
        total_time = total_end_time - total_start_time
        throughput = event_count / total_time
        
        # Verify success
        assert total_successful == event_count
        
        # Record performance results
        print(f"\nLarge-scale processing test:")
        print(f"Processed {event_count} events in {total_time:.2f} seconds")
        print(f"Overall throughput: {throughput:.2f} events/second")
        
        # Verify database state
        session = next(session_factory())
        events_count = session.query(func.count(Event.id)).scalar()
        llm_count = session.query(func.count(LLMInteraction.id)).scalar()
        security_count = session.query(func.count(SecurityAlert.id)).scalar()
        span_count = session.query(func.count(Span.span_id)).scalar()
        
        print(f"Database state:")
        print(f"Events: {events_count}")
        print(f"LLM Interactions: {llm_count}")
        print(f"Security Alerts: {security_count}")
        print(f"Spans: {span_count}")
        
        assert events_count == event_count
    
    def test_memory_usage(self, setup_perf_test):
        """Test memory usage during event processing."""
        engine, session_factory, processor = setup_perf_test
        
        # Generate test events
        batch_size = 100
        events = [self.generate_performance_test_event(
            event_type=["llm", "security", "span"][i % 3], 
            index=i
        ) for i in range(batch_size)]
        
        # Measure baseline memory
        process = psutil.Process(os.getpid())
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Measure memory during processing
        result, memory_usage = measure_memory_usage(processor.process_batch, events)
        
        # Verify success
        assert result["successful"] == batch_size
        
        # Record memory usage
        print(f"\nMemory usage for processing {batch_size} events:")
        print(f"Baseline memory: {baseline_memory:.2f} MB")
        print(f"Additional memory used: {memory_usage:.2f} MB")
        print(f"Memory per event: {memory_usage/batch_size:.4f} MB/event")


class TestDatabasePerformance:
    """Test database query performance."""
    
    @pytest.fixture(scope="function")
    def setup_db_perf_test(self, temp_db_path):
        """Set up a database with test data for performance testing."""
        # Create a temporary database
        db_url = f"sqlite:///{temp_db_path}"
        engine = create_engine(db_url, echo=False)
        
        # Create all tables
        Base.metadata.create_all(engine)
        
        # Create a session
        session = Session(bind=engine)
        
        # Create test agents
        agent_ids = []
        for i in range(5):
            agent_id = f"db-perf-agent-{i}"
            agent = Agent(
                agent_id=agent_id,
                name=f"DB Performance Test Agent {i}",
                first_seen=datetime.datetime.utcnow(),
                last_seen=datetime.datetime.utcnow(),
                is_active=True
            )
            session.add(agent)
            session.flush()
            agent_ids.append(agent.id)
        
        # Create events and model objects
        n_events = 100
        timestamp = datetime.datetime.utcnow()
        
        sessions = []
        spans = []
        
        # Create sessions (5 sessions)
        for i in range(5):
            session_id = f"session-{i}"
            s = SessionModel(
                session_id=session_id,
                name=f"Test Session {i}",
                start_time=timestamp,
                agent_id=agent_ids[i % len(agent_ids)]
            )
            session.add(s)
            session.flush()
            sessions.append(s)
        
        # Create spans (10 spans, 2 per session)
        for i in range(10):
            span_id = f"span-{i}"
            parent_id = f"span-{i-1}" if i % 2 == 1 else None
            s = Span(
                span_id=span_id,
                name=f"Test Span {i}",
                start_time=timestamp,
                parent_id=parent_id,
                agent_id=agent_ids[i % len(agent_ids)]
            )
            session.add(s)
            session.flush()
            spans.append(s)
        
        # Create events of different types
        for i in range(n_events):
            event_type = ["llm", "security", "framework", "tool", "span", "session"][i % 6]
            event_name = f"{event_type}.test.{i}"
            
            event = Event(
                agent_id=agent_ids[i % len(agent_ids)],
                timestamp=timestamp + datetime.timedelta(seconds=i),
                schema_version="1.0",
                name=event_name,
                level="INFO",
                event_type=event_type,
                session_id=sessions[i % len(sessions)].session_id if i % 2 == 0 else None,
                span_id=spans[i % len(spans)].span_id if i % 3 == 0 else None
            )
            session.add(event)
            session.flush()
            
            # Add related model based on event type
            if event_type == "llm":
                llm = LLMInteraction(
                    event_id=event.id,
                    interaction_type="start" if i % 2 == 0 else "finish",
                    vendor="test-vendor",
                    model=f"test-model-{i % 3}",
                    request_timestamp=timestamp,
                    request_data={"test": f"data-{i}"},
                    response_timestamp=timestamp + datetime.timedelta(seconds=1) if i % 2 == 1 else None,
                    duration_ms=100 if i % 2 == 1 else None,
                    input_tokens=10 if i % 2 == 1 else None,
                    output_tokens=20 if i % 2 == 1 else None
                )
                session.add(llm)
            
            elif event_type == "security":
                alert = SecurityAlert(
                    event_id=event.id,
                    alert_type="test-alert",
                    severity="medium",
                    source="test-source",
                    alert_timestamp=timestamp,
                    details={"test": f"detail-{i}"}
                )
                session.add(alert)
            
            elif event_type == "framework":
                fw = FrameworkEvent(
                    event_id=event.id,
                    framework_type="test-framework",
                    framework_version="1.0",
                    component_type="test-component",
                    component_name=f"test-name-{i}"
                )
                session.add(fw)
            
            elif event_type == "tool":
                tool = ToolInteraction(
                    event_id=event.id,
                    tool_name=f"test-tool-{i % 3}",
                    tool_description="Test tool",
                    tool_input={"input": f"test-{i}"} if i % 2 == 0 else None,
                    tool_output={"output": f"result-{i}"} if i % 2 == 1 else None,
                    duration_ms=50 if i % 2 == 1 else None,
                    status="success" if i % 2 == 1 else None
                )
                session.add(tool)
        
        # Commit all changes
        session.commit()
        
        # Return the engine and session for testing
        return engine, session
    
    def test_query_performance(self, setup_db_perf_test):
        """Test performance of common database queries."""
        engine, session = setup_db_perf_test
        
        # Define common queries to test
        queries = {
            "count_all_events": lambda s: s.query(func.count(Event.id)).scalar(),
            "get_events_by_agent": lambda s: s.query(Event).filter(Event.agent_id == 1).all(),
            "get_events_by_type": lambda s: s.query(Event).filter(Event.event_type == "llm").all(),
            "get_events_in_session": lambda s: s.query(Event).filter(Event.session_id == "session-0").all(),
            "get_events_in_span": lambda s: s.query(Event).filter(Event.span_id == "span-0").all(),
            "get_llm_interactions": lambda s: s.query(LLMInteraction).all(),
            "get_security_alerts": lambda s: s.query(SecurityAlert).all(),
            "get_llm_with_tokens": lambda s: s.query(LLMInteraction).filter(LLMInteraction.input_tokens.isnot(None)).all(),
            "get_tools_by_name": lambda s: s.query(ToolInteraction).filter(ToolInteraction.tool_name == "test-tool-0").all(),
            "get_session_with_events": lambda s: s.query(SessionModel).join(Event, Event.session_id == SessionModel.session_id).all(),
            "get_span_hierarchy": lambda s: s.query(Span).filter(Span.parent_id.isnot(None)).all(),
            "complex_join": lambda s: (
                s.query(Event, LLMInteraction)
                .join(LLMInteraction, Event.id == LLMInteraction.event_id)
                .filter(Event.event_type == "llm")
                .limit(10)
                .all()
            )
        }
        
        # Execute each query and measure performance
        perf_results = {}
        for name, query_func in queries.items():
            # Measure execution time (average of 3 runs)
            execution_times = []
            for _ in range(3):
                _, execution_time = measure_execution_time(query_func, session)
                execution_times.append(execution_time)
            
            avg_time = sum(execution_times) / len(execution_times)
            perf_results[name] = avg_time
        
        # Print the results
        print("\nDatabase Query Performance:")
        for name, time in perf_results.items():
            print(f"{name}: {time:.6f} seconds")
    
    @pytest.mark.skipif("SKIP_HEAVY_TESTS" in os.environ, reason="Skipping heavy performance test")
    def test_raw_query_performance(self, setup_db_perf_test):
        """Test performance of raw SQL queries vs. ORM queries."""
        engine, session = setup_db_perf_test
        
        # Define equivalent ORM and raw SQL queries
        queries = {
            "count_events_orm": lambda s: s.query(func.count(Event.id)).scalar(),
            "count_events_raw": lambda s: s.execute(text("SELECT COUNT(*) FROM events")).scalar(),
            
            "get_llm_interactions_orm": lambda s: s.query(LLMInteraction).all(),
            "get_llm_interactions_raw": lambda s: [
                dict(row) for row in s.execute(text("SELECT * FROM llm_interactions")).mappings()
            ],
            
            "get_events_by_type_orm": lambda s: s.query(Event).filter(Event.event_type == "llm").all(),
            "get_events_by_type_raw": lambda s: [
                dict(row) for row in s.execute(
                    text("SELECT * FROM events WHERE event_type = 'llm'")
                ).mappings()
            ],
            
            "complex_join_orm": lambda s: (
                s.query(Event, LLMInteraction)
                .join(LLMInteraction, Event.id == LLMInteraction.event_id)
                .filter(Event.event_type == "llm")
                .all()
            ),
            "complex_join_raw": lambda s: [
                dict(row) for row in s.execute(text(
                    "SELECT e.*, l.* FROM events e "
                    "JOIN llm_interactions l ON e.id = l.event_id "
                    "WHERE e.event_type = 'llm'"
                )).mappings()
            ]
        }
        
        # Execute each query and measure performance
        perf_results = {}
        for name, query_func in queries.items():
            # Measure execution time (average of 3 runs)
            execution_times = []
            for _ in range(3):
                _, execution_time = measure_execution_time(query_func, session)
                execution_times.append(execution_time)
            
            avg_time = sum(execution_times) / len(execution_times)
            perf_results[name] = avg_time
        
        # Print the results
        print("\nORM vs. Raw SQL Query Performance:")
        for i in range(0, len(queries), 2):
            orm_name = list(queries.keys())[i]
            raw_name = list(queries.keys())[i+1]
            orm_time = perf_results[orm_name]
            raw_time = perf_results[raw_name]
            diff_pct = ((orm_time - raw_time) / raw_time) * 100
            
            print(f"{orm_name}: {orm_time:.6f} seconds")
            print(f"{raw_name}: {raw_time:.6f} seconds")
            print(f"Difference: {diff_pct:.1f}% slower" if diff_pct > 0 else f"Difference: {-diff_pct:.1f}% faster")
            print()
    
    def test_scaling_with_data_volume(self, setup_db_perf_test):
        """Test how query performance scales with increasing data volume."""
        engine, session = setup_db_perf_test
        
        # First, measure performance with the existing data
        query_func = lambda s: s.query(Event).filter(Event.event_type == "llm").all()
        
        initial_count = session.query(func.count(Event.id)).scalar()
        _, initial_time = measure_execution_time(query_func, session)
        
        print(f"\nInitial query time with {initial_count} events: {initial_time:.6f} seconds")
        
        # Now add more data in batches and measure performance after each batch
        batch_sizes = [100, 500, 1000]
        scaling_results = []
        
        # Define a consistent query to test
        test_query = lambda s: s.query(Event).filter(Event.event_type == "llm").all()
        
        for batch_size in batch_sizes:
            # Skip the largest batches if SKIP_HEAVY_TESTS is set
            if batch_size > 100 and "SKIP_HEAVY_TESTS" in os.environ:
                continue
                
            # Add a batch of new events
            agent_id = 1  # Use the first agent
            timestamp = datetime.datetime.utcnow()
            
            for i in range(batch_size):
                event_type = ["llm", "security", "framework", "tool", "span", "session"][i % 6]
                event_name = f"{event_type}.scaling.{i}"
                
                event = Event(
                    agent_id=agent_id,
                    timestamp=timestamp + datetime.timedelta(seconds=i),
                    schema_version="1.0",
                    name=event_name,
                    level="INFO",
                    event_type=event_type
                )
                session.add(event)
                
                # Add related model based on event type
                if event_type == "llm":
                    llm = LLMInteraction(
                        event_id=event.id,
                        interaction_type="start" if i % 2 == 0 else "finish",
                        vendor="test-vendor",
                        model=f"test-model-{i % 3}"
                    )
                    session.add(llm)
            
            session.commit()
            
            # Measure query performance after adding data
            current_count = session.query(func.count(Event.id)).scalar()
            _, current_time = measure_execution_time(test_query, session)
            
            scaling_results.append((current_count, current_time))
            
            print(f"Query time with {current_count} events: {current_time:.6f} seconds")
        
        # Calculate scaling factor
        if len(scaling_results) > 1:
            first_count, first_time = scaling_results[0]
            last_count, last_time = scaling_results[-1]
            
            data_scale = last_count / first_count
            time_scale = last_time / first_time
            
            print(f"\nData volume increased by factor of {data_scale:.1f}x")
            print(f"Query time increased by factor of {time_scale:.1f}x")
            
            if time_scale < data_scale:
                print("Query time scales sub-linearly with data volume (good)")
            elif time_scale > data_scale:
                print("Query time scales super-linearly with data volume (concerning)")
            else:
                print("Query time scales linearly with data volume (expected)")


if __name__ == "__main__":
    # Allow running the performance tests directly
    pytest.main(["-xvs", __file__]) 