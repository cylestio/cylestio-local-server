"""
Security alert metrics endpoints.
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from src.database.session import get_db
from src.models.security_alert import SecurityAlert
from src.models.event import Event
from src.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

# The /alerts/stats endpoint has been moved to security.py file
# to ensure proper route ordering and avoid conflicts 