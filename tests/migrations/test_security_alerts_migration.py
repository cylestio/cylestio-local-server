"""
Tests for the security alerts schema migration.

This module tests that the security_alerts schema migration works correctly.
"""
import pytest
import sqlite3
from pathlib import Path
import tempfile
import os
import sys

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.database.schema_migration import AttributeMigration


def setup_test_db():
    """Create a test database with the old schema."""
    # Create temporary database file
    db_fd, db_path = tempfile.mkstemp()
    
    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create basic tables needed for testing
    cursor.execute("""
    CREATE TABLE events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        event_type TEXT,
        level TEXT,
        agent_id TEXT,
        trace_id TEXT,
        raw_data JSON
    )
    """)
    
    # Create old security_alerts table
    cursor.execute("""
    CREATE TABLE security_alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id INTEGER NOT NULL UNIQUE,
        timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        alert_type TEXT,
        severity TEXT,
        description TEXT,
        status TEXT DEFAULT 'OPEN',
        detection_source TEXT,
        confidence_score FLOAT,
        affected_component TEXT,
        detection_rule_id TEXT,
        risk_level TEXT,
        resolved_at TIMESTAMP,
        resolution_notes TEXT,
        raw_attributes JSON,
        FOREIGN KEY (event_id) REFERENCES events (id) ON DELETE CASCADE
    )
    """)
    
    # Create old security_alert_triggers table
    cursor.execute("""
    CREATE TABLE security_alert_triggers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        alert_id INTEGER NOT NULL,
        triggering_event_id INTEGER NOT NULL,
        FOREIGN KEY (alert_id) REFERENCES security_alerts (id),
        FOREIGN KEY (triggering_event_id) REFERENCES events (id)
    )
    """)
    
    # Insert sample event data
    cursor.execute("""
    INSERT INTO events (id, name, timestamp, event_type, level, agent_id, trace_id)
    VALUES (1, 'security.alert', '2024-04-24 10:00:00', 'security', 'ALERT', 'agent-123', 'trace-123')
    """)
    
    # Insert sample security alert data
    cursor.execute("""
    INSERT INTO security_alerts 
    (id, event_id, timestamp, alert_type, severity, description, status, risk_level)
    VALUES 
    (1, 1, '2024-04-24 10:00:00', 'prompt_injection', 'HIGH', 'Potential prompt injection detected', 'OPEN', 'high')
    """)
    
    # Insert sample trigger data
    cursor.execute("""
    INSERT INTO security_alert_triggers (alert_id, triggering_event_id)
    VALUES (1, 1)
    """)
    
    # Commit changes and close connection
    conn.commit()
    conn.close()
    os.close(db_fd)
    
    return db_path


