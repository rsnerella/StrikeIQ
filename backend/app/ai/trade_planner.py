"""
Trade Planner for StrikeIQ
Generates execution plans based on AI signals
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class TradePlan:
    symbol: str
    signal_type: str # BUY, SELL, HOLD
    entry_range: List[float]
    targets: List[float]
    stop_loss: float
    risk_reward: float
    conviction: str # LOW, MEDIUM, HIGH
    reasoning: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class TradePlanner:
    """
    Translates abstract AI signals into actionable trade plans with 
    specific entry, exit, and risk levels.
    """
    
    def __init__(self):
        logger.info("TradePlanner initialized")

    def plan(self, symbol: str, analysis: Any, confidence: float) -> Optional[TradePlan]:
        """
        Generates a trade plan if confidence meets thresholds.
        """
        if confidence < 0.6:
            return None
            
        spot = analysis.key_levels.get("vwap", 0) # Use VWAP as base for entry ranges
        atr = spot * 0.005 # Simplified ATR proxy
        
        signal = "BUY" if analysis.bias == "BULLISH" else "SELL"
        
        if signal == "BUY":
            entry_range = [round(spot - atr*0.2, 2), round(spot + atr*0.2, 2)]
            targets = [round(spot + atr, 2), round(spot + atr*2, 2)]
            stop_loss = round(spot - atr*1.5, 2)
        else:
            entry_range = [round(spot + atr*0.2, 2), round(spot - atr*0.2, 2)]
            targets = [round(spot - atr, 2), round(spot - atr*2, 2)]
            stop_loss = round(spot + atr*1.5, 2)
            
        rr = abs(targets[0] - spot) / abs(stop_loss - spot) if abs(stop_loss - spot) > 0 else 0
        
        conviction = "HIGH" if confidence > 0.8 else "MEDIUM"
        
        reasoning = [
            f"Bias is {analysis.bias} with strength {analysis.bias_strength}",
            f"Regime: {analysis.regime}",
            f"Gamma: {analysis.gamma_analysis['regime']}"
        ]

        return TradePlan(
            symbol=symbol,
            signal_type=signal,
            entry_range=entry_range,
            targets=targets,
            stop_loss=stop_loss,
            risk_reward=round(rr, 2),
            conviction=conviction,
            reasoning=reasoning
        )

trade_planner = TradePlanner()
