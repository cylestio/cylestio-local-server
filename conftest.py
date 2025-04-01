"""
Main conftest.py for the root tests directory.
This file enables importing modules from the src directory.
"""
import os
import sys
import pytest

# Add src to path to enable imports
sys.path.insert(0, os.path.abspath("src")) 