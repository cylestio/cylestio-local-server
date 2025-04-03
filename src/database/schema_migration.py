"""
Schema migration script for Task 04-01: Database Design and Processing Fixes.

This script applies the schema changes and migrates data from the EAV pattern
to a more efficient JSON storage format.
"""
import json
import logging
import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Tuple
import os
from datetime import datetime

from src.models.base import Base, engine, drop_all, create_all
from src.utils.logging import get_logger

# Set up logger
logger = get_logger(__name__)

class AttributeMigration:
    """
    Handles the migration of attributes from the EAV pattern to JSON format.
    """
    
    def __init__(self, db_path: str):
        """
        Initialize with the path to the SQLite database.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        
    def __enter__(self):
        """Context manager entry."""
        self.conn = sqlite3.connect(self.db_path)
        # Enable foreign keys
        self.conn.execute("PRAGMA foreign_keys = ON")
        # Enable JSON functions
        self.conn.enable_load_extension(True)
        try:
            self.conn.load_extension("json1")
        except sqlite3.OperationalError:
            logger.warning("Could not load JSON1 extension - JSON functions may not be available")
        self.conn.enable_load_extension(False)
        self.cursor = self.conn.cursor()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self.conn:
            self.conn.close()
    
    def apply_schema_changes(self):
        """Apply the schema changes from the SQL file."""
        try:
            with open(Path(__file__).parent / "ddl_fixes.sql", "r") as f:
                sql = f.read()
                
            # Split the SQL into individual statements
            statements = sql.split(';')
            
            for statement in statements:
                # Skip empty statements
                if statement.strip():
                    try:
                        self.cursor.execute(statement)
                        self.conn.commit()
                    except sqlite3.Error as e:
                        logger.error(f"Error executing SQL: {statement}")
                        logger.error(f"Error details: {str(e)}")
                        
            logger.info("Schema changes applied successfully")
            
        except Exception as e:
            logger.error(f"Error applying schema changes: {str(e)}")
            raise
    
    def migrate_attributes(self):
        """Migrate all attributes from EAV to JSON format."""
        try:
            self.migrate_llm_attributes()
            self.migrate_security_attributes()
            self.migrate_tool_attributes()
            self.migrate_framework_attributes()
            self.link_llm_interactions()
            logger.info("Attribute migration completed successfully")
        except Exception as e:
            logger.error(f"Error migrating attributes: {str(e)}")
            raise
    
    def migrate_llm_attributes(self):
        """Migrate LLM attributes from EAV to JSON format."""
        logger.info("Migrating LLM attributes...")
        
        # Get all LLM interaction IDs
        self.cursor.execute("SELECT id FROM llm_interactions")
        interaction_ids = [row[0] for row in self.cursor.fetchall()]
        
        for interaction_id in interaction_ids:
            # Get all attributes for this interaction
            self.cursor.execute(
                """
                SELECT key, value_text, value_numeric, value_boolean, value_type 
                FROM llm_attributes 
                WHERE llm_interaction_id = ?
                """, 
                (interaction_id,)
            )
            
            attributes = {}
            for key, value_text, value_numeric, value_boolean, value_type in self.cursor.fetchall():
                if value_type == 'text':
                    attributes[key] = value_text
                elif value_type == 'numeric':
                    attributes[key] = value_numeric
                elif value_type == 'boolean':
                    attributes[key] = bool(value_boolean)
                elif value_type == 'json' and value_text:
                    try:
                        attributes[key] = json.loads(value_text)
                    except json.JSONDecodeError:
                        attributes[key] = value_text
            
            # Store the raw JSON attributes
            if attributes:
                self.cursor.execute(
                    "UPDATE llm_interactions SET raw_attributes = ? WHERE id = ?",
                    (json.dumps(attributes), interaction_id)
                )
                
                # Extract specific attributes to dedicated columns
                # For each potential attribute, check if it exists and update the column
                updates = []
                params = []
                
                # Temperature
                if 'temperature' in attributes or 'llm.temperature' in attributes:
                    updates.append("temperature = ?")
                    params.append(attributes.get('temperature') or attributes.get('llm.temperature'))
                
                # Top P
                if 'top_p' in attributes or 'llm.top_p' in attributes:
                    updates.append("top_p = ?")
                    params.append(attributes.get('top_p') or attributes.get('llm.top_p'))
                
                # Max tokens
                if 'max_tokens' in attributes or 'llm.max_tokens' in attributes:
                    updates.append("max_tokens = ?")
                    params.append(attributes.get('max_tokens') or attributes.get('llm.max_tokens'))
                
                # Frequency penalty
                if 'frequency_penalty' in attributes or 'llm.frequency_penalty' in attributes:
                    updates.append("frequency_penalty = ?")
                    params.append(attributes.get('frequency_penalty') or attributes.get('llm.frequency_penalty'))
                
                # Presence penalty
                if 'presence_penalty' in attributes or 'llm.presence_penalty' in attributes:
                    updates.append("presence_penalty = ?")
                    params.append(attributes.get('presence_penalty') or attributes.get('llm.presence_penalty'))
                
                # Session ID
                if 'session.id' in attributes:
                    updates.append("session_id = ?")
                    params.append(attributes.get('session.id'))
                
                # User ID
                if 'user.id' in attributes:
                    updates.append("user_id = ?")
                    params.append(attributes.get('user.id'))
                
                # Prompt template ID
                if 'prompt.template_id' in attributes:
                    updates.append("prompt_template_id = ?")
                    params.append(attributes.get('prompt.template_id'))
                
                # Stream
                if 'stream' in attributes or 'llm.stream' in attributes:
                    updates.append("stream = ?")
                    params.append(attributes.get('stream') or attributes.get('llm.stream'))
                
                # Cached response
                if 'cached_response' in attributes or 'llm.cached_response' in attributes:
                    updates.append("cached_response = ?")
                    params.append(attributes.get('cached_response') or attributes.get('llm.cached_response'))
                
                # Model version
                if 'model_version' in attributes or 'llm.model_version' in attributes:
                    updates.append("model_version = ?")
                    params.append(attributes.get('model_version') or attributes.get('llm.model_version'))
                
                # If we have any extracted attributes, update the interaction
                if updates and params:
                    sql = f"UPDATE llm_interactions SET {', '.join(updates)} WHERE id = ?"
                    params.append(interaction_id)
                    self.cursor.execute(sql, params)
        
        self.conn.commit()
        logger.info(f"Migrated attributes for {len(interaction_ids)} LLM interactions")
    
    def migrate_security_attributes(self):
        """Migrate security attributes from EAV to JSON format."""
        logger.info("Migrating security attributes...")
        
        # Get all security alert IDs
        self.cursor.execute("SELECT id FROM security_alerts")
        alert_ids = [row[0] for row in self.cursor.fetchall()]
        
        for alert_id in alert_ids:
            # Get all attributes for this alert
            self.cursor.execute(
                """
                SELECT key, value_text, value_numeric, value_boolean, value_type 
                FROM security_attributes 
                WHERE security_alert_id = ?
                """, 
                (alert_id,)
            )
            
            attributes = {}
            for key, value_text, value_numeric, value_boolean, value_type in self.cursor.fetchall():
                if value_type == 'text':
                    attributes[key] = value_text
                elif value_type == 'numeric':
                    attributes[key] = value_numeric
                elif value_type == 'boolean':
                    attributes[key] = bool(value_boolean)
                elif value_type == 'json' and value_text:
                    try:
                        attributes[key] = json.loads(value_text)
                    except json.JSONDecodeError:
                        attributes[key] = value_text
            
            # Store the JSON attributes
            if attributes:
                self.cursor.execute(
                    "UPDATE security_alerts SET attributes = ? WHERE id = ?",
                    (json.dumps(attributes), alert_id)
                )
        
        self.conn.commit()
        logger.info(f"Migrated attributes for {len(alert_ids)} security alerts")
    
    def migrate_tool_attributes(self):
        """Migrate tool attributes from EAV to JSON format."""
        logger.info("Migrating tool attributes...")
        
        # Get all tool interaction IDs
        self.cursor.execute("SELECT id FROM tool_interactions")
        interaction_ids = [row[0] for row in self.cursor.fetchall()]
        
        for interaction_id in interaction_ids:
            # Get all attributes for this interaction
            self.cursor.execute(
                """
                SELECT key, value_text, value_numeric, value_boolean, value_type 
                FROM tool_attributes 
                WHERE tool_interaction_id = ?
                """, 
                (interaction_id,)
            )
            
            attributes = {}
            for key, value_text, value_numeric, value_boolean, value_type in self.cursor.fetchall():
                if value_type == 'text':
                    attributes[key] = value_text
                elif value_type == 'numeric':
                    attributes[key] = value_numeric
                elif value_type == 'boolean':
                    attributes[key] = bool(value_boolean)
                elif value_type == 'json' and value_text:
                    try:
                        attributes[key] = json.loads(value_text)
                    except json.JSONDecodeError:
                        attributes[key] = value_text
            
            # Store the JSON attributes
            if attributes:
                self.cursor.execute(
                    "UPDATE tool_interactions SET attributes = ? WHERE id = ?",
                    (json.dumps(attributes), interaction_id)
                )
        
        self.conn.commit()
        logger.info(f"Migrated attributes for {len(interaction_ids)} tool interactions")
    
    def migrate_framework_attributes(self):
        """Migrate framework attributes from EAV to JSON format."""
        logger.info("Migrating framework attributes...")
        
        # Get all framework event IDs
        self.cursor.execute("SELECT id FROM framework_events")
        event_ids = [row[0] for row in self.cursor.fetchall()]
        
        for event_id in event_ids:
            # Get all attributes for this event
            self.cursor.execute(
                """
                SELECT key, value_text, value_numeric, value_boolean, value_type 
                FROM framework_attributes 
                WHERE framework_event_id = ?
                """, 
                (event_id,)
            )
            
            attributes = {}
            for key, value_text, value_numeric, value_boolean, value_type in self.cursor.fetchall():
                if value_type == 'text':
                    attributes[key] = value_text
                elif value_type == 'numeric':
                    attributes[key] = value_numeric
                elif value_type == 'boolean':
                    attributes[key] = bool(value_boolean)
                elif value_type == 'json' and value_text:
                    try:
                        attributes[key] = json.loads(value_text)
                    except json.JSONDecodeError:
                        attributes[key] = value_text
            
            # Store the JSON attributes
            if attributes:
                self.cursor.execute(
                    "UPDATE framework_events SET attributes = ? WHERE id = ?",
                    (json.dumps(attributes), event_id)
                )
        
        self.conn.commit()
        logger.info(f"Migrated attributes for {len(event_ids)} framework events")
    
    def link_llm_interactions(self):
        """Link related start and finish llm_interactions based on trace_id and span_id."""
        logger.info("Linking related LLM interactions...")
        
        # Find paired start/finish LLM interactions
        self.cursor.execute(
            """
            SELECT 
                s.id AS start_id, 
                f.id AS finish_id
            FROM 
                llm_interactions s
            JOIN 
                events e_s ON s.event_id = e_s.id
            JOIN 
                llm_interactions f ON f.interaction_type = 'finish'
            JOIN 
                events e_f ON f.event_id = e_f.id
            WHERE 
                s.interaction_type = 'start'
                AND e_s.trace_id = e_f.trace_id
                AND e_s.span_id = e_f.span_id
                AND e_s.span_id IS NOT NULL
            """
        )
        
        pairs = self.cursor.fetchall()
        logger.info(f"Found {len(pairs)} related LLM interaction pairs")
        
        # Update the relationships
        for start_id, finish_id in pairs:
            self.cursor.execute(
                "UPDATE llm_interactions SET related_interaction_id = ? WHERE id = ?",
                (finish_id, start_id)
            )
            self.cursor.execute(
                "UPDATE llm_interactions SET related_interaction_id = ? WHERE id = ?",
                (start_id, finish_id)
            )
        
        self.conn.commit()
        logger.info(f"Linked {len(pairs)} LLM interaction pairs")
    
    def populate_empty_tables(self):
        """Populate empty tables with data derived from existing records."""
        self.populate_sessions()
        self.populate_security_alert_triggers()
        self.populate_tool_interactions()
        
    def populate_sessions(self):
        """Populate the sessions table from session IDs in attributes."""
        logger.info("Populating sessions table...")
        
        # Find session IDs in event attributes
        self.cursor.execute(
            """
            SELECT DISTINCT 
                e.agent_id, 
                json_extract(li.attributes, '$.session.id') AS session_id,
                MIN(e.timestamp) AS start_timestamp
            FROM 
                events e
            JOIN 
                llm_interactions li ON e.id = li.event_id
            WHERE 
                json_extract(li.attributes, '$.session.id') IS NOT NULL
            GROUP BY 
                e.agent_id, session_id
            """
        )
        
        sessions = self.cursor.fetchall()
        
        for agent_id, session_id, start_timestamp in sessions:
            # Check if session already exists
            self.cursor.execute(
                "SELECT 1 FROM sessions WHERE session_id = ?", 
                (session_id,)
            )
            
            if not self.cursor.fetchone():
                # Create new session
                self.cursor.execute(
                    """
                    INSERT INTO sessions (agent_id, session_id, start_timestamp) 
                    VALUES (?, ?, ?)
                    """,
                    (agent_id, session_id, start_timestamp)
                )
                
                # Update events with this session ID
                self.cursor.execute(
                    """
                    UPDATE events 
                    SET session_id = ? 
                    WHERE id IN (
                        SELECT e.id 
                        FROM events e 
                        JOIN llm_interactions li ON e.id = li.event_id 
                        WHERE json_extract(li.attributes, '$.session.id') = ?
                    )
                    """,
                    (session_id, session_id)
                )
        
        self.conn.commit()
        logger.info(f"Populated {len(sessions)} sessions")
    
    def populate_security_alert_triggers(self):
        """Populate security_alert_triggers table by analyzing event relationships."""
        logger.info("Populating security_alert_triggers table...")
        
        # For each security alert, find potential triggering events
        self.cursor.execute("SELECT id, event_id FROM security_alerts")
        alerts = self.cursor.fetchall()
        
        for alert_id, alert_event_id in alerts:
            # Get the event details
            self.cursor.execute(
                "SELECT agent_id, timestamp FROM events WHERE id = ?", 
                (alert_event_id,)
            )
            agent_id, timestamp = self.cursor.fetchone()
            
            # Find potential triggering events
            # (events from the same agent that occurred shortly before the alert)
            self.cursor.execute(
                """
                SELECT id 
                FROM events 
                WHERE 
                    agent_id = ? 
                    AND timestamp < ? 
                    AND timestamp > datetime(?, '-1 minute')
                    AND id != ?
                ORDER BY timestamp DESC
                LIMIT 1
                """,
                (agent_id, timestamp, timestamp, alert_event_id)
            )
            
            result = self.cursor.fetchone()
            if result:
                triggering_event_id = result[0]
                
                # Create the trigger relationship
                self.cursor.execute(
                    """
                    INSERT INTO security_alert_triggers 
                    (security_alert_id, triggering_event_id) 
                    VALUES (?, ?)
                    """,
                    (alert_id, triggering_event_id)
                )
        
        self.conn.commit()
        logger.info(f"Populated triggers for {len(alerts)} security alerts")
    
    def populate_tool_interactions(self):
        """Populate tool_interactions table from tool events."""
        logger.info("Populating tool_interactions table...")
        
        # Find events of type 'tool'
        self.cursor.execute(
            """
            SELECT 
                id, agent_id, timestamp, name
            FROM 
                events 
            WHERE 
                event_type = 'tool'
            """
        )
        
        tool_events = self.cursor.fetchall()
        
        for event_id, agent_id, timestamp, name in tool_events:
            # Determine interaction type from name
            if '.execution' in name:
                interaction_type = 'execution'
            elif '.result' in name:
                interaction_type = 'result'
            else:
                interaction_type = 'other'
                
            # Extract tool name from event name
            tool_name = name.split('.')[0] if '.' in name else name
            
            # Create tool interaction
            self.cursor.execute(
                """
                INSERT INTO tool_interactions 
                (event_id, tool_name, interaction_type) 
                VALUES (?, ?, ?)
                """,
                (event_id, tool_name, interaction_type)
            )
        
        self.conn.commit()
        logger.info(f"Populated {len(tool_events)} tool interactions")
    
    def update_timestamps(self):
        """Update NULL timestamps in LLM interactions."""
        logger.info("Updating NULL timestamps...")
        
        # Update NULL request_timestamp for start records
        self.cursor.execute(
            """
            UPDATE llm_interactions
            SET request_timestamp = (
                SELECT timestamp 
                FROM events 
                WHERE events.id = llm_interactions.event_id
            )
            WHERE request_timestamp IS NULL
            AND interaction_type = 'start'
            """
        )
        
        # Update NULL response_timestamp for finish records
        self.cursor.execute(
            """
            UPDATE llm_interactions
            SET response_timestamp = (
                SELECT timestamp 
                FROM events 
                WHERE events.id = llm_interactions.event_id
            )
            WHERE response_timestamp IS NULL
            AND interaction_type = 'finish'
            """
        )
        
        self.conn.commit()
        
        # Count updated records
        self.cursor.execute(
            "SELECT COUNT(*) FROM llm_interactions WHERE interaction_type = 'start' AND request_timestamp IS NOT NULL"
        )
        start_count = self.cursor.fetchone()[0]
        
        self.cursor.execute(
            "SELECT COUNT(*) FROM llm_interactions WHERE interaction_type = 'finish' AND response_timestamp IS NOT NULL"
        )
        finish_count = self.cursor.fetchone()[0]
        
        logger.info(f"Updated {start_count} start records and {finish_count} finish records with timestamps")
    
    def verify_migration(self) -> Dict[str, Any]:
        """Verify the migration was successful and return statistics."""
        result = {
            "attributes_migration": {
                "llm_interactions_with_json": 0,
                "security_alerts_with_json": 0,
                "tool_interactions_with_json": 0,
                "framework_events_with_json": 0
            },
            "relationship_linking": {
                "linked_llm_pairs": 0
            },
            "empty_tables_population": {
                "sessions": 0,
                "security_alert_triggers": 0,
                "tool_interactions": 0
            },
            "null_values_fixed": {
                "request_timestamps": 0,
                "response_timestamps": 0
            }
        }
        
        # Check LLM interactions with JSON
        self.cursor.execute(
            "SELECT COUNT(*) FROM llm_interactions WHERE attributes IS NOT NULL"
        )
        result["attributes_migration"]["llm_interactions_with_json"] = self.cursor.fetchone()[0]
        
        # Check security alerts with JSON
        self.cursor.execute(
            "SELECT COUNT(*) FROM security_alerts WHERE attributes IS NOT NULL"
        )
        result["attributes_migration"]["security_alerts_with_json"] = self.cursor.fetchone()[0]
        
        # Check tool interactions with JSON
        self.cursor.execute(
            "SELECT COUNT(*) FROM tool_interactions WHERE attributes IS NOT NULL"
        )
        result["attributes_migration"]["tool_interactions_with_json"] = self.cursor.fetchone()[0]
        
        # Check framework events with JSON
        self.cursor.execute(
            "SELECT COUNT(*) FROM framework_events WHERE attributes IS NOT NULL"
        )
        result["attributes_migration"]["framework_events_with_json"] = self.cursor.fetchone()[0]
        
        # Check linked LLM pairs
        self.cursor.execute(
            "SELECT COUNT(*) FROM llm_interactions WHERE related_interaction_id IS NOT NULL"
        )
        result["relationship_linking"]["linked_llm_pairs"] = self.cursor.fetchone()[0] // 2
        
        # Check populated sessions
        self.cursor.execute("SELECT COUNT(*) FROM sessions")
        result["empty_tables_population"]["sessions"] = self.cursor.fetchone()[0]
        
        # Check populated security alert triggers
        self.cursor.execute("SELECT COUNT(*) FROM security_alert_triggers")
        result["empty_tables_population"]["security_alert_triggers"] = self.cursor.fetchone()[0]
        
        # Check populated tool interactions
        self.cursor.execute("SELECT COUNT(*) FROM tool_interactions")
        result["empty_tables_population"]["tool_interactions"] = self.cursor.fetchone()[0]
        
        # Check fixed request timestamps
        self.cursor.execute(
            "SELECT COUNT(*) FROM llm_interactions WHERE interaction_type = 'start' AND request_timestamp IS NOT NULL"
        )
        result["null_values_fixed"]["request_timestamps"] = self.cursor.fetchone()[0]
        
        # Check fixed response timestamps
        self.cursor.execute(
            "SELECT COUNT(*) FROM llm_interactions WHERE interaction_type = 'finish' AND response_timestamp IS NOT NULL"
        )
        result["null_values_fixed"]["response_timestamps"] = self.cursor.fetchone()[0]
        
        return result

def rebuild_database():
    """
    Completely rebuild the database schema.
    
    WARNING: This will delete all existing data.
    
    Use this function to fix fundamental schema issues like foreign key mismatches.
    """
    logger.warning("Rebuilding entire database schema - all data will be lost")
    
    # Get the database path from the connection URL
    db_path = None
    if engine.url.drivername.startswith('sqlite'):
        db_path = engine.url.database
        if os.path.exists(db_path):
            # Create a backup first
            backup_path = f"{db_path}.backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            try:
                import shutil
                shutil.copy2(db_path, backup_path)
                logger.info(f"Created database backup at {backup_path}")
            except Exception as e:
                logger.error(f"Failed to create database backup: {e}")
    
    try:
        # Drop all tables
        logger.info("Dropping all tables...")
        drop_all()
        
        # Create all tables with the updated schema
        logger.info("Creating all tables with updated schema...")
        create_all()
        
        logger.info("Database schema rebuilt successfully")
        return True
    except Exception as e:
        logger.error(f"Error rebuilding database schema: {e}")
        return False

def main(db_path: str):
    """
    Run the migration.
    
    Args:
        db_path: Path to the SQLite database file
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info(f"Starting migration for database: {db_path}")
    
    with AttributeMigration(db_path) as migration:
        # Apply schema changes
        migration.apply_schema_changes()
        
        # Migrate attributes to JSON format
        migration.migrate_attributes()
        
        # Fix NULL timestamps
        migration.update_timestamps()
        
        # Populate empty tables
        migration.populate_empty_tables()
        
        # Verify migration
        stats = migration.verify_migration()
        
        logger.info("Migration completed successfully")
        logger.info(f"Migration statistics: {json.dumps(stats, indent=2)}")
    
    return stats

if __name__ == "__main__":
    # Run the migration when the script is executed directly
    rebuild_database() 