"""
Servicio de calculo de huella de carbono.

Implementacion actual: formula local con factores fijos.
Preparado para integracion con APIs externas (Climatiq, Carbon Interface).
"""
import os
import requests
from typing import Dict, Any
import logging


class CarbonCalculatorService:
    # Factores de carbono por tipo de operacion (kg CO2 por unidad)
    CARBON_FACTORS = {
        'electricity': 0.5,      # kWh
        'transportation': 2.3,   # km
        'heating': 1.8,          # m3 gas
        'manufacturing': 3.2,    # unidad producida
        'default': 1.0
    }

    def __init__(self):
        self.external_api_key = os.getenv('CARBON_API_KEY')
        self.use_external_api = bool(self.external_api_key)
        self.logger = logging.getLogger(__name__)

    def calculate_carbon_score(self, operation_type: str, amount: float) -> float:
        """
        Calculate carbon score for an operation.
        First tries external API if configured, falls back to local calculation.
        """
        self.logger.debug(f"Calculating carbon score for type: {operation_type}, amount: {amount}")

        if self.use_external_api:
            try:
                self.logger.debug("Attempting external API calculation")
                return self._calculate_external(operation_type, amount)
            except Exception as e:
                self.logger.warning(f"External API failed: {e}. Falling back to local calculation.")

        self.logger.debug("Using local calculation method")
        return self._calculate_local(operation_type, amount)

    def _calculate_local(self, operation_type: str, amount: float) -> float:
        """Local carbon score calculation using simple factors"""
        factor = self.CARBON_FACTORS.get(operation_type.lower(), self.CARBON_FACTORS['default'])
        carbon_score = round(amount * factor, 2)

        self.logger.debug(f"Local calculation: {operation_type} * {factor} = {carbon_score}")
        return carbon_score

    def _calculate_external(self, operation_type: str, amount: float) -> float:
        """
        External API calculation (placeholder for real implementation)
        This would integrate with services like Climatiq or Carbon Interface
        """
        self.logger.info(f"External API calculation requested for {operation_type}")

        # Placeholder implementation - would need real API integration
        # For now, just return local calculation
        self.logger.warning("External API not implemented, using local calculation as fallback")
        return self._calculate_local(operation_type, amount)
