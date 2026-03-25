"""
Regime Engine for StrikeIQ
Basic regime detection functionality
"""

from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

def detect_regime(analytics: Dict[str, Any]) -> str:
    """
    Simple regime detection based on PCR and other indicators
    """
    try:
        pcr = analytics.get("pcr", 1.0)
        
        if pcr > 1:
            return "TREND"  # Bearish trend
        elif pcr < 0.7:
            return "TREND"  # Bullish trend
        else:
            return "RANGING"
    except Exception as e:
        logger.error(f"Regime detection failed: {e}")
        return "RANGING"

def get_regime_confidence(analytics: Dict[str, Any]) -> float:
    """
    Calculate confidence level for regime detection
    """
    try:
        pcr = analytics.get("pcr", 1.0)
        
        # Strong PCR values indicate higher confidence
        if pcr > 1.2 or pcr < 0.6:
            return 0.8
        elif pcr > 1.0 or pcr < 0.8:
            return 0.6
        else:
            return 0.4
    except Exception as e:
        logger.error(f"Regime confidence calculation failed: {e}")
        return 0.4
