"""
Configuration for the processing layer.

This module provides configuration classes and settings for the processing layer.
"""
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


class ValidationConfig(BaseModel):
    """
    Configuration for telemetry validation.
    
    This class contains settings for controlling the validation behavior
    of telemetry records.
    """
    
    strict_mode: bool = Field(
        default=False,
        description="When true, validation is more strict, failing on fields that don't match exact patterns"
    )
    
    allow_unknown_fields: bool = Field(
        default=True,
        description="When true, unknown fields in the telemetry data are allowed"
    )
    
    validate_attributes: bool = Field(
        default=True,
        description="When true, the attributes object is validated for structure"
    )
    
    max_attribute_depth: int = Field(
        default=5,
        description="Maximum nesting depth for attributes objects"
    )


class TransformationConfig(BaseModel):
    """
    Configuration for telemetry transformation.
    
    This class contains settings for controlling the transformation behavior
    of telemetry records.
    """
    
    max_attribute_count: int = Field(
        default=100,
        description="Maximum number of attributes to extract from a record"
    )
    
    auto_create_related_entities: bool = Field(
        default=True,
        description="When true, automatically create missing related entities like sessions"
    )
    
    extract_embedded_events: bool = Field(
        default=False,
        description="When true, attempt to extract embedded events from attribute fields"
    )


class BatchProcessingConfig(BaseModel):
    """
    Configuration for batch processing.
    
    This class contains settings for controlling the batch processing behavior.
    """
    
    batch_size: int = Field(
        default=100,
        description="Default number of records to process in a batch"
    )
    
    max_workers: int = Field(
        default=4,
        description="Maximum number of worker threads for parallel processing"
    )
    
    default_commit: bool = Field(
        default=True,
        description="Whether to commit transactions by default"
    )
    
    auto_retry_failed: bool = Field(
        default=False,
        description="When true, automatically retry failed records"
    )
    
    max_retries: int = Field(
        default=3,
        description="Maximum number of retries for failed records"
    )
    
    retry_delay_ms: int = Field(
        default=100,
        description="Delay in milliseconds between retries"
    )


class ProcessingConfig(BaseModel):
    """
    Main configuration for the processing layer.
    
    This class contains all configuration settings for the processing layer.
    """
    
    validation: ValidationConfig = Field(
        default_factory=ValidationConfig,
        description="Validation configuration"
    )
    
    transformation: TransformationConfig = Field(
        default_factory=TransformationConfig,
        description="Transformation configuration"
    )
    
    batch_processing: BatchProcessingConfig = Field(
        default_factory=BatchProcessingConfig,
        description="Batch processing configuration"
    )
    
    log_validation_errors: bool = Field(
        default=True,
        description="Whether to log validation errors"
    )
    
    log_transformation_errors: bool = Field(
        default=True,
        description="Whether to log transformation errors"
    )
    
    log_persistence_errors: bool = Field(
        default=True,
        description="Whether to log persistence errors"
    )
    
    error_log_level: str = Field(
        default="error",
        description="Log level for errors (error, warning, info, etc.)"
    )
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "ProcessingConfig":
        """
        Create a configuration from a dictionary.
        
        Args:
            config_dict: Configuration dictionary
            
        Returns:
            ProcessingConfig: Configuration object
        """
        return cls(**config_dict)
    
    @classmethod
    def create_default(cls) -> "ProcessingConfig":
        """
        Create a default configuration.
        
        Returns:
            ProcessingConfig: Default configuration object
        """
        return cls()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to a dictionary.
        
        Returns:
            dict: Configuration dictionary
        """
        return self.dict()


# Default configuration instance
DEFAULT_CONFIG = ProcessingConfig.create_default() 