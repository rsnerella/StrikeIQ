import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class StrategyPlanningEngine:
    """
    Decides on trade direction, type and strike based on advanced signals.
    Inputs: option_chain, oi_clusters, gamma_levels, smart_money_signals
    """
    
    def plan_strategy(self, signals: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main planning function
        Args:
            signals: Dictionary containing market data and signals
        Returns:
            Dictionary with strategy details
        """
        try:
            smart_money = signals.get('smart_money_signals', {})
            bias = smart_money.get('bias', 'neutral')
            confidence = smart_money.get('confidence', 0.5)
            spot = smart_money.get('spot', 0)
            
            if spot == 0:
                # Try to get from metrics if provided separately
                spot = signals.get('spot', 22500)
            
            # Strike selection logic (ATM, ATM+100, ATM-100)
            if bias == 'bullish':
                if confidence > 0.75:
                    return {
                        "strategy": "Long Call",
                        "direction": "CALL",
                        "trade_type": "BUY",
                        "strike": self._get_strike(spot, "ATM")
                    }
                else:
                    return {
                        "strategy": "Bull Call Spread",
                        "direction": "CALL",
                        "trade_type": "BUY",
                        "strike": self._get_strike(spot, "ATM")
                    }
            elif bias == 'bearish':
                if confidence > 0.75:
                    return {
                        "strategy": "Long Put",
                        "direction": "PUT",
                        "trade_type": "BUY",
                        "strike": self._get_strike(spot, "ATM")
                    }
                else:
                    return {
                        "strategy": "Bear Put Spread",
                        "direction": "PUT",
                        "trade_type": "BUY",
                        "strike": self._get_strike(spot, "ATM")
                    }
            else:
                # Neutral bias - range bound
                return {
                    "strategy": "Iron Condor",
                    "direction": "CALL",
                    "trade_type": "SELL",
                    "strike": self._get_strike(spot, "ATM+100")
                }
                
        except Exception as e:
            logger.error(f"Error in strategy planning: {e}")
            return {
                "strategy": "Hold",
                "direction": "NEUTRAL",
                "trade_type": "NONE",
                "strike": 0
            }

    def _get_strike(self, spot: float, offset: str) -> float:
        """Helper to get strike based on ATM and offset"""
        atm = round(spot / 50) * 50
        if offset == "ATM+100":
            return atm + 100
        elif offset == "ATM-100":
            return atm - 100
        return atm
