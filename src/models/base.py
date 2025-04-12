"""
Base SQLAlchemy model and database connection utilities.

This module provides the Base model class and database connection utilities
for SQLAlchemy ORM models.
"""
import os
import logging
from typing import Iterator, Optional, List, Set
from contextlib import contextmanager
import importlib

from sqlalchemy import create_engine, event, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import DeclarativeMeta

# Import our custom JSON encoder
from src.utils.json_serializer import dumps, loads

# Create a logger
logger = logging.getLogger(__name__)

# Create the SQLAlchemy Base class
Base = declarative_base()

# Get settings for database URL
try:
    from src.config.settings import get_settings
    settings = get_settings()
    DATABASE_URL = settings.DATABASE_URL
except ImportError:
    # Fallback if settings module is not available
    DEFAULT_DB_PATH = os.path.join(os.getcwd(), "cylestio.db")
    DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{DEFAULT_DB_PATH}")
    logger.warning(f"Using fallback database URL: {DATABASE_URL}")

# Create the SQLAlchemy engine with custom JSON serializer
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    echo=os.environ.get("SQL_ECHO", "false").lower() == "true",
    json_serializer=dumps,
    json_deserializer=loads
)

# Log database information
logger.info(f"Initializing database connection to: {DATABASE_URL}")

# Create the session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Register event listeners for SQLite for better performance
if DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

def get_db() -> Iterator[Session]:
    """
    Get a database session.
    
    Yields:
        Session: Database session
    """
    db = None
    try:
        db = SessionLocal()
        yield db
    finally:
        if db is not None:
            db.close()

def init_db() -> None:
    """
    Initialize the database and verify all required tables exist.
    
    This function ensures:
    1. All models are imported and registered with Base
    2. The database exists
    3. All required tables exist
    4. Creates any missing tables

    Raises:
        Exception: If database validation fails and cannot be corrected
    """
    # Import all models to ensure they are registered with Base
    _import_all_models()
    
    # Check if database exists and has all required tables
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    
    # Get all model tables that should exist
    model_tables = set([model.__tablename__ for model in Base.__subclasses__()])
    
    # Log table status
    logger.info(f"Database has {len(existing_tables)} tables: {', '.join(existing_tables) if existing_tables else 'none'}")
    logger.info(f"Models require {len(model_tables)} tables: {', '.join(model_tables)}")
    
    # Check for missing tables
    missing_tables = model_tables - existing_tables
    
    if missing_tables:
        logger.warning(f"Missing {len(missing_tables)} tables: {', '.join(missing_tables)}")
        logger.info("Creating missing tables...")
        
        # Create only the missing tables
        # First build a list of metadata tables that need creation
        tables_to_create = []
        for table_name in missing_tables:
            for model in Base.__subclasses__():
                if model.__tablename__ == table_name:
                    tables_to_create.append(model.__table__)
        
        # Create the missing tables
        Base.metadata.create_all(bind=engine, tables=tables_to_create)
        logger.info(f"Created {len(tables_to_create)} missing tables")
    else:
        logger.info("All required tables exist in the database")
    
    # Verify tables were created successfully
    after_tables = set(inspect(engine).get_table_names())
    still_missing = model_tables - after_tables
    
    if still_missing:
        error_msg = f"Failed to create required tables: {', '.join(still_missing)}"
        logger.error(error_msg)
        raise Exception(error_msg)
    
    logger.info(f"Database initialization successful at: {DATABASE_URL}")

def _import_all_models() -> None:
    """Import all models to ensure they are registered with Base"""
    from src.models import (
        Agent,
        Session,
        Trace,
        Span,
        Event,
        LLMInteraction,
        ToolInteraction,
        SecurityAlert,
        SecurityAlertTrigger,
        FrameworkEvent
    )
    # Log imported models
    logger.debug(f"Imported {len(Base.__subclasses__())} models")

def create_all() -> None:
    """Create all tables."""
    logger.info("Creating all database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info(f"All database tables created at: {DATABASE_URL}")

def drop_all() -> None:
    """Drop all tables (use with caution)."""
    logger.warning(f"Dropping all database tables at: {DATABASE_URL}")
    Base.metadata.drop_all(bind=engine)
    logger.warning(f"All database tables dropped at: {DATABASE_URL}")

@contextmanager
def transaction() -> Iterator[Session]:
    """
    Context manager for transactions.
    
    This provides a context manager for handling transactions with automatic
    commit and rollback.
    
    Yields:
        Session: Database session
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close() 