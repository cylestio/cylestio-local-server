#!/usr/bin/env python3
"""
Command-line interface for starting the Cylestio Local Server.
"""
import argparse
import sys
from typing import List, Optional

from cylestio_local_server.server import run_server


def main(args: Optional[List[str]] = None) -> int:
    """
    Main entry point for the CLI application.
    
    Args:
        args: Command line arguments (defaults to sys.argv[1:])
        
    Returns:
        int: Exit code
    """
    parser = argparse.ArgumentParser(
        description="Cylestio Local Server - A lightweight, self-hosted server for collecting, processing, and analyzing telemetry data from AI agents"
    )
    parser.add_argument(
        "--host", 
        type=str, 
        default="0.0.0.0", 
        help="Host to bind the server to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        default=8000, 
        help="Port to bind the server to (default: 8000)"
    )
    parser.add_argument(
        "--db-path", 
        type=str, 
        default="cylestio.db", 
        help="Path to the SQLite database file (default: cylestio.db)"
    )
    parser.add_argument(
        "--reload", 
        action="store_true", 
        help="Enable auto-reload for development"
    )
    parser.add_argument(
        "--debug", 
        action="store_true",
        help="Enable debug mode"
    )
    
    parsed_args = parser.parse_args(args)
    
    try:
        run_server(
            host=parsed_args.host,
            port=parsed_args.port,
            db_path=parsed_args.db_path,
            reload=parsed_args.reload,
            debug=parsed_args.debug
        )
        return 0
    except Exception as e:
        print(f"Error starting server: {str(e)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main()) 