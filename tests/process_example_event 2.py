#!/usr/bin/env python3
"""
Process all events from example_records.json using SimpleProcessor.
This demonstrates the end-to-end flow from JSON events to database entries.
"""
import json
import os
import sys
from pathlib import Path
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
import time
import logging

# Using imports within src directory
from src.models.base import init_db, get_db, create_all
from src.models.event import Event
from src.models.llm_interaction import LLMInteraction
from src.models.security_alert import SecurityAlert
from src.models.framework_event import FrameworkEvent
from src.models.tool_interaction import ToolInteraction
from src.models.agent import Agent
from src.models.session import Session as SessionModel
from src.models.trace import Trace
from src.models.span import Span
from src.processing.simple_processor import SimpleProcessor

# Set up database
DB_PATH = "/tmp/cylestio_demo.db"
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)
db_url = f"sqlite:///{DB_PATH}"
init_db(db_url, echo=True)
create_all()  # Create all tables

# Create a database session
db_session = next(get_db())

# Initialize processor with the get_db function
processor = SimpleProcessor(get_db)

# Let's pre-create the agent to avoid the error
current_time = datetime.utcnow()
agent = Agent(
    agent_id="chatbot-agent", 
    name="Chatbot Agent", 
    first_seen=current_time,
    last_seen=current_time,
    is_active=True
)
db_session.add(agent)

# Also create the rag-agent and weather-agent as they appear in the example records
agent2 = Agent(
    agent_id="rag-agent", 
    name="RAG Agent", 
    first_seen=current_time,
    last_seen=current_time,
    is_active=True
)
db_session.add(agent2)

agent3 = Agent(
    agent_id="weather-agent", 
    name="Weather Agent", 
    first_seen=current_time,
    last_seen=current_time,
    is_active=True
)
db_session.add(agent3)

db_session.commit()
print(f"Created agents: chatbot-agent, rag-agent, weather-agent")

# Load all events from example_records.json
example_file = Path("example_records.json")

try:
    events_to_process = []
    with open(example_file, 'r') as f:
        for line in f:
            try:
                event_data = json.loads(line)
                events_to_process.append(event_data)
            except json.JSONDecodeError:
                print(f"Warning: Skipping invalid JSON line: {line[:50]}...")
                continue
    
    print(f"Loaded {len(events_to_process)} events from {example_file}")
    
    if not events_to_process:
        print("No events found in the example_records.json")
        sys.exit(1)
        
except FileNotFoundError:
    print(f"Error: File not found: {example_file}")
    sys.exit(1)

# Process all events
start_time = time.time()
successful_events = 0
failed_events = 0
event_types = {}

for i, event_data in enumerate(events_to_process):
    print(f"\nProcessing event {i+1}/{len(events_to_process)}: {event_data.get('name', 'Unknown')}")
    result = processor.process_event(event_data)
    
    event_type = event_data.get('name', '').split('.')[0] if '.' in event_data.get('name', '') else 'unknown'
    event_types[event_type] = event_types.get(event_type, 0) + 1
    
    if result.get("success", False):
        successful_events += 1
    else:
        failed_events += 1
        print(f"  Error: {result.get('error', 'Unknown error')}")

end_time = time.time()
processing_time = end_time - start_time

# Database evaluation
print("\n" + "="*50)
print("PROCESSING SUMMARY")
print("="*50)
print(f"Total events processed: {len(events_to_process)}")
print(f"Successful: {successful_events}, Failed: {failed_events}")
print(f"Processing time: {processing_time:.2f} seconds")
print(f"Events per second: {len(events_to_process)/processing_time:.2f}")

print("\nEvent types processed:")
for event_type, count in event_types.items():
    print(f"  {event_type}: {count}")

print("\n" + "="*50)
print("DATABASE EVALUATION")
print("="*50)

# Count records in each table
events_count = db_session.query(func.count(Event.id)).scalar()
llm_interactions_count = db_session.query(func.count(LLMInteraction.id)).scalar()
security_alerts_count = db_session.query(func.count(SecurityAlert.id)).scalar()
framework_events_count = db_session.query(func.count(FrameworkEvent.id)).scalar()
tool_interactions_count = db_session.query(func.count(ToolInteraction.id)).scalar()
sessions_count = db_session.query(func.count(SessionModel.id)).scalar()
traces_count = db_session.query(func.count(Trace.id)).scalar()
spans_count = db_session.query(func.count(Span.span_id)).scalar()

