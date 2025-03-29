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

# Add the current directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from models.base import init_db, get_db, create_all
from models.event import Event
from models.llm_interaction import LLMInteraction
# LLMAttribute does not exist in the codebase
from models.security_alert import SecurityAlert
from models.framework_event import FrameworkEvent
from models.tool_interaction import ToolInteraction
from models.agent import Agent
from models.session import Session as SessionModel
from models.trace import Trace
from models.span import Span
from processing.simple_processor import SimpleProcessor

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
if not example_file.exists():
    # Try current directory parent (project root)
    example_file = Path(__file__).parent.parent / "example_records.json"

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
# LLMAttribute doesn't exist as a separate model, attributes are stored in raw_attributes field of LLMInteraction
security_alerts_count = db_session.query(func.count(SecurityAlert.id)).scalar()
framework_events_count = db_session.query(func.count(FrameworkEvent.id)).scalar()
tool_interactions_count = db_session.query(func.count(ToolInteraction.id)).scalar()
sessions_count = db_session.query(func.count(SessionModel.id)).scalar()
traces_count = db_session.query(func.count(Trace.id)).scalar()
spans_count = db_session.query(func.count(Span.span_id)).scalar()

print(f"Events: {events_count}")
print(f"LLM Interactions: {llm_interactions_count}")
# No more LLMAttributes count
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
    
    # Get attributes from raw_attributes instead of LLMAttribute table
    raw_attributes = llm_sample.raw_attributes or {}
    print(f"  Attributes count: {len(raw_attributes)}")
    for key, value in raw_attributes.items():
        # Only show a preview of long values
        value_str = str(value)
        print(f"    {key}: {value_str[:50]}..." if len(value_str) > 50 else f"    {key}: {value_str}")

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

# Tool interactions
if tool_interactions_count > 0:
    print("\nTool Interactions sample:")
    tool_sample = db_session.query(ToolInteraction).first()
    print(f"  ID: {tool_sample.id}")
    print(f"  Event ID: {tool_sample.event_id}")
    print(f"  Tool Name: {tool_sample.tool_name}")

# Sessions
if sessions_count > 0:
    print("\nSessions sample:")
    session_sample = db_session.query(SessionModel).first()
    print(f"  ID: {session_sample.id}")
    print(f"  Session ID: {session_sample.session_id}")
    print(f"  Agent ID: {session_sample.agent_id}")

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
    print(f"  Span ID: {span_sample.span_id}")
    print(f"  Parent Span ID: {span_sample.parent_span_id}")
    print(f"  Trace ID: {span_sample.trace_id}")

print(f"\nDatabase file location: {DB_PATH}")
print("You can examine the database using SQLite tools like DB Browser for SQLite")
print("Sample commands to query the database using sqlite3:")
print(f"  sqlite3 {DB_PATH} 'SELECT COUNT(*) FROM events'")
print(f"  sqlite3 {DB_PATH} 'SELECT COUNT(*) FROM llm_interactions'")
print(f"  sqlite3 {DB_PATH} 'SELECT COUNT(*) FROM security_alerts'")
print(f"  sqlite3 {DB_PATH} 'SELECT DISTINCT event_type FROM events'")
print(f"  sqlite3 {DB_PATH} 'SELECT * FROM security_alerts LIMIT 5'") 