#!/usr/bin/env python3
"""
Wrapper script to process example records with proper import paths.
"""
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Now we can import from src modules
from process_example_event import *

# The imported script will run automatically 