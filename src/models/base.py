"""
Base SQLAlchemy model and database connection utilities.

This module provides the Base model class and database connection utilities
for SQLAlchemy ORM models.
"""
import os
import logging
from typing import Iterator, Optional
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# Create a logger
logger = logging.getLogger(__name__)

# Create the SQLAlchemy Base class
Base = declarative_base()

# Default to SQLite database if not specified
DEFAULT_DB_PATH = os.path.join(os.getcwd(), "cylestio.db")
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{DEFAULT_DB_PATH}")

# Create the SQLAlchemy engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    echo=os.environ.get("SQL_ECHO", "false").lower() == "true"
)

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
    """Initialize the database and create tables."""
    # Import all models to ensure they are registered with Base
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
    
    # Create the tables
    create_all()

def create_all() -> None:
    """Create all tables."""
    Base.metadata.create_all(bind=engine)

def drop_all() -> None:
    """Drop all tables (use with caution)."""
    Base.metadata.drop_all(bind=engine)

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