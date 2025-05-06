"""
This module serves as a bridge to allow 'from src.xxx' imports to work correctly when the package
is installed via pip. It creates a "src" module that points to the appropriate modules in the package.
"""
import sys
import os
import importlib.util

# Make the parent directory importable as 'src'
if 'src' not in sys.modules:
    # Use the parent directory of this file's directory as the base path
    src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    
    # Create a module spec for 'src'
    spec = importlib.util.spec_from_file_location('src', os.path.join(src_path, '__init__.py'))
    if spec is not None:
        src_module = importlib.util.module_from_spec(spec)
        sys.modules['src'] = src_module
        if spec.loader is not None:
            spec.loader.exec_module(src_module)
    else:
        # Create an empty module as fallback
        import types
        sys.modules['src'] = types.ModuleType('src')
        sys.modules['src'].__path__ = [src_path] 