print(f"Events: {events_count}")
print(f"LLM Interactions: {llm_interactions_count}")
print(f"Security Alerts: {security_alerts_count}")
print(f"Framework Events: {framework_events_count}")
print(f"Tool Interactions: {tool_interactions_count}")
print(f"Sessions: {sessions_count}")
print(f"Traces: {traces_count}")
print(f"Spans: {spans_count}")

# Event types in the database
event_types_db = db_session.query(Event.event_type, func.count(Event.id)).group_by(Event.event_type).all()
print("\nEvent types in database:")
for event_type, count in event_types_db:
    print(f"  {event_type}: {count}")

# Sample of each event type
print("\nSamples of each event type:")

# LLM events
if llm_interactions_count > 0:
    print("\nLLM Interactions sample:")
    llm_sample = db_session.query(LLMInteraction).first()
    print(f"  ID: {llm_sample.id}")
    print(f"  Event ID: {llm_sample.event_id}")
    print(f"  Vendor: {llm_sample.vendor}")
    print(f"  Model: {llm_sample.model}")
    
    # Add debugging for configuration parameters
    print(f"  Temperature: {llm_sample.temperature}")
    print(f"  Max Tokens: {llm_sample.max_tokens}")
    print(f"  Top P: {llm_sample.top_p}")
    print(f"  Frequency Penalty: {llm_sample.frequency_penalty}")
    print(f"  Presence Penalty: {llm_sample.presence_penalty}")
    
    # Display LLM attributes from raw_attributes
    raw_attributes = llm_sample.raw_attributes or {}
    print(f"  Raw attributes count: {len(raw_attributes)}")
    for key, value in raw_attributes.items():
        # Only show a preview of long values
        value_str = str(value)
        print(f"    {key}: {value_str[:50]}..." if len(value_str) > 50 else f"    {key}: {value_str}")
    
    # Print statistics for parameters across all LLM interactions
    print("\nLLM Configuration Parameter Statistics:")
    
    # Check temperature parameter stats
    temperature_count = db_session.query(func.count(LLMInteraction.id)).filter(LLMInteraction.temperature.isnot(None)).scalar()
    temperature_null = db_session.query(func.count(LLMInteraction.id)).filter(LLMInteraction.temperature.is_(None)).scalar()
    print(f"  Temperature: {temperature_count} populated, {temperature_null} NULL")
    
    # Check max_tokens parameter stats
    max_tokens_count = db_session.query(func.count(LLMInteraction.id)).filter(LLMInteraction.max_tokens.isnot(None)).scalar()
    max_tokens_null = db_session.query(func.count(LLMInteraction.id)).filter(LLMInteraction.max_tokens.is_(None)).scalar()
    print(f"  Max Tokens: {max_tokens_count} populated, {max_tokens_null} NULL")
    
    # Check top_p parameter stats
    top_p_count = db_session.query(func.count(LLMInteraction.id)).filter(LLMInteraction.top_p.isnot(None)).scalar()
    top_p_null = db_session.query(func.count(LLMInteraction.id)).filter(LLMInteraction.top_p.is_(None)).scalar()
    print(f"  Top P: {top_p_count} populated, {top_p_null} NULL")
    
    # Sample a few different LLM interactions to verify extraction for different vendors/formats
    print("\nSampling a few different LLM interactions:")
    llm_samples = db_session.query(LLMInteraction).limit(5).all()
    for i, sample in enumerate(llm_samples):
        print(f"\n  Sample {i+1}:")
        print(f"    Vendor: {sample.vendor}")
        print(f"    Model: {sample.model}")
        print(f"    Temperature: {sample.temperature}")
        print(f"    Max Tokens: {sample.max_tokens}")
        print(f"    Top P: {sample.top_p}")
        
        # Also print the event name to see if it's start or finish
        event = db_session.query(Event).filter(Event.id == sample.event_id).first()
        if event:
            print(f"    Event Name: {event.name}")

# Security alerts
if security_alerts_count > 0:
    print("\nSecurity Alerts sample:")
    security_sample = db_session.query(SecurityAlert).first()
    print(f"  ID: {security_sample.id}")
    print(f"  Event ID: {security_sample.event_id}")
    print(f"  Alert Type: {security_sample.alert_type}")
    print(f"  Severity: {security_sample.severity}")
    print(f"  Status: {security_sample.status}")
    context_dict = security_sample.get_context_dict()
    if context_dict:
        print(f"  Context: {context_dict}")

