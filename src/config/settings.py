import os
from typing import List, Dict, Any
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables or .env file
    """
    # Server settings
    HOST: str = Field("0.0.0.0", env="HOST")
    PORT: int = Field(8000, env="PORT")
    DEBUG: bool = Field(False, env="DEBUG")
    
    # Database settings
    DATABASE_URL: str = Field("sqlite:///cylestio.db", env="DATABASE_URL")
    
    # API settings
    API_PREFIX: str = Field("/api", env="API_PREFIX")
    RATE_LIMIT_PER_MINUTE: int = Field(100, env="RATE_LIMIT_PER_MINUTE")
    
    # Logging settings
    LOG_LEVEL: str = Field("DEBUG", env="LOG_LEVEL")
    
    class Config:
        env_file = ".env"
        
def get_settings() -> Settings:
    """
    Get application settings
    """
    return Settings() 