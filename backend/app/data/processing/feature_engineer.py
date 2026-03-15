"""
Feature Engineering Engine for StrikeIQ
Computes MarketFeatureVector from live snapshots
"""

import logging
import numpy as np
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class MarketFeatureVector:
    """Standardized feature vector for AI model inputs"""
    symbol: str
    timestamp: int
    price_change_5m: float
    volatility_15m: float
    pcr_ratio: float
    oi_trend: float
    net_gamma: float
    vwap_distance: float
    rsi_14: float
    momentum: float
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class FeatureEngineeringEngine:
    """
    Computes high-dimensional feature vectors from raw market snapshots.
    Used as the primary input for all AI decision engines.
    """
    
    def __init__(self):
        logger.info("FeatureEngineeringEngine initialized")

    def compute(self, symbol: str, snapshots: List[Dict[str, Any]]) -> Optional[MarketFeatureVector]:
        """
        Computes the feature vector from a series of snapshots.
        Requires at least 15 snapshots for stable calculations.
        """
        if not snapshots or len(snapshots) < 2:
            return None
        
        latest = snapshots[-1]
        prev = snapshots[-2]
        
        try:
            # Basic Price features
            current_price = latest.get("spot", 0)
            if current_price == 0:
                return None
                
            # Price delta
            price_delta = (current_price - prev.get("spot", current_price)) / current_price
            
            # Options specific features
            option_chain = latest.get("option_chain", {})
            pcr = float(option_chain.get("pcr", 1.0))
            net_gex = float(option_chain.get("net_gex", 0.0))
            
            # OI features
            total_oi = float(option_chain.get("total_call_oi", 0) + option_chain.get("total_put_oi", 0))
            prev_oi = 0
            if "option_chain" in prev:
                prev_oi = float(prev["option_chain"].get("total_call_oi", 0) + prev["option_chain"].get("total_put_oi", 0))
            
            oi_trend = (total_oi - prev_oi) / total_oi if total_oi > 0 else 0
            
            # Simulated technicals (in production these would use history)
            # For now, we use simple deltas between latest snapshots
            rsi_sim = 50 + (price_delta * 1000) # Simple proxy
            momentum = price_delta * 100
            
            return MarketFeatureVector(
                symbol=symbol,
                timestamp=latest.get("timestamp", 0),
                price_change_5m=price_delta,
                volatility_15m=abs(price_delta), # Simplified
                pcr_ratio=pcr,
                oi_trend=oi_trend,
                net_gamma=net_gex,
                vwap_distance=0.0, # Placeholder
                rsi_14=float(np.clip(rsi_sim, 0, 100)),
                momentum=momentum
            )
            
        except Exception as e:
            logger.error(f"Feature engineering failed for {symbol}: {e}")
            return None

feature_engineering_engine = FeatureEngineeringEngine()
