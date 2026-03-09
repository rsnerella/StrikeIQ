"""
Strategy Engine - Selects trading strategy based on formula signals
Lightweight, optimized for Intel i5 CPU, 8GB RAM
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from .formula_engine import FormulaSignal

logger = logging.getLogger(__name__)

@dataclass
class StrategyChoice:
    """Selected trading strategy with confidence"""
    strategy: str  # Long Call, Long Put, Bull Call Spread, etc.
    confidence: float  # 0.0 - 1.0
    market_bias: str  # bullish, bearish, neutral
    reasoning: str  # Why this strategy was chosen

class StrategyEngine:
    """
    Selects optimal trading strategy based on formula signals
    Maps signal patterns to appropriate option strategies
    """
    
    def __init__(self):
        self.strategies = {
            "Long Call": self._long_call_conditions,
            "Long Put": self._long_put_conditions,
            "Bull Call Spread": self._bull_call_spread_conditions,
            "Bear Put Spread": self._bear_put_spread_conditions,
            "Iron Condor": self._iron_condor_conditions,
            "Straddle": self._straddle_conditions,
            "Strangle": self._strangle_conditions
        }
    
    async def select_strategy(self, formula_signals: Dict[str, FormulaSignal]) -> StrategyChoice:
        """
        Analyze formula signals and select optimal strategy.
        Adjusted by historical performance scores from Redis (Step 8).
        """
        try:
            # Calculate overall market bias
            market_bias = self._determine_market_bias(formula_signals)
            
            # Load scores from Redis (Step 8)
            from app.services.cache_service import cache_service
            scores = await cache_service.get("ai:strategy_scores") or {}
            
            # Evaluate each strategy
            strategy_scores = []
            for strategy_name, condition_func in self.strategies.items():
                base_score, reasoning = condition_func(formula_signals, market_bias)
                if base_score > 0:
                    # Step 8: Only adjust weighting, prefer strategies with higher score
                    learning_weight = scores.get(strategy_name, 0.5)
                    weight_factor = 0.8 + (0.4 * learning_weight)
                    weighted_score = base_score * weight_factor
                    
                    strategy_scores.append((strategy_name, weighted_score, reasoning))
            
            # Sort by weighted score
            strategy_scores.sort(key=lambda x: x[1], reverse=True)
            
            if strategy_scores:
                best_strategy = strategy_scores[0]
                return StrategyChoice(
                    strategy=best_strategy[0],
                    confidence=best_strategy[1],
                    market_bias=market_bias,
                    reasoning=best_strategy[2]
                )
            else:
                return StrategyChoice(
                    strategy="Hold",
                    confidence=0.0,
                    market_bias="neutral",
                    reasoning="No clear strategy signal"
                )
                
        except Exception as e:
            logger.error(f"Strategy selection error: {e}")
            return StrategyChoice(
                strategy="Hold",
                confidence=0.0,
                market_bias="neutral",
                reasoning="Strategy analysis error"
            )
    
    def _determine_market_bias(self, formula_signals: Dict[str, FormulaSignal]) -> str:
        """Determine overall market bias from signals"""
        try:
            buy_weight = 0.0
            sell_weight = 0.0
            total_weight = 0.0
            
            # Weight important formulas more heavily
            weights = {
                "F01": 2.0,  # PCR - most important
                "F02": 1.5,  # OI imbalance
                "F03": 1.8,  # Gamma regime
                "F06": 1.3,  # Delta imbalance
                "F10": 1.4   # Flow imbalance
            }
            
            for formula_id, signal in formula_signals.items():
                weight = weights.get(formula_id, 1.0)
                total_weight += weight
                
                if signal.signal == "BUY":
                    buy_weight += weight * signal.confidence
                elif signal.signal == "SELL":
                    sell_weight += weight * signal.confidence
            
            if total_weight == 0:
                return "neutral"
            
            buy_ratio = buy_weight / total_weight
            sell_ratio = sell_weight / total_weight
            
            # Lower threshold for bias determination
            if buy_ratio > 0.25:
                return "bullish"
            elif sell_ratio > 0.25:
                return "bearish"
            else:
                return "neutral"
                
        except Exception as e:
            logger.error(f"Market bias determination error: {e}")
            return "neutral"
    
    def _long_call_conditions(self, formula_signals: Dict[str, FormulaSignal], market_bias: str) -> Tuple[float, str]:
        """Check conditions for Long Call strategy"""
        if market_bias != "bullish":
            return 0.0, "Market not bullish"
        
        score = 0.0
        reasons = []
        
        # Key bullish indicators
        if formula_signals.get("F01", FormulaSignal("", 0, "")).signal == "BUY":
            score += 0.3
            reasons.append("PCR bullish")
        
        if formula_signals.get("F03", FormulaSignal("", 0, "")).signal == "BUY":
            score += 0.25
            reasons.append("Positive gamma")
        
        if formula_signals.get("F06", FormulaSignal("", 0, "")).signal == "BUY":
            score += 0.25
            reasons.append("Call flow dominance")
        
        if formula_signals.get("F10", FormulaSignal("", 0, "")).signal == "BUY":
            score += 0.2
            reasons.append("Strong call flow")
        
        return min(score, 1.0), "; ".join(reasons) if reasons else "General bullish bias"
    
    def _long_put_conditions(self, formula_signals: Dict[str, FormulaSignal], market_bias: str) -> Tuple[float, str]:
        """Check conditions for Long Put strategy"""
        if market_bias != "bearish":
            return 0.0, "Market not bearish"
        
        score = 0.0
        reasons = []
        
        # Key bearish indicators
        if formula_signals.get("F01", FormulaSignal("", 0, "")).signal == "SELL":
            score += 0.3
            reasons.append("PCR bearish")
        
        if formula_signals.get("F03", FormulaSignal("", 0, "")).signal == "SELL":
            score += 0.25
            reasons.append("Negative gamma")
        
        if formula_signals.get("F06", FormulaSignal("", 0, "")).signal == "SELL":
            score += 0.25
            reasons.append("Put flow dominance")
        
        if formula_signals.get("F10", FormulaSignal("", 0, "")).signal == "SELL":
            score += 0.2
            reasons.append("Strong put flow")
        
        return min(score, 1.0), "; ".join(reasons) if reasons else "General bearish bias"
    
    def _bull_call_spread_conditions(self, formula_signals: Dict[str, FormulaSignal], market_bias: str) -> Tuple[float, str]:
        """Check conditions for Bull Call Spread strategy"""
        if market_bias != "bullish":
            return 0.0, "Market not bullish"
        
        score = 0.0
        reasons = []
        
        # Moderate bullish with risk control
        f01 = formula_signals.get("F01", FormulaSignal("", 0, ""))
        if f01.signal == "BUY" and f01.confidence < 0.8:
            score += 0.3
            reasons.append("Moderate PCR bullish")
        
        f03 = formula_signals.get("F03", FormulaSignal("", 0, ""))
        if f03.signal == "BUY" and f03.confidence < 0.8:
            score += 0.25
            reasons.append("Moderate positive gamma")
        
        # Check for range-bound but bullish bias
        f05 = formula_signals.get("F05", FormulaSignal("", 0, ""))
        if f05.signal == "HOLD":
            score += 0.2
            reasons.append("Range-bound with bullish bias")
        
        # Lower volatility preference for spreads
        f07 = formula_signals.get("F07", FormulaSignal("", 0, ""))
        if f07.reason and "low volatility" in f07.reason.lower():
            score += 0.25
            reasons.append("Low volatility favorable for spreads")
        
        return min(score, 1.0), "; ".join(reasons) if reasons else "Moderate bullish setup"
    
    def _bear_put_spread_conditions(self, formula_signals: Dict[str, FormulaSignal], market_bias: str) -> Tuple[float, str]:
        """Check conditions for Bear Put Spread strategy"""
        if market_bias != "bearish":
            return 0.0, "Market not bearish"
        
        score = 0.0
        reasons = []
        
        # Moderate bearish with risk control
        f01 = formula_signals.get("F01", FormulaSignal("", 0, ""))
        if f01.signal == "SELL" and f01.confidence < 0.8:
            score += 0.3
            reasons.append("Moderate PCR bearish")
        
        f03 = formula_signals.get("F03", FormulaSignal("", 0, ""))
        if f03.signal == "SELL" and f03.confidence < 0.8:
            score += 0.25
            reasons.append("Moderate negative gamma")
        
        # Check for range-bound but bearish bias
        f05 = formula_signals.get("F05", FormulaSignal("", 0, ""))
        if f05.signal == "HOLD":
            score += 0.2
            reasons.append("Range-bound with bearish bias")
        
        # Lower volatility preference for spreads
        f07 = formula_signals.get("F07", FormulaSignal("", 0, ""))
        if f07.reason and "low volatility" in f07.reason.lower():
            score += 0.25
            reasons.append("Low volatility favorable for spreads")
        
        return min(score, 1.0), "; ".join(reasons) if reasons else "Moderate bearish setup"
    
    def _iron_condor_conditions(self, formula_signals: Dict[str, FormulaSignal], market_bias: str) -> Tuple[float, str]:
        """Check conditions for Iron Condor strategy"""
        if market_bias != "neutral":
            return 0.0, "Market not neutral"
        
        score = 0.0
        reasons = []
        
        # Neutral market requirements
        f01 = formula_signals.get("F01", FormulaSignal("", 0, ""))
        if f01.signal == "HOLD":
            score += 0.3
            reasons.append("PCR neutral")
        
        f03 = formula_signals.get("F03", FormulaSignal("", 0, ""))
        if f03.signal == "HOLD":
            score += 0.25
            reasons.append("Gamma neutral")
        
        # Range-bound preference
        f05 = formula_signals.get("F05", FormulaSignal("", 0, ""))
        if f05.signal == "HOLD" and f05.confidence >= 0.5:
            score += 0.25
            reasons.append("Price within expected range")
        
        # Low to moderate volatility
        f07 = formula_signals.get("F07", FormulaSignal("", 0, ""))
        if f07.reason and ("normal volatility" in f07.reason.lower() or "low volatility" in f07.reason.lower()):
            score += 0.2
            reasons.append("Favorable volatility regime")
        
        return min(score, 1.0), "; ".join(reasons) if reasons else "Neutral market setup"
    
    def _straddle_conditions(self, formula_signals: Dict[str, FormulaSignal], market_bias: str) -> Tuple[float, str]:
        """Check conditions for Straddle strategy"""
        score = 0.0
        reasons = []
        
        # High volatility or breakout potential
        f07 = formula_signals.get("F07", FormulaSignal("", 0, ""))
        if f07.reason and ("extreme volatility" in f07.reason.lower() or "elevated volatility" in f07.reason.lower()):
            score += 0.4
            reasons.append("High volatility environment")
        
        # High breakout probability
        f05 = formula_signals.get("F05", FormulaSignal("", 0, ""))
        if f05.reason and "breakout probability" in f05.reason.lower():
            score += 0.3
            reasons.append("High breakout probability")
        
        # Volume spike indicating potential move
        f04 = formula_signals.get("F04", FormulaSignal("", 0, ""))
        if f04.confidence > 0.6:
            score += 0.3
            reasons.append("High volume activity")
        
        return min(score, 1.0), "; ".join(reasons) if reasons else "Volatility/breakout setup"
    
    def _strangle_conditions(self, formula_signals: Dict[str, FormulaSignal], market_bias: str) -> Tuple[float, str]:
        """Check conditions for Strangle strategy"""
        score = 0.0
        reasons = []
        
        # Moderate volatility with directional uncertainty
        f07 = formula_signals.get("F07", FormulaSignal("", 0, ""))
        if f07.reason and ("elevated volatility" in f07.reason.lower()):
            score += 0.3
            reasons.append("Elevated volatility")
        
        # Neutral bias but expecting movement
        if market_bias == "neutral":
            score += 0.2
            reasons.append("Neutral bias with movement expectation")
        
        # Moderate breakout probability
        f05 = formula_signals.get("F05", FormulaSignal("", 0, ""))
        if f05.confidence > 0.5:
            score += 0.3
            reasons.append("Moderate breakout potential")
        
        # Some volume activity but not extreme
        f04 = formula_signals.get("F04", FormulaSignal("", 0, ""))
        if 0.5 < f04.confidence < 0.8:
            score += 0.2
            reasons.append("Moderate volume activity")
        
        return min(score, 1.0), "; ".join(reasons) if reasons else "Moderate volatility setup"
