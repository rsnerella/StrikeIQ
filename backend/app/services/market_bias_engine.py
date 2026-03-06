"""
Market Bias Engine
Computes price vs VWAP, OI changes, PCR, and divergence detection
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import numpy as np
from ..exceptions.data_unavailable_error import DataUnavailableError, MissingOIError

logger = logging.getLogger(__name__)

@dataclass
class MarketBiasResult:
    """Market bias analysis result"""
    symbol: str
    price_vs_vwap: float  # Price deviation from VWAP
    vwap: float
    current_price: float
    oi_change_5min: float  # OI change over 5 minutes
    pcr: float  # Put-Call Ratio
    divergence_detected: bool
    divergence_type: str  # "bullish", "bearish", "none"
    bias_strength: float  # 0-100 bias strength
    timestamp: str

class MarketBiasEngine:
    """
    Computes market bias indicators from option chain data
    """
    
    def __init__(self):
        self.historical_oi = {}  # Store OI history for velocity calculation
        
    def compute(self, data: Dict[str, Any]) -> MarketBiasResult:
        """
        Compute market bias from option chain data
        """
        try:
            symbol = data.get("symbol", "NIFTY")
            spot = data.get("spot", 0)
            calls = data.get("calls", [])
            puts = data.get("puts", [])
            
            # Calculate VWAP from option chain
            vwap = self._calculate_vwap(calls, puts, spot)
            price_vs_vwap = ((spot - vwap) / vwap) * 100 if vwap > 0 else 0
            
            # Calculate OI change over 5 minutes
            oi_change_5min = self._calculate_oi_velocity(symbol, calls, puts)
            
            # Calculate PCR
            pcr = self._calculate_pcr(calls, puts)
            
            # Detect divergence
            divergence_detected, divergence_type = self._detect_divergence(
                price_vs_vwap, pcr, oi_change_5min
            )
            
            # Calculate bias strength
            bias_strength = self._calculate_bias_strength(
                price_vs_vwap, pcr, oi_change_5min, divergence_detected
            )
            
            return MarketBiasResult(
                symbol=symbol,
                price_vs_vwap=price_vs_vwap,
                vwap=vwap,
                current_price=spot,
                oi_change_5min=oi_change_5min,
                pcr=pcr,
                divergence_detected=divergence_detected,
                divergence_type=divergence_type,
                bias_strength=bias_strength,
                timestamp=data.get("timestamp", "")
            )
            
        except Exception as e:
            logger.error(f"Error computing market bias: {e}")
            # Return neutral bias on error
            return MarketBiasResult(
                symbol=data.get("symbol", "NIFTY"),
                price_vs_vwap=0,
                vwap=0,
                current_price=data.get("spot", 0),
                oi_change_5min=0,
                pcr=1.0,
                divergence_detected=False,
                divergence_type="none",
                bias_strength=50,
                timestamp=data.get("timestamp", "")
            )
    
    def _calculate_vwap(self, calls: List[Dict], puts: List[Dict], spot: float) -> float:
        """Calculate Volume Weighted Average Price from option chain"""
        try:
            total_volume = 0
            weighted_sum = 0
            
            # Include calls
            for call in calls:
                volume = call.get("volume", 0)
                strike = call.get("strike", 0)
                if volume > 0:
                    weighted_sum += strike * volume
                    total_volume += volume
            
            # Include puts
            for put in puts:
                volume = put.get("volume", 0)
                strike = put.get("strike", 0)
                if volume > 0:
                    weighted_sum += strike * volume
                    total_volume += volume
            
            # Include spot price with minimum weight
            weighted_sum += spot * 1
            total_volume += 1
            
            return weighted_sum / total_volume if total_volume > 0 else spot
            
        except Exception as e:
            logger.error(f"Error calculating VWAP: {e}")
            return spot
    
    def _calculate_oi_velocity(self, symbol: str, calls: List[Dict], puts: List[Dict]) -> float:
        """Calculate OI change over 5 minutes"""
        try:
            current_total_oi = sum(
                call.get("open_interest", 0) for call in calls
            ) + sum(
                put.get("open_interest", 0) for put in puts
            )
            
            if symbol not in self.historical_oi:
                self.historical_oi[symbol] = []
            
            # Store current OI with timestamp
            import time
            self.historical_oi[symbol].append({
                "timestamp": time.time(),
                "oi": current_total_oi
            })
            
        except Exception as e:
            logger.error(f"Error calculating OI velocity: {e}")
            raise DataUnavailableError(f"OI velocity calculation failed: {e}")
    
    def _calculate_pcr(self, calls: List[Dict], puts: List[Dict]) -> float:
        """Calculate Put-Call Ratio"""
        try:
            if not calls or not puts:
                raise MissingOIError("Empty calls/puts data for PCR calculation")
            
            total_call_oi = sum(call.get("open_interest", 0) for call in calls)
            total_put_oi = sum(put.get("open_interest", 0) for put in puts)
            
            if total_call_oi == 0 and total_put_oi == 0:
                raise MissingOIError("No OI data available for PCR calculation")
            
            return total_put_oi / total_call_oi if total_call_oi > 0 else 1.0
            
        except Exception as e:
            logger.error(f"Error calculating PCR: {e}")
            raise DataUnavailableError(f"PCR calculation failed: {e}")
    
    def _detect_divergence(self, price_vs_vwap: float, pcr: float, oi_change: float) -> tuple[bool, str]:
        """Detect bullish/bearish divergence"""
        try:
            # Bullish divergence: Price below VWAP but PCR decreasing
            if price_vs_vwap < -1 and pcr < 0.8 and oi_change < 0:
                return True, "bullish"
            
            # Bearish divergence: Price above VWAP but PCR increasing
            if price_vs_vwap > 1 and pcr > 1.2 and oi_change > 0:
                return True, "bearish"
            
            return False, "none"
            
        except Exception as e:
            logger.error(f"Error detecting divergence: {e}")
            return False, "none"
    
    def _calculate_bias_strength(self, price_vs_vwap: float, pcr: float, oi_change: float, divergence: bool) -> float:
        """Calculate overall bias strength (0-100)"""
        try:
            strength = 50  # Neutral base
            
            # Price momentum factor
            strength += price_vs_vwap * 2
            
            # PCR factor
            if pcr > 1.2:  # More puts than calls
                strength -= 10
            elif pcr < 0.8:  # More calls than puts
                strength += 10
            
            # OI change factor
            strength += min(max(oi_change / 1000, 10), -10)
            
            # Divergence bonus
            if divergence:
                strength += 15
            
            return max(0, min(100, strength))
            
        except Exception as e:
            logger.error(f"Error calculating bias strength: {e}")
            return 50
