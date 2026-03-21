"""
Early Warning Engine for StrikeIQ
Scans for probability moves and structural risks
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class EarlyWarning:
    alert_type: str  # VOLATILITY_SPIKE, GAMMA_FLIP_RISK, MOMENTUM_DIVERGENCE, etc.
    severity: str    # LOW, MEDIUM, HIGH, CRITICAL
    probability_move: float
    direction_bias: str
    description: str
    suggested_action: str
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class EarlyWarningEngine:
    """
    Scans real-time feature vectors and market analysis for emerging risks or opportunities.
    Provides proactive alerts before price action confirms.
    """
    
    def __init__(self):
        logger.info("EarlyWarningEngine initialized")

    def scan(self, fv: Any, snapshot: Dict[str, Any], analysis: Any) -> List[EarlyWarning]:
        """
        Scans for various warning patterns and returns a list of active alerts.
        """
        warnings = []
        
        # 1. Gamma Flip Risk
        spot = snapshot.spot if hasattr(snapshot, 'spot') else 0
        gex_flip = analysis.key_levels.get("gex_flip", 0)
        dist_to_flip = abs(spot - gex_flip) / spot if spot > 0 else 1.0
        
        if dist_to_flip < 0.002: # Within 0.2% of flip level
            warnings.append(EarlyWarning(
                alert_type="GAMMA_FLIP_RISK",
                severity="HIGH",
                probability_move=0.75,
                direction_bias="VOLATILE",
                description=f"Spot price ({spot}) is approaching the Gamma Flip Level ({gex_flip}). Expect increased volatility.",
                suggested_action="Hedge open delta positions or tighten stop losses."
            ))
            
        # 2. Momentum / Bias Divergence
        if analysis.bias == "BULLISH" and fv.momentum < -0.5:
            warnings.append(EarlyWarning(
                alert_type="MOMENTUM_DIVERGENCE",
                severity="MEDIUM",
                probability_move=0.6,
                direction_bias="BEARISH",
                description="Bullish bias detected but momentum is turning negative.",
                suggested_action="Consider scaling out of longs or waiting for momentum confirmation."
            ))
            
        # 3. Volatility Compression / Expansion
        if fv.volatility_15m < 0.002:
            warnings.append(EarlyWarning(
                alert_type="VOLATILITY_COMPRESSION",
                severity="LOW",
                probability_move=0.8,
                direction_bias="NEUTRAL",
                description="Price is in a tight compression zone. Expansion is imminent.",
                suggested_action="Look for breakout patterns near key levels."
            ))

        return warnings

early_warning_engine = EarlyWarningEngine()