# Framework events
if framework_events_count > 0:
    print("\nFramework Events sample:")
    framework_sample = db_session.query(FrameworkEvent).first()
    print(f"  ID: {framework_sample.id}")
    print(f"  Event ID: {framework_sample.event_id}")
    print(f"  Framework: {framework_sample.framework_name}")
    print(f"  Framework Version: {framework_sample.framework_version}")
    print(f"  Category: {framework_sample.category}")
    print(f"  Subcategory: {framework_sample.subcategory}")
    print(f"  Component: {framework_sample.component}")
    print(f"  Lifecycle State: {framework_sample.lifecycle_state}")
    print(f"  Message: {framework_sample.message}")
    
    # Add detailed stats for framework events fields
    print("\nFramework Events Field Statistics:")
    
    # Check framework_name parameter stats
    framework_name_count = db_session.query(func.count(FrameworkEvent.id)).filter(FrameworkEvent.framework_name.isnot(None)).scalar()
    framework_name_null = db_session.query(func.count(FrameworkEvent.id)).filter(FrameworkEvent.framework_name.is_(None)).scalar()
    print(f"  Framework Name: {framework_name_count} populated, {framework_name_null} NULL")
    
    # Check framework_version parameter stats
    framework_version_count = db_session.query(func.count(FrameworkEvent.id)).filter(FrameworkEvent.framework_version.isnot(None)).scalar()
    framework_version_null = db_session.query(func.count(FrameworkEvent.id)).filter(FrameworkEvent.framework_version.is_(None)).scalar()
    print(f"  Framework Version: {framework_version_count} populated, {framework_version_null} NULL")
    
    # Check category parameter stats
    category_count = db_session.query(func.count(FrameworkEvent.id)).filter(FrameworkEvent.category.isnot(None)).scalar()
    category_null = db_session.query(func.count(FrameworkEvent.id)).filter(FrameworkEvent.category.is_(None)).scalar()
    print(f"  Category: {category_count} populated, {category_null} NULL")
    
    # Check subcategory parameter stats
    subcategory_count = db_session.query(func.count(FrameworkEvent.id)).filter(FrameworkEvent.subcategory.isnot(None)).scalar()
    subcategory_null = db_session.query(func.count(FrameworkEvent.id)).filter(FrameworkEvent.subcategory.is_(None)).scalar()
    print(f"  Subcategory: {subcategory_count} populated, {subcategory_null} NULL")
    
    # Check component parameter stats
    component_count = db_session.query(func.count(FrameworkEvent.id)).filter(FrameworkEvent.component.isnot(None)).scalar()
    component_null = db_session.query(func.count(FrameworkEvent.id)).filter(FrameworkEvent.component.is_(None)).scalar()
    print(f"  Component: {component_count} populated, {component_null} NULL")
    
    # Check lifecycle_state parameter stats
    lifecycle_state_count = db_session.query(func.count(FrameworkEvent.id)).filter(FrameworkEvent.lifecycle_state.isnot(None)).scalar()
    lifecycle_state_null = db_session.query(func.count(FrameworkEvent.id)).filter(FrameworkEvent.lifecycle_state.is_(None)).scalar()
    print(f"  Lifecycle State: {lifecycle_state_count} populated, {lifecycle_state_null} NULL")
    
    # Check message parameter stats
    message_count = db_session.query(func.count(FrameworkEvent.id)).filter(FrameworkEvent.message.isnot(None)).scalar()
    message_null = db_session.query(func.count(FrameworkEvent.id)).filter(FrameworkEvent.message.is_(None)).scalar()
    print(f"  Message: {message_count} populated, {message_null} NULL")
    
    # Sample a few different framework events to verify extraction for different types/formats
    print("\nSampling different framework events:")
    framework_samples = db_session.query(FrameworkEvent).limit(7).all()
    
    for i, sample in enumerate(framework_samples):
        print(f"\n  Sample {i+1}:")
        # Get the event to see the name
        event = db_session.query(Event).filter(Event.id == sample.event_id).first()
        print(f"    Event Name: {event.name if event else 'Unknown'}")
        print(f"    Framework Name: {sample.framework_name}")
        print(f"    Framework Version: {sample.framework_version}")
        print(f"    Category: {sample.category}")
        print(f"    Subcategory: {sample.subcategory}")
        print(f"    Component: {sample.component}")
        print(f"    Lifecycle State: {sample.lifecycle_state}")
        print(f"    Message: {sample.message}")

