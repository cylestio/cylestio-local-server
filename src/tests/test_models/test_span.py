"""
Tests for the Span model.
"""
import datetime
import pytest

from models.agent import Agent
from models.trace import Trace
from models.span import Span


@pytest.fixture
def test_agent(db_session):
    """Create a test agent for use in span tests."""
    agent = Agent(
        agent_id="test-span-agent",
        name="Test Span Agent",
        first_seen=datetime.datetime.utcnow(),
        last_seen=datetime.datetime.utcnow()
    )
    db_session.add(agent)
    db_session.commit()
    return agent


@pytest.fixture
def test_trace(db_session, test_agent):
    """Create a test trace for use in span tests."""
    trace = Trace(
        trace_id="test-span-trace",
        agent_id=test_agent.id,
        start_timestamp=datetime.datetime.utcnow()
    )
    db_session.add(trace)
    db_session.commit()
    return trace


def test_span_creation(db_session, test_trace):
    """Test creating a new span."""
    # Create a new span
    span = Span(
        span_id="test-span-id",
        trace_id=test_trace.trace_id,
        name="test-span-name",
        start_timestamp=datetime.datetime.utcnow()
    )
    
    db_session.add(span)
    db_session.commit()
    
    # Query the span
    saved_span = db_session.query(Span).filter(Span.span_id == "test-span-id").first()
    
    # Verify
    assert saved_span is not None
    assert saved_span.span_id == "test-span-id"
    assert saved_span.trace_id == test_trace.trace_id
    assert saved_span.name == "test-span-name"
    assert saved_span.start_timestamp is not None
    assert saved_span.end_timestamp is None
    assert saved_span.parent_span_id is None


def test_span_with_parent(db_session, test_trace):
    """Test creating a span with a parent span."""
    # Create a parent span
    parent_span = Span(
        span_id="parent-span-id",
        trace_id=test_trace.trace_id,
        name="parent-span",
        start_timestamp=datetime.datetime.utcnow()
    )
    db_session.add(parent_span)
    db_session.commit()
    
    # Create a child span
    child_span = Span(
        span_id="child-span-id",
        trace_id=test_trace.trace_id,
        parent_span_id=parent_span.span_id,
        name="child-span",
        start_timestamp=datetime.datetime.utcnow()
    )
    db_session.add(child_span)
    db_session.commit()
    
    # Query the child span
    saved_child = db_session.query(Span).filter(Span.span_id == "child-span-id").first()
    
    # Verify
    assert saved_child is not None
    assert saved_child.parent_span_id == "parent-span-id"


def test_span_get_or_create_new(db_session, test_trace):
    """Test get_or_create method when creating a new span."""
    # Use get_or_create to create a new span
    span = Span.get_or_create(
        db_session,
        span_id="new-span-id",
        trace_id=test_trace.trace_id,
        name="new-span"
    )
    
    db_session.commit()
    
    # Verify
    assert span is not None
    assert span.span_id == "new-span-id"
    assert span.trace_id == test_trace.trace_id
    assert span.name == "new-span"
    assert span.start_timestamp is not None
    assert span.end_timestamp is None
    assert span.parent_span_id is None


def test_span_get_or_create_with_parent(db_session, test_trace):
    """Test get_or_create method with a parent span."""
    # Create a parent span
    parent_span = Span(
        span_id="parent-get-create-id",
        trace_id=test_trace.trace_id,
        name="parent-get-create",
        start_timestamp=datetime.datetime.utcnow()
    )
    db_session.add(parent_span)
    db_session.commit()
    
    # Use get_or_create to create a child span
    child_span = Span.get_or_create(
        db_session,
        span_id="child-get-create-id",
        trace_id=test_trace.trace_id,
        parent_span_id=parent_span.span_id,
        name="child-get-create"
    )
    
    db_session.commit()
    
    # Verify
    assert child_span is not None
    assert child_span.span_id == "child-get-create-id"
    assert child_span.trace_id == test_trace.trace_id
    assert child_span.parent_span_id == parent_span.span_id
    assert child_span.name == "child-get-create"


