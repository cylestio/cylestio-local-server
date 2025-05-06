"""
This module serves as a bridge to allow 'from src.xxx' imports to work correctly when the package
is installed via pip. It creates a "src" module that points to the appropriate modules in the package.
"""
import sys
import os
import importlib.util
import importlib.machinery
import types

# Make the parent directory importable as 'src'
if 'src' not in sys.modules:
    # First try to import the src package directly (if it exists as a proper package)
    try:
        import src
    except ImportError:
        # If direct import fails, create a virtual 'src' module
        # that points to the parent directory of cylestio_local_server
        src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        
        # Create an empty module
        src_module = types.ModuleType('src')
        sys.modules['src'] = src_module
        
        # Set the __path__ attribute so Python can find submodules
        src_module.__path__ = [src_path]
        
        # Try to load the __init__.py if it exists, but don't fail if it doesn't
        init_path = os.path.join(src_path, '__init__.py')
        if os.path.exists(init_path):
            try:
                spec = importlib.util.spec_from_file_location('src', init_path)
                if spec is not None and spec.loader is not None:
                    loader = spec.loader
                    src_module.__spec__ = spec
                    loader.exec_module(src_module)
            except Exception:
                # If loading fails, we still have the basic module
                pass 