import os
import requests
from typing import Dict, Any

class CarbonCalculatorService:
    """Service to calculate carbon scores for operations"""

    # Simple carbon factors for different operation types
    CARBON_FACTORS = {
        'electricity': 0.5,
        'transportation': 2.3,
        'heating': 1.8,
        'manufacturing': 3.2,
        'default': 1.0
    }

    def __init__(self):
        self.external_api_key = os.getenv('CARBON_API_KEY')
        self.use_external_api = bool(self.external_api_key)

    def calculate_carbon_score(self, operation_type: str, amount: float) -> float:
        """
        Calculate carbon score for an operation.
        First tries external API if configured, falls back to local calculation.
        """
        if self.use_external_api:
            try:
                return self._calculate_external(operation_type, amount)
            except Exception as e:
                print(f"External API failed: {e}. Falling back to local calculation.")

        return self._calculate_local(operation_type, amount)

    def _calculate_local(self, operation_type: str, amount: float) -> float:
        """Local carbon score calculation using simple factors"""
        factor = self.CARBON_FACTORS.get(operation_type.lower(), self.CARBON_FACTORS['default'])
        return round(amount * factor, 2)

    def _calculate_external(self, operation_type: str, amount: float) -> float:
        """
        External API calculation (placeholder for real implementation)
        This would integrate with services like Climatiq or Carbon Interface
        """
        # Placeholder implementation - would need real API integration
        # For now, just return local calculation
        return self._calculate_local(operation_type, amount)