# Tool interactions
if tool_interactions_count > 0:
    print("\nTool Interactions sample:")
    tool_sample = db_session.query(ToolInteraction).first()
    print(f"  ID: {tool_sample.id}")
    print(f"  Event ID: {tool_sample.event_id}")
    print(f"  Tool Name: {tool_sample.tool_name}")
    print(f"  Interaction Type: {tool_sample.interaction_type}")
    print(f"  Status: {tool_sample.status}")
    print(f"  Parameters: {tool_sample.parameters}")
    print(f"  Result: {tool_sample.result}")
    print(f"  Request Timestamp: {tool_sample.request_timestamp}")
    print(f"  Response Timestamp: {tool_sample.response_timestamp}")
    print(f"  Duration (ms): {tool_sample.duration_ms}")
    
    # Display all tool interactions
    print("\nAll Tool Interactions:")
    all_tools = db_session.query(ToolInteraction).all()
    for i, tool in enumerate(all_tools):
        print(f"  Tool {i+1}:")
        print(f"    ID: {tool.id}")
        print(f"    Tool Name: {tool.tool_name}")
        print(f"    Interaction Type: {tool.interaction_type}")
        print(f"    Status: {tool.status}")
        print(f"    Parameters: {tool.get_parameters_dict()}")
        print(f"    Result: {tool.get_result_dict()}")
        print(f"    Duration (ms): {tool.duration_ms}")
    
    # Test the complete tool interactions feature
    print("\nComplete Tool Interaction Cycles:")
    complete_cycles = ToolInteraction.get_complete_interactions(db_session)
    print(f"Found {len(complete_cycles)} complete tool interaction cycles")
    
    for i, (execution, result) in enumerate(complete_cycles):
        print(f"  Cycle {i+1}:")
        print(f"    Execution ID: {execution.id}")
        print(f"    Tool Name: {execution.tool_name}")
        print(f"    Status: {execution.status}")
        print(f"    Duration (ms): {execution.duration_ms}")
        
        # Get the events to show span_id
        exec_event = db_session.query(Event).filter(Event.id == execution.event_id).first()
        if exec_event:
            print(f"    Span ID: {exec_event.span_id}")
        
        if result:
            print(f"    Has matching result: Yes")
            print(f"    Result ID: {result.id}")
        else:
            print(f"    Has matching result: No")
    
    # Test success rate calculation
    success_rate = ToolInteraction.calculate_success_rate(db_session)
    print(f"\nTool Interaction Success Rate: {success_rate:.1f}%")
    
    # Test average duration calculation
    avg_duration = ToolInteraction.get_average_duration(db_session)
    print(f"Average Tool Interaction Duration: {avg_duration:.1f} ms")

# Sessions
if sessions_count > 0:
    print("\nSessions sample:")
    session_sample = db_session.query(SessionModel).first()
    print(f"  ID: {session_sample.id}")
    print(f"  Session ID: {session_sample.session_id}")
    print(f"  Agent ID: {session_sample.agent_id}")
    print(f"  Start timestamp: {session_sample.start_timestamp}")
    print(f"  End timestamp: {session_sample.end_timestamp}")
    print(f"  Duration: {session_sample.duration_seconds} seconds")
    print(f"  Status: {session_sample.get_status()}")

# Traces
if traces_count > 0:
    print("\nTraces sample:")
    trace_sample = db_session.query(Trace).first()
    print(f"  ID: {trace_sample.id}")
    print(f"  Trace ID: {trace_sample.trace_id}")
    print(f"  Agent ID: {trace_sample.agent_id}")

# Spans
if spans_count > 0:
    print("\nSpans sample:")
    span_sample = db_session.query(Span).first()
    print(f"  ID: {span_sample.span_id}")
    print(f"  Span ID: {span_sample.span_id}")
    print(f"  Parent Span ID: {span_sample.parent_span_id}")
    print(f"  Trace ID: {span_sample.trace_id}")

