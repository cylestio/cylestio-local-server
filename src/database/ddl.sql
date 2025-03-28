-- Cylestio Local Server Database Schema
-- SQLite DDL Script

-- Enable foreign keys
PRAGMA foreign_keys = ON;

-- Agents Table
CREATE TABLE agents (
    agent_id TEXT PRIMARY KEY,
    first_seen_timestamp TIMESTAMP NOT NULL,
    last_seen_timestamp TIMESTAMP NOT NULL,
    version TEXT,
    monitoring_version TEXT,
    environment JSON
);

CREATE INDEX idx_agents_timestamps ON agents(first_seen_timestamp, last_seen_timestamp);

-- Sessions Table
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    start_timestamp TIMESTAMP NOT NULL,
    end_timestamp TIMESTAMP,
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
);

CREATE INDEX idx_sessions_agent_id ON sessions(agent_id);
CREATE INDEX idx_sessions_timestamps ON sessions(start_timestamp, end_timestamp);

-- Traces Table
CREATE TABLE traces (
    trace_id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    start_timestamp TIMESTAMP,
    end_timestamp TIMESTAMP,
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
);

CREATE INDEX idx_traces_agent_id ON traces(agent_id);
CREATE INDEX idx_traces_timestamps ON traces(start_timestamp, end_timestamp);

-- Spans Table
CREATE TABLE spans (
    span_id TEXT PRIMARY KEY,
    trace_id TEXT NOT NULL,
    parent_span_id TEXT,
    name TEXT,
    start_timestamp TIMESTAMP,
    end_timestamp TIMESTAMP,
    FOREIGN KEY (trace_id) REFERENCES traces(trace_id)
);

CREATE INDEX idx_spans_trace_id ON spans(trace_id);
CREATE INDEX idx_spans_parent_id ON spans(parent_span_id);

-- Events Table
CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT NOT NULL,
    session_id TEXT,
    trace_id TEXT,
    span_id TEXT,
    parent_span_id TEXT,
    timestamp TIMESTAMP NOT NULL,
    schema_version TEXT NOT NULL,
    name TEXT NOT NULL,
    level TEXT NOT NULL,
    event_type TEXT NOT NULL,
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id),
    FOREIGN KEY (session_id) REFERENCES sessions(session_id),
    FOREIGN KEY (trace_id) REFERENCES traces(trace_id),
    FOREIGN KEY (span_id) REFERENCES spans(span_id)
);

CREATE INDEX idx_events_agent_id ON events(agent_id);
CREATE INDEX idx_events_session_id ON events(session_id);
CREATE INDEX idx_events_trace_id ON events(trace_id);
CREATE INDEX idx_events_timestamp ON events(timestamp);
CREATE INDEX idx_events_name ON events(name);
CREATE INDEX idx_events_type ON events(event_type);
CREATE INDEX idx_events_agent_timestamp ON events(agent_id, timestamp);
CREATE INDEX idx_events_agent_type ON events(agent_id, event_type);
CREATE INDEX idx_events_session_trace_span ON events(session_id, trace_id, span_id);
CREATE INDEX idx_events_span_parent_span ON events(span_id, parent_span_id);
CREATE INDEX idx_events_name_timestamp ON events(name, timestamp);

-- LLM Interactions Table
CREATE TABLE llm_interactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL,
    interaction_type TEXT NOT NULL,
    vendor TEXT NOT NULL,
    model TEXT NOT NULL,
    request_timestamp TIMESTAMP,
    response_timestamp TIMESTAMP,
    duration_ms INTEGER,
    input_tokens INTEGER,
    output_tokens INTEGER,
    total_tokens INTEGER,
    request_data JSON,
    response_content JSON,
    response_id TEXT,
    stop_reason TEXT,
    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE
);

CREATE INDEX idx_llm_event_id ON llm_interactions(event_id);
CREATE INDEX idx_llm_model ON llm_interactions(model);
CREATE INDEX idx_llm_vendor ON llm_interactions(vendor);
CREATE INDEX idx_llm_timestamps ON llm_interactions(request_timestamp, response_timestamp);

