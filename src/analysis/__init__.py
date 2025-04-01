"""
Analysis layer for the telemetry system.

This package provides interfaces and implementations for analyzing telemetry
data from AI agents. It includes components for querying data, calculating
metrics, and generating insights from telemetry events.
"""

from src.analysis.interface import (
    AnalysisInterface,
    BaseQueryParams,
    MetricParams,
    TimeSeriesParams,
    TimeRange,
    TimeResolution,
    SortDirection,
    QueryResult,
    PaginationParams,
    Pagination
)

from src.analysis.metrics import (
    TokenMetrics,
    ToolMetrics,
    SecurityMetrics,
    DashboardMetrics
)

__all__ = [
    # Interfaces
    'AnalysisInterface',
    'BaseQueryParams',
    'MetricParams',
    'TimeSeriesParams',
    'TimeRange',
    'TimeResolution',
    'SortDirection',
    'QueryResult',
    'PaginationParams',
    'Pagination',
    
    # Metrics
    'TokenMetrics',
    'ToolMetrics',
    'SecurityMetrics',
    'DashboardMetrics'
] 