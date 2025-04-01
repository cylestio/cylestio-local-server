from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

# Import routes
from src.api.routes import telemetry, metrics, health
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
        
        app.openapi_schema = openapi_schema
        return app.openapi_schema
        
    app.openapi = custom_openapi
    
    return app 