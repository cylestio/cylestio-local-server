from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

# Import routes
from src.api.routes import telemetry, metrics, health, agents, security, alert_metrics, events
from src.api.middleware.error_handler import add_error_handlers

def create_api_app() -> FastAPI:
    """
    Create and configure the FastAPI application
    """
    app = FastAPI(
        title="Cylestio Local Server API",
        description="API for receiving and analyzing telemetry data from cylestio-monitor",
        version="1.0.0",
    )
    
    # Configure CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, replace with specific origins
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add error handlers
    add_error_handlers(app)
    
    # Include routers
    app.include_router(health.router, prefix="/v1", tags=["Health"])
    app.include_router(telemetry.router, prefix="/v1", tags=["Telemetry"])
    app.include_router(metrics.router, prefix="/v1", tags=["Metrics"])
    app.include_router(agents.router, prefix="/v1", tags=["Agents"])
    app.include_router(alert_metrics.router, prefix="/v1", tags=["Security"])
    app.include_router(security.router, prefix="/v1", tags=["Security"])
    app.include_router(events.router, prefix="/v1", tags=["Events"])
    
    # Custom OpenAPI schema
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
            
        openapi_schema = get_openapi(
            title="Cylestio Local Server API",
            version="1.0.0",
            description="API for receiving and analyzing telemetry data from cylestio-monitor",
            routes=app.routes,
        )
        
        # Add API versioning info
        openapi_schema["info"]["x-api-versions"] = {
            "current": "v1",
            "deprecated": [],
            "supported": ["v1"]
        }
        
        # Filter out deprecated endpoints from the OpenAPI schema
        paths = openapi_schema.get("paths", {})
        filtered_paths = {}
        
        for path, path_item in paths.items():
            # Create a new path_item that excludes any deprecated operations
            new_path_item = {}
            has_non_deprecated = False
            
            for method, operation in path_item.items():
                # Skip deprecated operations
                if not operation.get("deprecated", False):
                    new_path_item[method] = operation
                    has_non_deprecated = True
            
            # Only include the path if it has at least one non-deprecated operation
            if has_non_deprecated:
                filtered_paths[path] = new_path_item
        
        # Replace the paths with the filtered version
        openapi_schema["paths"] = filtered_paths
        
        app.openapi_schema = openapi_schema
        return app.openapi_schema
        
    app.openapi = custom_openapi
    
    return app 