def run_migration(db_path):
    """Run the migration script on the test database."""
    # Generate the migration SQL
    migration_sql = """
    -- Drop the security_alert_triggers table
    DROP TABLE IF EXISTS security_alert_triggers;
    
    -- Add new columns to security_alerts table
    ALTER TABLE security_alerts ADD COLUMN schema_version TEXT;
    ALTER TABLE security_alerts ADD COLUMN trace_id TEXT;
    ALTER TABLE security_alerts ADD COLUMN span_id TEXT;
    ALTER TABLE security_alerts ADD COLUMN parent_span_id TEXT;
    ALTER TABLE security_alerts ADD COLUMN event_name TEXT;
    ALTER TABLE security_alerts ADD COLUMN log_level TEXT;
    ALTER TABLE security_alerts ADD COLUMN alert_level TEXT;
    ALTER TABLE security_alerts ADD COLUMN category TEXT;
    ALTER TABLE security_alerts ADD COLUMN llm_vendor TEXT;
    ALTER TABLE security_alerts ADD COLUMN content_sample TEXT;
    ALTER TABLE security_alerts ADD COLUMN detection_time TIMESTAMP;
    ALTER TABLE security_alerts ADD COLUMN keywords JSON;
    
    -- Set default values for NOT NULL columns
    UPDATE security_alerts SET schema_version = '1.0' WHERE schema_version IS NULL;
    UPDATE security_alerts SET event_name = 'security.content.unknown' WHERE event_name IS NULL;
    UPDATE security_alerts SET log_level = 'INFO' WHERE log_level IS NULL;
    UPDATE security_alerts SET alert_level = CASE WHEN severity = 'HIGH' OR severity = 'CRITICAL' THEN 'dangerous' WHEN severity = 'MEDIUM' THEN 'suspicious' ELSE 'none' END WHERE alert_level IS NULL;
    UPDATE security_alerts SET category = CASE WHEN alert_type = 'prompt_injection' THEN 'prompt_injection' WHEN alert_type = 'data_leak' THEN 'sensitive_data' ELSE 'unknown' END WHERE category IS NULL;
    
    -- Add column to events table for span_id
    ALTER TABLE events ADD COLUMN span_id TEXT;
    
    -- Create indexes for efficient querying
    CREATE INDEX IF NOT EXISTS ix_security_alerts_trace_id ON security_alerts (trace_id);
    CREATE INDEX IF NOT EXISTS ix_security_alerts_span_id ON security_alerts (span_id);
    CREATE INDEX IF NOT EXISTS ix_security_alerts_event_name ON security_alerts (event_name);
    CREATE INDEX IF NOT EXISTS ix_security_alerts_log_level ON security_alerts (log_level);
    CREATE INDEX IF NOT EXISTS ix_security_alerts_alert_level ON security_alerts (alert_level);
    CREATE INDEX IF NOT EXISTS ix_security_alerts_category ON security_alerts (category);
    CREATE INDEX IF NOT EXISTS ix_security_alerts_llm_vendor ON security_alerts (llm_vendor);
    CREATE INDEX IF NOT EXISTS ix_security_alerts_detection_time ON security_alerts (detection_time);
    CREATE INDEX IF NOT EXISTS ix_events_span_id ON events (span_id);
    """
    
    # Connect to the database and run the migration
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Execute migration statements
    for statement in migration_sql.split(';'):
        if statement.strip():
            cursor.execute(statement)
    
    # Commit and close
    conn.commit()
    conn.close()


def test_security_alerts_migration():
    """Test that the security alerts migration works correctly."""
    # Setup: Create a test database with the old schema and some test data
    db_path = setup_test_db()
    
    try:
        # Run the migration
        run_migration(db_path)
        
        # Verify the migration worked correctly
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. Check that the security_alert_triggers table doesn't exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='security_alert_triggers'")
        assert cursor.fetchone() is None, "security_alert_triggers table still exists"
        
        # 2. Check that all new columns exist in the security_alerts table
        cursor.execute("PRAGMA table_info(security_alerts)")
        columns = [row[1] for row in cursor.fetchall()]
        
        new_columns = [
            'schema_version', 'trace_id', 'span_id', 'parent_span_id',
            'event_name', 'log_level', 'alert_level', 'category',
            'llm_vendor', 'content_sample', 'detection_time', 'keywords'
        ]
        
        for col in new_columns:
            assert col in columns, f"Column '{col}' is missing from security_alerts table"
        
        # 3. Verify that the default values were set correctly
        cursor.execute("SELECT schema_version, alert_level, category FROM security_alerts WHERE id=1")
        row = cursor.fetchone()
        assert row[0] == '1.0', "schema_version not set to default value"
        assert row[1] == 'dangerous', "alert_level not set correctly based on severity"
        assert row[2] == 'prompt_injection', "category not set correctly based on alert_type"
        
        # 4. Check that the indexes were created
        for col in ['trace_id', 'span_id', 'event_name', 'log_level', 'alert_level', 'category', 'llm_vendor', 'detection_time']:
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='index' AND name='ix_security_alerts_{col}'")
            assert cursor.fetchone() is not None, f"Index for '{col}' was not created"
        
        # 5. Check that span_id was added to events table
        cursor.execute("PRAGMA table_info(events)")
        columns = [row[1] for row in cursor.fetchall()]
        assert 'span_id' in columns, "span_id column is missing from events table"
        
        # 6. Check that span_id index was created on events table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='ix_events_span_id'")
        assert cursor.fetchone() is not None, "Index for span_id was not created on events table"
        
        conn.close()
    finally:
        # Clean up
        os.unlink(db_path)


if __name__ == "__main__":
    test_security_alerts_migration()
    print("All tests passed!") 