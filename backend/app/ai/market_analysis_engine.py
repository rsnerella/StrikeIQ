"""
Market Analysis Engine for StrikeIQ
Analyzes regime, bias, and levels based on FeatureVectors
"""

import logging
import numpy as np
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class MarketAnalysis:
    regime: str  # TRENDING_UP, TRENDING_DOWN, RANGING, VOLATILE
    bias: str    # BULLISH, BEARISH, NEUTRAL
    bias_strength: float # 0.0 - 1.0
    key_levels: Dict[str, float]
    gamma_analysis: Dict[str, Any]
    volatility_state: Dict[str, Any]
    summary: str

class MarketAnalysisEngine:
    """
    Core AI analytic node that classifies the current market regime and directional bias.
    Integrates technical signals with options market structure (gamma/OI).
    """
    
    def __init__(self):
        logger.info("MarketAnalysisEngine initialized")

    def analyze(self, fv: Any, snapshot: Dict[str, Any]) -> MarketAnalysis:
        """
        Analyzes the market state using a feature vector and current snapshot.
        """
        # 1. Determine Regime
        regime = "RANGING"
        if abs(fv.momentum) > 1.5:
            regime = "TRENDING_UP" if fv.momentum > 0 else "TRENDING_DOWN"
        elif fv.volatility_15m > 0.02:
            regime = "VOLATILE"
            
        # 2. Determine Bias and Strength
        bias = "NEUTRAL"
        bias_strength = 0.5
        
        # PCR + Momentum + Gamma weightings
        weights = {
            "pcr": -0.3, # Inverse: High PCR (put dominance) usually contrarian or high resistance
            "momentum": 0.4,
            "gamma": 0.3
        }
        
        # Simplified scoring
        score = (fv.momentum * weights["momentum"]) + \
                ((1.0 - fv.pcr_ratio) * 0.5) + \
                (np.sign(fv.net_gamma) * 0.2 if hasattr(fv, 'net_gamma') else 0)
        
        if score > 0.2:
            bias = "BULLISH"
            bias_strength = min(1.0, 0.5 + score)
        elif score < -0.2:
            bias = "BEARISH"
            bias_strength = min(1.0, 0.5 + abs(score))
            
        # 3. Extract Levels (Walls, Pain, etc.)
        option_chain = snapshot.get("option_chain", {})
        key_levels = {
            "call_wall": float(option_chain.get("call_wall", 0)),
            "put_wall": float(option_chain.get("put_wall", 0)),
            "max_pain": float(option_chain.get("max_pain", 0)),
            "gex_flip": float(option_chain.get("gex_flip", 0)),
            "vwap": float(snapshot.get("vwap", 0)),
            "ema20": float(snapshot.get("ema20", 0))
        }
        
        # 4. Gamma Analysis
        gamma_analysis = {
            "net_gex": fv.net_gamma,
            "regime": "SHORT_GAMMA" if fv.net_gamma < 0 else "LONG_GAMMA",
            "flip_level": key_levels["gex_flip"],
            "implication": "ACCELERATION" if fv.net_gamma < 0 else "STABILIZATION"
        }
        
        # 5. Volatility State
        volatility_state = {
            "iv_atm": float(option_chain.get("iv_atm", 0)),
            "iv_percentile": float(option_chain.get("iv_percentile", 0.5)),
            "state": "COMPRESSION" if fv.volatility_15m < 0.005 else "EXPANSION",
            "compression": fv.volatility_15m < 0.003
        }
        
        summary = f"Market is {regime} with a {bias} bias ({(bias_strength*100):.1f}% strength). " \
                  f"Gamma profile indicates {gamma_analysis['regime']}."

        return MarketAnalysis(
            regime=regime,
            bias=bias,
            bias_strength=round(bias_strength, 3),
            key_levels=key_levels,
            gamma_analysis=gamma_analysis,
            volatility_state=volatility_state,
            summary=summary
        )

market_analysis_engine = MarketAnalysisEngine()
