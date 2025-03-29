"""
Tests for the SimpleProcessor class.
"""
import json
import datetime
import pytest
from unittest.mock import MagicMock, patch

import sqlalchemy
from sqlalchemy import text
from processing.simple_processor import SimpleProcessor, ProcessingError
from models.event import Event
from models.llm_interaction import LLMInteraction
from models.security_alert import SecurityAlert
from models.framework_event import FrameworkEvent 