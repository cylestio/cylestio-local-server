"""
Base models for SQLAlchemy ORM.

This module provides the base SQLAlchemy components for the entire application.
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session

# Create the SQLAlchemy base class
Base = declarative_base()

# Engine and session factory will be set up at runtime
engine = None
SessionLocal = None


def init_db(db_url: str, echo: bool = False):
    """
    Initialize the database connection.

    Args:
        db_url: SQLite connection string
        echo: Whether to echo SQL statements (for debugging)
    """
    global engine, SessionLocal
    
    # Create engine
    engine = create_engine(db_url, echo=echo, connect_args={"check_same_thread": False})
    
    # Create session factory
    SessionLocal = scoped_session(
        sessionmaker(autocommit=False, autoflush=False, bind=engine)
    )
    
    # Bind the session to the base class
    Base.query = SessionLocal.query_property()
    
    # Set pragma to enable foreign keys
    with engine.connect() as conn:
        conn.execute("PRAGMA foreign_keys = ON")
    
    return engine


def get_db():
    """
    Get a database session.
    
    Yields:
        A SQLAlchemy database session
    """
    if SessionLocal is None:
        raise RuntimeError("Database not initialized. Call init_db first.")
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_all():
    """Create all tables in the database."""
    if engine is None:
        raise RuntimeError("Database not initialized. Call init_db first.")
    
    Base.metadata.create_all(bind=engine)


def drop_all():
    """Drop all tables from the database."""
    if engine is None:
        raise RuntimeError("Database not initialized. Call init_db first.")
    
    Base.metadata.drop_all(bind=engine) 