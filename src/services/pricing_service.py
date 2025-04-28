"""
Pricing Service

This module provides a centralized service for LLM model pricing operations.
It loads pricing data from CSV and provides methods to calculate costs based on
token usage for various models. It serves as the single source of truth for
all pricing-related operations in the application.
"""
import csv
import os
import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from functools import lru_cache
import re

# Setup logger
logger = logging.getLogger(__name__)

class PricingService:
    """
    Service for managing LLM model pricing and cost calculations.
    
    This service loads pricing data from a CSV file and provides
    methods to calculate costs based on token usage for various models.
    """
    
    # Singleton instance
    _instance = None
    
    def __new__(cls):
        """Implement singleton pattern"""
        if cls._instance is None:
            cls._instance = super(PricingService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the pricing service"""
        if self._initialized:
            return
            
        self._pricing_data = {}
        self._last_loaded = None
        self._csv_path = os.path.join("resources", "full_llm_models_pricing_08April2025.csv")
        self._load_pricing_data()
        self._initialized = True
    
    def _load_pricing_data(self):
        """Load pricing data from CSV file"""
        logger.info(f"Loading pricing data from {self._csv_path}")
        
        try:
            with open(self._csv_path, mode='r', encoding='utf-8') as csv_file:
                csv_reader = csv.DictReader(csv_file)
                
                # Clear existing data
                self._pricing_data = {}
                
                for row in csv_reader:
                    # Extract provider and model
                    provider = row.get('Provider', '').strip()
                    model = row.get('Model', '').strip()
                    
                    # Parse prices, handling 'N/A' and price ranges
                    input_price = self._parse_price(row.get('Input Price', '0'))
                    output_price = self._parse_price(row.get('Output Price', '0'))
                    
                    # Store data in multiple formats for flexible matching
                    # 1. Original keys
                    combined_key = f"{provider.lower()}-{model.lower()}"
                    
                    # 2. Model only (for fallback)
                    model_key = model.lower()
                    
                    # 3. Normalized model name (spaces to dashes)
                    normalized_model = model.lower().replace(' ', '-')
                    normalized_key = f"{provider.lower()}-{normalized_model}"
                    
                    # Store the data
                    for key in [combined_key, normalized_key]:
                        self._pricing_data[key] = {
                            'provider': provider,
                            'model': model,
                            'input_price': input_price,
                            'output_price': output_price,
                            'context_window': row.get('Context Window', ''),
                            'notes': row.get('Notes', '')
                        }
                    
                    # Also store by model only, but don't overwrite if exists
                    # (prefer to keep the first entry for a given model)
                    if model_key not in self._pricing_data:
                        self._pricing_data[model_key] = {
                            'provider': provider,
                            'model': model,
                            'input_price': input_price,
                            'output_price': output_price,
                            'context_window': row.get('Context Window', ''),
                            'notes': row.get('Notes', '')
                        }
            
            self._last_loaded = datetime.now()
            logger.info(f"Successfully loaded pricing data for {len(self._pricing_data)} models")
            
        except Exception as e:
            logger.error(f"Error loading pricing data: {str(e)}", exc_info=True)
            # Keep the existing data if load fails
    
    def _parse_price(self, price_str: str) -> float:
        """
        Parse price string, handling special formats.
        
        Args:
            price_str: Price string from CSV (e.g., "$0.0015", "N/A", "$0.00125–0.0025")
            
        Returns:
            Parsed price as float
        """
        # Remove '$' and whitespace
        cleaned = price_str.replace('$', '').strip()
        
        if not cleaned or cleaned.lower() == 'n/a':
            return 0.0
            
        try:
            # Handle price ranges (e.g., "0.00125–0.0025")
            if '–' in cleaned or '-' in cleaned:
                # Split on either dash character
                parts = cleaned.replace('–', '-').split('-')
                values = []
                
                for part in parts:
                    if part.strip():
                        try:
                            values.append(float(part.strip()))
                        except ValueError:
                            pass
                            
                # Calculate average if we have values
                if values:
                    return sum(values) / len(values)
                return 0.0
                
            # Regular case - single price
            return float(cleaned)
            
        except ValueError:
            logger.warning(f"Could not parse price: '{price_str}', using 0.0")
            return 0.0
    
    def reload_pricing_data(self):
        """Reload pricing data from CSV file"""
        self._load_pricing_data()
        
    def get_model_price(self, model: str, vendor: Optional[str] = None) -> Tuple[float, float]:
        """
        Get input and output prices for a given model.
        
        Args:
            model: Model name (e.g., "gpt-3.5-turbo", "claude-3-opus")
            vendor: Optional vendor/provider name (e.g., "OpenAI", "Anthropic")
            
        Returns:
            Tuple of (input_price, output_price) in $ per token
        """
        if not model:
            return 0.0, 0.0
            
        # Clean and normalize inputs
        clean_model = model.lower().strip()
        vendor_key = vendor.lower().strip() if vendor else None
        
        logger.info(f"Looking up pricing for model '{model}' (vendor: {vendor})")
        
        # Try all possible key combinations
        possible_keys = []
        
        # 1. Combined vendor-model key (most specific)
        if vendor_key:
            possible_keys.append(f"{vendor_key}-{clean_model}")
            
            # Also try with spaces converted to dashes
            normalized_model = clean_model.replace(' ', '-')
            possible_keys.append(f"{vendor_key}-{normalized_model}")
            
            # And vice versa - dashes to spaces
            spacey_model = clean_model.replace('-', ' ')
            possible_keys.append(f"{vendor_key}-{spacey_model}")
            
        # 2. Model-only keys (fallback)
        possible_keys.append(clean_model)
        # Also with space variations
        possible_keys.append(clean_model.replace('-', ' '))
        possible_keys.append(clean_model.replace(' ', '-'))
        
        # 3. Handle versioned models with date suffixes like claude-3-haiku-20240307
        # Strip version suffix (typically date in format YYYYMMDD at the end)
        base_model_match = re.match(r'^(claude-3(?:\.5)?-(?:haiku|sonnet|opus))(?:-.+)?$', clean_model)
        if base_model_match:
            base_model = base_model_match.group(1)
            logger.info(f"Extracted base model: '{base_model}' from '{clean_model}'")
            if base_model != clean_model:  # Only if there was a match and stripping occurred
                possible_keys.append(base_model)
                if vendor_key:
                    possible_keys.append(f"{vendor_key}-{base_model}")
                # Also try with space/dash variations
                possible_keys.append(base_model.replace('-', ' '))
                possible_keys.append(base_model.replace(' ', '-'))
        
        # Special case handling for common models
        model_mappings = {
            'gpt-3.5-turbo': ['gpt-3.5 turbo', 'gpt-3.5'],
            'gpt-4': ['gpt-4'],
            'gpt-4-turbo': ['gpt-4 turbo', 'gpt-4-turbo-preview'],
            'gpt-4o': ['gpt-4o', 'gpt4o'],
            'claude-3-opus': ['claude 3 opus', 'claude-3-opus'],
            'claude-3-sonnet': ['claude 3 sonnet', 'claude-3-sonnet'],
            'claude-3.5-sonnet': ['claude 3.5 sonnet', 'claude-3.5-sonnet', 'claude-3-5-sonnet'],
            'claude-3-haiku': ['claude 3 haiku', 'claude-3-haiku'],
        }
        
        # Add special cases to possible keys
        for base_model, variants in model_mappings.items():
            if any(variant in clean_model for variant in variants + [base_model]):
                for variant in variants + [base_model]:
                    possible_keys.append(variant)
                    if vendor_key:
                        possible_keys.append(f"{vendor_key}-{variant}")
        
        logger.info(f"Trying possible keys: {possible_keys}")
        logger.info(f"Available pricing keys: {list(self._pricing_data.keys())[:10]} (showing first 10)")
        
        # Try each key and return the first match
        for key in possible_keys:
            if key in self._pricing_data:
                price_data = self._pricing_data[key]
                logger.info(f"Found pricing for {model}: input=${price_data['input_price']}, output=${price_data['output_price']}")
                return price_data['input_price'], price_data['output_price']
        
        # Log warning and return default values if no match found
        logger.warning(f"No pricing found for model {model} (vendor: {vendor}). Using default $0.0.")
        return 0.0, 0.0
        
    def calculate_cost(self, input_tokens: int, output_tokens: int, model: str, vendor: Optional[str] = None) -> Dict[str, float]:
        """
        Calculate costs for token usage.
        
        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            model: Model name
            vendor: Optional vendor/provider name
            
        Returns:
            Dictionary with cost breakdown
        """
        # Get prices ($ per token)
        input_price, output_price = self.get_model_price(model, vendor)
        
        # Calculate costs ($ per 1K tokens)
        input_cost = (input_tokens / 1000) * input_price
        output_cost = (output_tokens / 1000) * output_price
        total_cost = input_cost + output_cost
        
        return {
            'input_cost': round(input_cost, 6),
            'output_cost': round(output_cost, 6),
            'total_cost': round(total_cost, 6),
            'input_price_per_1k': input_price,
            'output_price_per_1k': output_price
        }

# Create a global instance for easy import
pricing_service = PricingService() 