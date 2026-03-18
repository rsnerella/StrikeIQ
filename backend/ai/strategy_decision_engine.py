"""
Strategy Decision Engine for StrikeIQ
Smart money logic with institutional positioning analysis
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
import logging
import math

logger = logging.getLogger(__name__)

@dataclass
class StrategyDecision:
    """Strategy decision result"""
    strategy: str
    regime: str
    bias_confidence: float
    execution_probability: float
    reasoning: list[str]
    metadata: Optional[Dict[str, Any]] = None

class StrategyDecisionEngine:
    """Smart money strategy decision engine"""
    
    def __init__(self):
        logger.info("StrategyDecisionEngine initialized")
    
    def decide_strategy(self, bias_result, features, snapshot=None) -> StrategyDecision:
        """Smart money strategy decision based on institutional positioning"""
        print("[STRATEGY ENGINE CALLED]")
        print("[DEBUG] decide_strategy called with features:", list(features.keys()))
        try:
            # STEP 1: ADD REQUIRED INPUTS
            price = features.get("spot")
            recent_high = features.get("recent_high")
            recent_low = features.get("recent_low")
            volatility = features.get("iv") or features.get("volatility")
            volume = features.get("volume", 0)
            
            # VALIDATE: If missing → skip entry logic (do not break system)
            entry_logic_available = all([
                price is not None,
                recent_high is not None,
                recent_low is not None,
                volume is not None
            ])
            
            # STEP 2: EXTRACT REQUIRED INPUTS
            spot = features.get("spot", 0)
            oi_calls = sum(features.get("call_oi_distribution", {}).values())
            oi_puts = sum(features.get("put_oi_distribution", {}).values())
            
            # STEP 1: FIX OI SIGNAL BUG (CRITICAL)
            oi_change_calls = features.get("oi_change_calls", 0)
            oi_change_puts = features.get("oi_change_puts", 0)
            
            call_wall = features.get("call_wall_strike", 0)
            put_wall = features.get("put_wall_strike", 0)
            net_gex = features.get("gex_profile", {}).get("net_gamma", 0)
            
            # VALIDATE: If any critical value missing → return NO_TRADE with confidence 0
            if spot <= 0 or (oi_calls == 0 and oi_puts == 0):
                print("[SMART MONEY DEBUG]", {
                    "error": "MISSING_CRITICAL_DATA",
                    "spot": spot,
                    "oi_calls": oi_calls,
                    "oi_puts": oi_puts,
                    "action": "NO_TRADE",
                    "confidence": 0.0
                })
                return StrategyDecision(
                    strategy='NO_TRADE',
                    regime='UNKNOWN',
                    bias_confidence=0.0,
                    execution_probability=0.0,
                    reasoning=['Missing critical market data']
                )
            
            # STEP 2: UPGRADE OI SIGNAL (SMART)
            total_oi = oi_calls + oi_puts
            threshold = total_oi * 0.05  # 5% of total OI
            
            oi_diff = oi_change_puts - oi_change_calls
            
            if oi_diff > threshold:
                oi_signal = +1
            elif oi_diff < -threshold:
                oi_signal = -1
            else:
                oi_signal = 0
            
            # STEP 3: UPGRADE WALL PRESSURE (IMPORTANT)
            # Provide default values when walls are None
            if not call_wall:
                call_wall = spot + 200  # Default call wall 200 points above
            if not put_wall:
                put_wall = spot - 200  # Default put wall 200 points below
            
            distance_call = abs(call_wall - spot)
            distance_put = abs(spot - put_wall)
            
            call_pressure = oi_calls / max(distance_call, 1)
            put_pressure = oi_puts / max(distance_put, 1)
            
            if call_pressure > put_pressure:
                wall_signal = -1
            elif put_pressure > call_pressure:
                wall_signal = +1
            else:
                wall_signal = 0
            
            # STEP 4: UPGRADE GEX LOGIC (DYNAMIC)
            gex_strength = min(abs(net_gex) / 100000, 1.0)
            
            if net_gex > 0:
                regime_factor = 1 - (0.5 * gex_strength)   # mean reversion
            else:
                regime_factor = 1 + (0.5 * gex_strength)   # trending
            
            # Calculate adjusted score with increased signal strength
            raw_score = oi_signal + wall_signal
            adjusted_score = raw_score * regime_factor * 1.2
            
            # STEP 6: DECISION LOGIC
            if adjusted_score >= 1:
                action = "BUY"
            elif adjusted_score <= -1:
                action = "SELL"
            else:
                action = "NO_TRADE"
            
            # STEP 7: FIX OVERCONFIDENCE (MANDATORY)
            max_score = 2 * 1.5
            base_conf = abs(adjusted_score) / max_score
            
            # Cap confidence (real markets never 100%)
            confidence = min(base_conf, 0.85)
            
            # STEP 8: ADD REASONING ENGINE (CRITICAL)
            reasoning = []
            
            if oi_signal == +1:
                reasoning.append("Put OI buildup → bullish positioning")
            elif oi_signal == -1:
                reasoning.append("Call OI buildup → bearish positioning")
            
            if wall_signal == +1:
                reasoning.append("Price closer to strong put support")
            elif wall_signal == -1:
                reasoning.append("Price near strong call resistance")
            
            if net_gex < 0:
                reasoning.append("Negative gamma → trending behavior")
            else:
                reasoning.append("Positive gamma → mean reversion")
            
            if action == "NO_TRADE":
                reasoning.append("Insufficient institutional pressure")
            
            # STEP 10: SMART MONEY DEBUG OUTPUT
            print("[SMART MONEY DEBUG]", {
                "spot": spot,
                "oi_calls": oi_calls,
                "oi_puts": oi_puts,
                "oi_change_calls": oi_change_calls,
                "oi_change_puts": oi_change_puts,
                "oi_diff": oi_diff,
                "threshold": threshold,
                "call_wall": call_wall,
                "put_wall": put_wall,
                "distance_call": distance_call,
                "distance_put": distance_put,
                "call_pressure": call_pressure,
                "put_pressure": put_pressure,
                "net_gex": net_gex,
                "gex_strength": gex_strength,
                "oi_signal": oi_signal,
                "wall_signal": wall_signal,
                "regime_factor": regime_factor,
                "raw_score": raw_score,
                "adjusted_score": adjusted_score,
                "confidence": confidence,
                "action": action,
                "reasoning": reasoning
            })
            
            # Classify market regime
            regime = self.classify_market_regime(features)
            
            # STEP 3: LIQUIDITY TRAP DETECTION (UPGRADED)
            trap_signal = False
            trap_reason = None
            
            if entry_logic_available:
                # Bull trap (fake breakout)
                if price > recent_high and net_gex > 0:
                    trap_signal = True
                    trap_reason = "Bull trap: breakout in positive gamma (mean reversion)"
                
                # Bear trap (fake breakdown)
                elif price < recent_low and net_gex > 0:
                    trap_signal = True
                    trap_reason = "Bear trap: breakdown in positive gamma (mean reversion)"
            
            # STEP 4: ENTRY TIMING LOGIC (WITH BUFFER)
            entry_signal = "WAIT"
            
            if entry_logic_available and action != "NO_TRADE":
                buffer = price * 0.002  # 0.2%
                
                # BUY condition
                if action == "BUY":
                    if price <= put_wall + buffer:
                        entry_signal = "ENTER_NOW"
                    else:
                        entry_signal = "WAIT_FOR_PULLBACK"
                
                # SELL condition
                elif action == "SELL":
                    if price >= call_wall - buffer:
                        entry_signal = "ENTER_NOW"
                    else:
                        entry_signal = "WAIT_FOR_PULLBACK"
            
            # STEP 5: SMOOTH PROBABILITY CURVE
            probability = 1 / (1 + math.exp(-adjusted_score * 0.7))
            
            # STEP 6: ADD CONFIDENCE DAMPENERS
            # Reduce confidence in weak environments
            if regime_factor < 1:  # mean reversion
                confidence *= 0.6
            
            if trap_signal:
                confidence *= 0.7
                reasoning.append("Trap detected → confidence reduced")
            
            if entry_signal != "ENTER_NOW":
                confidence *= 0.85
                reasoning.append("Suboptimal entry timing")
            
            # STEP 7: ADD MULTI-TIMEFRAME FILTER (ADVANCED)
            htf_bias = features.get("htf_bias")
            
            if htf_bias:
                if htf_bias != action:
                    confidence *= 0.6
                    reasoning.append("Higher timeframe opposes trade")
            
            # STEP 8: LOW CONFIDENCE FILTER (RELAXED)
            if confidence < 0.25:
                action = "NO_TRADE"
                reasoning.append("Very low confidence → trade filtered")
            elif 0.25 <= confidence < 0.4:
                reasoning.append("Medium confidence trade (allowed)")
            
            # STEP 9: FINAL CLAMP
            confidence = min(max(confidence, 0), 0.85)
            probability = min(max(probability, 0), 1)
            
            # STEP 10: EXTEND REASONING ENGINE
            if trap_signal:
                reasoning.append(trap_reason)
            
            if entry_signal == "ENTER_NOW":
                reasoning.append("Optimal entry near key level")
            elif entry_signal == "WAIT_FOR_PULLBACK":
                reasoning.append("Wait for better price near support/resistance")
            
            # STEP 11: OPTIMIZED DEBUG OUTPUT
            print("[OPTIMIZED DEBUG]", {
                "adjusted_score": adjusted_score,
                "confidence": confidence,
                "action": action
            })
            
            # STEP 12: VERIFY STRATEGY OUTPUT
            strategy_decision = StrategyDecision(
                strategy=action,
                regime=regime,
                bias_confidence=confidence,
                execution_probability=probability,
                reasoning=reasoning,
                metadata={
                    "entry": entry_signal,
                    "trap": trap_signal
                }
            )
            print("[STRATEGY OUTPUT]", {
                "strategy": strategy_decision.strategy,
                "confidence": strategy_decision.bias_confidence
            })
            
            return strategy_decision
            
        except Exception as e:
            logger.error(f"Strategy decision failed: {e}")
            return self.get_default_strategy()
    
    def classify_market_regime(self, features) -> str:
        """Classify market regime from features"""
        try:
            # Volatility regime
            iv_regime = features.get('iv_regime', 'MEDIUM')
            
            # Gamma flip probability
            gamma_flip = features.get('gamma_flip_probability', 0)
            
            # Liquidity vacuum
            liquidity_vacuum = features.get('liquidity_vacuum', 0)
            
            # OI concentration
            oi_concentration = features.get('oi_concentration', 0)
            
            # Regime classification logic
            if iv_regime == 'HIGH' and gamma_flip > 0.7:
                return 'BREAKOUT'
            elif iv_regime == 'LOW' and liquidity_vacuum < 0.3:
                return 'RANGING'
            elif abs(gamma_flip - 0.5) < 0.2 and oi_concentration > 0.6:
                return 'TRENDING'
            else:
                return 'RANGING'
                
        except Exception as e:
            logger.error(f"Regime classification failed: {e}")
            return 'RANGING'
    
    def calculate_execution_probability(self, strategy, bias_result, regime) -> float:
        """Calculate probability of successful execution"""
        base_probability = 0.5
        
        # Strategy-specific adjustments - updated for new strategy names
        if strategy in ['BUY', 'SELL']:
            if regime == 'TRENDING':
                base_probability += 0.3
            else:
                base_probability -= 0.2
        elif strategy == 'MEAN_REVERSION':
            if regime == 'RANGING':
                base_probability += 0.3
            else:
                base_probability -= 0.1
        elif strategy == 'BREAKOUT':
            if regime == 'BREAKOUT':
                base_probability += 0.4
            else:
                base_probability -= 0.3
        elif strategy == 'NO_TRADE':
            base_probability = 0.0
        
        # Confidence adjustment
        base_probability += (bias_result.confidence - 0.5) * 0.4
        
        return max(0.1, min(0.9, base_probability))
    
    def get_default_strategy(self) -> StrategyDecision:
        """Default strategy for error cases"""
        return StrategyDecision(
            strategy='NO_TRADE',
            regime='RANGING',
            bias_confidence=0.0,
            execution_probability=0.0,
            reasoning=['Error in strategy decision', 'No trade executed'],
            metadata={
                "entry": "WAIT",
                "trap": False
            }
        )
