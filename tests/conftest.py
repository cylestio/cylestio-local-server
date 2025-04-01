"""
Basic test fixtures for MVP testing.
"""
import os
import sys
import tempfile
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

# Add src directory to path
sys.path.insert(0, os.path.abspath("src"))

from models.base import Base
from processing.simple_processor import SimpleProcessor


@pytest.fixture(scope="session")
def temp_db_path():
    """Create a temporary file path for a SQLite database."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture(scope="session")
def db_engine(temp_db_path):
    """Create a SQLite database engine for testing."""
    engine = create_engine(f"sqlite:///{temp_db_path}", echo=False)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Create a new database session for a test."""
    connection = db_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def db_session_factory(db_engine):
    """Create a session factory function for tests."""
    def get_session():
        connection = db_engine.connect()
        session = Session(bind=connection)
        return session
    
    return get_session


@pytest.fixture(scope="function")
def simple_processor(db_session_factory):
    """Create a SimpleProcessor for testing."""
    return SimpleProcessor(db_session_factory) 