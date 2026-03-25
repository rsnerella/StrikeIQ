"""
Confidence Scoring Engine for StrikeIQ
Weights signals across 1m, 5m, and 15m views
"""

import logging
import numpy as np
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class ConfidenceScoringEngine:
    """
    Evaluates the conviction of a signal by cross-referencing multiple timeframes
    and validates against structural confluence.
    """
    
    def __init__(self):
        logger.info("ConfidenceScoringEngine initialized")

    def score(self, fv_1m: Any, fv_5m: Optional[Dict], fv_15m: Optional[Dict], analysis: Any, warnings: List[Any]) -> float:
        """
        Computes a confidence score from 0.0 to 1.0.
        """
        score = 0.5 # Base confidence
        
        # 1. Multi-timeframe Confluence
        if fv_5m and fv_15m:
            if np.sign(fv_1m.momentum) == np.sign(fv_5m.get("momentum", 0)) == np.sign(fv_15m.get("momentum", 0)):
                score += 0.2
            elif np.sign(fv_1m.momentum) != np.sign(fv_5m.get("momentum", 0)):
                score -= 0.1
                
        # 2. Bias Strength Integration
        score += (analysis.bias_strength - 0.5) * 0.4
        
        # 3. Warning Penalties
        critical_warnings = [w for w in warnings if w.severity == "CRITICAL"]
        high_warnings = [w for w in warnings if w.severity == "HIGH"]
        
        score -= (len(critical_warnings) * 0.3)
        score -= (len(high_warnings) * 0.15)
        
        # 4. IV Percentile Check (Prefer lower IV for directional trades)
        iv_p = analysis.volatility_state.get("iv_percentile", 0.5)
        if iv_p > 0.8:
            score -= 0.1 # Expensive premiums reduce directional conviction
            
        final_score = float(np.clip(score, 0.0, 1.0))
        logger.debug(f"Confidence score computed: {final_score:.2f}")
        
        return final_score

import numpy as np
confidence_scoring_engine = ConfidenceScoringEngine()
