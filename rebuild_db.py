#!/usr/bin/env python3
"""
Rebuild the database with the correct schema.

This script is used to fix foreign key constraint issues by completely rebuilding 
the database with the updated schema.

WARNING: This will delete all existing data.
"""
import os
import sys
import logging
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath("."))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)

def main():
    """Main entry point for the script."""
    logger.info("Starting database rebuild...")
    
    # Check if database exists
    db_path = Path("cylestio.db")
    if db_path.exists():
        logger.info(f"Found existing database at {db_path}")
    else:
        logger.info(f"No existing database found at {db_path}, will create a new one")
    
    # Import and run the rebuild function
    from src.database.schema_migration import rebuild_database
    
    try:
        success = rebuild_database()
        if success:
            logger.info("Database rebuilt successfully!")
            return 0
        else:
            logger.error("Failed to rebuild database")
            return 1
    except Exception as e:
        logger.error(f"Error rebuilding database: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main()) 