-- Tool Interactions Table
CREATE TABLE tool_interactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL,
    tool_name TEXT NOT NULL,
    tool_id TEXT,
    interaction_type TEXT NOT NULL,
    params JSON,
    status TEXT,
    result_type TEXT,
    result_data JSON,
    framework_name TEXT,
    framework_type TEXT,
    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE
);

CREATE INDEX idx_tool_event_id ON tool_interactions(event_id);
CREATE INDEX idx_tool_name ON tool_interactions(tool_name);
CREATE INDEX idx_tool_status ON tool_interactions(status);

-- Security Alerts Table
CREATE TABLE security_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL,
    alert_level TEXT NOT NULL,
    keywords JSON,
    content_sample TEXT,
    detection_timestamp TIMESTAMP NOT NULL,
    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE
);

CREATE INDEX idx_security_event_id ON security_alerts(event_id);
CREATE INDEX idx_security_level ON security_alerts(alert_level);
CREATE INDEX idx_security_timestamp ON security_alerts(detection_timestamp);

-- Security Alert Triggers Table
CREATE TABLE security_alert_triggers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    security_alert_id INTEGER NOT NULL,
    triggering_event_id INTEGER NOT NULL,
    FOREIGN KEY (security_alert_id) REFERENCES security_alerts(id) ON DELETE CASCADE,
    FOREIGN KEY (triggering_event_id) REFERENCES events(id) ON DELETE CASCADE
);

CREATE INDEX idx_security_alert_triggers ON security_alert_triggers(security_alert_id, triggering_event_id);

-- Framework Events Table
CREATE TABLE framework_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL,
    framework_name TEXT NOT NULL,
    framework_type TEXT,
    action TEXT NOT NULL,
    patch_type TEXT,
    patch_components JSON,
    version TEXT,
    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE
);

CREATE INDEX idx_framework_event_id ON framework_events(event_id);
CREATE INDEX idx_framework_name ON framework_events(framework_name);
CREATE INDEX idx_framework_action ON framework_events(action);

-- LLM Attributes Table
CREATE TABLE llm_attributes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    llm_interaction_id INTEGER NOT NULL,
    key TEXT NOT NULL,
    value_text TEXT,
    value_numeric REAL,
    value_boolean BOOLEAN,
    value_type TEXT NOT NULL,
    FOREIGN KEY (llm_interaction_id) REFERENCES llm_interactions(id) ON DELETE CASCADE
);

CREATE INDEX idx_llm_attr_interaction_id ON llm_attributes(llm_interaction_id);
CREATE INDEX idx_llm_attr_key ON llm_attributes(key);

-- Tool Attributes Table
CREATE TABLE tool_attributes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tool_interaction_id INTEGER NOT NULL,
    key TEXT NOT NULL,
    value_text TEXT,
    value_numeric REAL,
    value_boolean BOOLEAN,
    value_type TEXT NOT NULL,
    FOREIGN KEY (tool_interaction_id) REFERENCES tool_interactions(id) ON DELETE CASCADE
);

CREATE INDEX idx_tool_attr_interaction_id ON tool_attributes(tool_interaction_id);
CREATE INDEX idx_tool_attr_key ON tool_attributes(key);

-- Security Attributes Table
CREATE TABLE security_attributes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    security_alert_id INTEGER NOT NULL,
    key TEXT NOT NULL,
    value_text TEXT,
    value_numeric REAL,
    value_boolean BOOLEAN,
    value_type TEXT NOT NULL,
    FOREIGN KEY (security_alert_id) REFERENCES security_alerts(id) ON DELETE CASCADE
);

CREATE INDEX idx_security_attr_alert_id ON security_attributes(security_alert_id);
CREATE INDEX idx_security_attr_key ON security_attributes(key);

-- Framework Attributes Table
CREATE TABLE framework_attributes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    framework_event_id INTEGER NOT NULL,
    key TEXT NOT NULL,
    value_text TEXT,
    value_numeric REAL,
    value_boolean BOOLEAN,
    value_type TEXT NOT NULL,
    FOREIGN KEY (framework_event_id) REFERENCES framework_events(id) ON DELETE CASCADE
);

CREATE INDEX idx_framework_attr_event_id ON framework_attributes(framework_event_id);
CREATE INDEX idx_framework_attr_key ON framework_attributes(key); 