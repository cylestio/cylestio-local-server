#!/usr/bin/env python
"""
Script to update agent names in the database to match their agent_ids.

This script fixes the confusion between agent_id and name by making them consistent.
"""
import sqlite3
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def update_agent_names(db_path):
    """Update all agent names to match their agent_ids."""
    logger.info(f"Connecting to database at {db_path}")
    
    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all agents
        cursor.execute("SELECT agent_id, name FROM agents")
        agents = cursor.fetchall()
        
        if not agents:
            logger.info("No agents found in the database.")
            return
            
        logger.info(f"Found {len(agents)} agents in the database.")
        
        # Display current values
        logger.info("Current values:")
        for agent_id, name in agents:
            logger.info(f"agent_id: {agent_id}, name: {name}")
        
        # Update each agent's name to match its agent_id
        for agent_id, name in agents:
            cursor.execute(
                "UPDATE agents SET name = ? WHERE agent_id = ?",
                (agent_id, agent_id)
            )
            logger.info(f"Updated agent {agent_id}: changed name from '{name}' to '{agent_id}'")
        
        # Commit the changes
        conn.commit()
        logger.info("All changes committed successfully.")
        
        # Verify the changes
        cursor.execute("SELECT agent_id, name FROM agents")
        updated_agents = cursor.fetchall()
        
        logger.info("Updated values:")
        for agent_id, name in updated_agents:
            logger.info(f"agent_id: {agent_id}, name: {name}")
        
    except Exception as e:
        logger.error(f"Error updating agent names: {str(e)}")
        raise
    finally:
        if conn:
            conn.close()

def main():
    """Main entry point."""
    db_path = Path("cylestio.db")
    
    if not db_path.exists():
        logger.error(f"Database file not found at {db_path}")
        return
    
    logger.info("Starting agent name update process")
    update_agent_names(db_path)
    logger.info("Agent name update process completed")

if __name__ == "__main__":
    main() 