print(f"\nDatabase file location: {DB_PATH}")
print("You can examine the database using SQLite tools like DB Browser for SQLite")
print("Sample commands to query the database using sqlite3:")
print(f"  sqlite3 {DB_PATH} 'SELECT COUNT(*) FROM events'")
print(f"  sqlite3 {DB_PATH} 'SELECT COUNT(*) FROM llm_interactions'")
print(f"  sqlite3 {DB_PATH} 'SELECT COUNT(*) FROM sessions'")
print(f"  sqlite3 {DB_PATH} 'SELECT session_id, start_timestamp, end_timestamp FROM sessions'")
print(f"  sqlite3 {DB_PATH} 'SELECT DISTINCT event_type FROM events'")

def debug_llm_parameters():
    """Debug the extraction of LLM parameters from the database."""
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
    import json
    
    # Create engine and session
    engine = create_engine(f"sqlite:////{DB_PATH}")
    Session = sessionmaker(bind=engine)
    db_session = Session()
    
    # Get all LLM interactions
    llm_interactions = db_session.execute(text("""
        SELECT 
            li.id, 
            li.event_id,
            li.interaction_type,
            li.vendor,
            li.model,
            li.temperature,
            li.max_tokens,
            li.raw_attributes
        FROM llm_interactions li
    """)).fetchall()
    
    print(f"Found {len(llm_interactions)} LLM interactions")
    
    # Iterate through each interaction
    for interaction in llm_interactions[:5]:  # Check first 5 for brevity
        interaction_id = interaction[0]
        event_id = interaction[1]
        interaction_type = interaction[2]
        vendor = interaction[3]
        temperature = interaction[5] 
        max_tokens = interaction[6]
        raw_attributes_json = interaction[7]
        
        print(f"\nAnalyzing interaction {interaction_id} (event_id: {event_id}, type: {interaction_type}, vendor: {vendor})")
        print(f"  Stored temperature: {temperature}")
        print(f"  Stored max_tokens: {max_tokens}")
        
        # Parse raw attributes
        if raw_attributes_json:
            try:
                raw_attributes = json.loads(raw_attributes_json)
                print(f"  Raw attributes available: {len(raw_attributes)} keys")
                
                # Check temperature possibilities
                print("  Checking temperature fields:")
                temperature_keys = [
                    'temperature', 'llm.temperature', 'llm.request.temperature',
                    'llm.request.data.temperature'
                ]
                for key in temperature_keys:
                    if key in raw_attributes:
                        print(f"    ✓ {key}: {raw_attributes[key]}")
                    else:
                        print(f"    ✗ {key}: not found")
                
                # Check max_tokens possibilities
                print("  Checking max_tokens fields:")
                max_tokens_keys = [
                    'max_tokens', 'llm.max_tokens', 'llm.request.max_tokens',
                    'llm.request.data.max_tokens', 'llm.request.max_tokens_to_sample'
                ]
                for key in max_tokens_keys:
                    if key in raw_attributes:
                        print(f"    ✓ {key}: {raw_attributes[key]}")
                    else:
                        print(f"    ✗ {key}: not found")
                
                # Check if we have request_data
                if 'llm.request.data' in raw_attributes:
                    try:
                        request_data = raw_attributes['llm.request.data']
                        if isinstance(request_data, str):
                            request_data = json.loads(request_data)
                        
                        print("  Request data structure:")
                        print(f"    Keys: {list(request_data.keys())}")
                        
                        # Look for parameters in request_data
                        if 'temperature' in request_data:
                            print(f"    ✓ request_data['temperature']: {request_data['temperature']}")
                        
                        if 'max_tokens' in request_data:
                            print(f"    ✓ request_data['max_tokens']: {request_data['max_tokens']}")
                        
                        # Anthropic-specific
                        if 'max_tokens_to_sample' in request_data:
                            print(f"    ✓ request_data['max_tokens_to_sample']: {request_data['max_tokens_to_sample']}")
                    except Exception as e:
                        print(f"  Error parsing request_data: {str(e)}")
            except Exception as e:
                print(f"  Error parsing raw_attributes: {str(e)}")
        else:
            print("  No raw attributes available")
    
    db_session.close()

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Main processing - the entire script from the beginning until the DATABASE EVALUATION section
    # We don't need to call a function here as the processing code is already in the global scope
    
    # Debug LLM parameters extraction
    print("\n" + "=" * 50)
    print("LLM PARAMETERS DEBUG")
    print("=" * 50)
    debug_llm_parameters() 