def test_span_get_or_create_existing(db_session, test_trace):
    """Test get_or_create method with an existing span."""
    # Create a span
    span1 = Span(
        span_id="existing-span-id",
        trace_id=test_trace.trace_id,
        name="existing-span",
        start_timestamp=datetime.datetime.utcnow()
    )
    db_session.add(span1)
    db_session.commit()
    
    # Use get_or_create to get the existing span
    span2 = Span.get_or_create(
        db_session,
        span_id="existing-span-id",
        trace_id=test_trace.trace_id,
        name="updated-span"  # This should be ignored
    )
    
    db_session.commit()
    
    # Verify that we got the existing span
    assert span2.span_id == span1.span_id
    assert span2.trace_id == span1.trace_id
    assert span2.name == "existing-span"  # Name should not be updated


def test_span_update_timestamps(db_session, test_trace):
    """Test updating span timestamps."""
    # Create a span with no timestamps
    span = Span(
        span_id="update-span-id",
        trace_id=test_trace.trace_id,
        name="update-span"
    )
    db_session.add(span)
    db_session.commit()
    
    # Set start and end timestamps
    start_time = datetime.datetime(2020, 1, 1, 12, 0, 0)
    end_time = datetime.datetime(2020, 1, 1, 13, 0, 0)
    
    span.update_timestamps(db_session, start_time, end_time)
    db_session.commit()
    
    # Refresh from database
    db_session.refresh(span)
    
    # Verify
    assert span.start_timestamp == start_time
    assert span.end_timestamp == end_time


def test_span_duration_with_timestamps(db_session, test_trace):
    """Test span duration calculation with timestamps."""
    # Create a span with start and end times
    start_time = datetime.datetime(2020, 1, 1, 12, 0, 0)
    end_time = datetime.datetime(2020, 1, 1, 13, 0, 0)
    
    span = Span(
        span_id="duration-span-id",
        trace_id=test_trace.trace_id,
        name="duration-span",
        start_timestamp=start_time,
        end_timestamp=end_time
    )
    db_session.add(span)
    db_session.commit()
    
    # Get duration
    duration = span.get_duration_seconds()
    
    # Verify (should be 3600 seconds = 1 hour)
    assert duration == 3600.0


def test_span_get_child_spans(db_session, test_trace):
    """Test getting child spans."""
    # Create a parent span
    parent_span = Span(
        span_id="children-parent-id",
        trace_id=test_trace.trace_id,
        name="children-parent"
    )
    db_session.add(parent_span)
    
    # Create three child spans
    for i in range(3):
        child_span = Span(
            span_id=f"child-{i}-id",
            trace_id=test_trace.trace_id,
            parent_span_id=parent_span.span_id,
            name=f"child-{i}"
        )
        db_session.add(child_span)
    
    db_session.commit()
    
    # Get child spans
    children = parent_span.get_child_spans(db_session)
    
    # Verify
    assert len(children) == 3
    for i, child in enumerate(sorted(children, key=lambda s: s.name)):
        assert child.name == f"child-{i}"
        assert child.parent_span_id == parent_span.span_id


def test_span_get_span_tree(db_session, test_trace):
    """Test getting the entire span tree."""
    # Create a root span
    root_span = Span(
        span_id="root-span-id",
        trace_id=test_trace.trace_id,
        name="root-span"
    )
    db_session.add(root_span)
    db_session.commit()
    
    # Create child spans
    child1 = Span(
        span_id="child1-id",
        trace_id=test_trace.trace_id,
        parent_span_id=root_span.span_id,
        name="child1"
    )
    db_session.add(child1)
    
    child2 = Span(
        span_id="child2-id",
        trace_id=test_trace.trace_id,
        parent_span_id=root_span.span_id,
        name="child2"
    )
    db_session.add(child2)
    
    # Create grandchild span
    grandchild = Span(
        span_id="grandchild-id",
        trace_id=test_trace.trace_id,
        parent_span_id=child1.span_id,
        name="grandchild"
    )
    db_session.add(grandchild)
    
    db_session.commit()
    
    # Get the span tree
    tree = root_span.get_span_tree(db_session)
    
    # Verify
    assert len(tree) == 4  # root + 2 children + 1 grandchild
    
    # Check that each span is in the tree
    span_ids = [span.span_id for span in tree]
    assert "root-span-id" in span_ids
    assert "child1-id" in span_ids
    assert "child2-id" in span_ids
    assert "grandchild-id" in span_ids 