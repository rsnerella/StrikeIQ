"""
Strategy Decision Engine for StrikeIQ
Smart money logic with institutional positioning analysis
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
import logging
import math

from app.core.risk_mode import RISK_MODE
from .ai_logger import log, log_decision, log_market_data, log_fetching

logger = logging.getLogger(__name__)

RISK_MODE = "SAFE"   # SAFE | AGGRESSIVE

@dataclass
class StrategyDecision:
    """Strategy decision result"""
    strategy: str
    regime: str
    bias_confidence: float
    execution_probability: float
    reasoning: list[str]
    metadata: Optional[Dict[str, Any]] = None

    @property
    def action(self) -> str:
        """Alias for strategy for backward compatibility"""
        return self.strategy
    
    @property
    def confidence(self) -> float:
        """Alias for bias_confidence for backward compatibility"""
        return self.bias_confidence

class StrategyDecisionEngine:
    """Smart money strategy decision engine"""
    
    def __init__(self):
        logger.info("StrategyDecisionEngine initialized")
    
    def decide_strategy(self, bias_result, features, snapshot=None) -> StrategyDecision:
        """Smart money strategy decision based on institutional positioning"""
        try:
            # STEP 1: EXTRACT REQUIRED INPUTS
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

            spot = features.get("spot", 0)
            oi_calls = sum(features.get("call_oi_distribution", {}).values())
            oi_puts = sum(features.get("put_oi_distribution", {}).values())
            
            # Robustness Fallback: Use totals if distributions are empty
            if not oi_calls and features.get("total_call_oi"):
                oi_calls = features["total_call_oi"]
            if not oi_puts and features.get("total_put_oi"):
                oi_puts = features["total_put_oi"]

            oi_change_calls = features.get("oi_change_calls", 0)
            oi_change_puts = features.get("oi_change_puts", 0)
            
            call_wall = features.get("call_wall_strike", 0)
            put_wall = features.get("put_wall_strike", 0)
            net_gex = features.get("gex_profile", {}).get("net_gamma", 0)
            
            # Additional features for tracing
            rsi = features.get("rsi", 0)
            iv = features.get("iv") or features.get("volatility", 0)
            pcr = oi_puts / max(oi_calls, 1)
            total_oi = oi_calls + oi_puts
            oi_diff = oi_change_puts - oi_change_calls
            
            # Additional features
            rsi = features.get("rsi", 0)
            iv = features.get("iv") or features.get("volatility", 0)
            pcr = oi_puts / max(oi_calls, 1)
            total_oi = oi_calls + oi_puts
            oi_diff = oi_change_puts - oi_change_calls

            # VALIDATE: If any critical value missing → return NO_TRADE with confidence 0
            if spot <= 0 or (oi_calls == 0 and oi_puts == 0):
                return StrategyDecision(
                    strategy='NO_TRADE',
                    regime='UNKNOWN',
                    bias_confidence=0.0,
                    execution_probability=0.0,
                    reasoning=['Missing critical market data']
                )
            
            # STEP 2: UPGRADE OI SIGNAL (SMART)
            total_oi = oi_calls + oi_puts
            threshold = total_oi * 0.02  # 2% of total OI (more sensitive)
            
            oi_diff = oi_change_puts - oi_change_calls
            
            # OI DEBUG
            logger.info(f"[OI DEBUG] oi_diff={oi_diff} threshold={threshold}")
            
            if abs(oi_diff) > threshold:
                oi_signal = 1 if oi_diff > 0 else -1
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
            
            # PRICE MOMENTUM SIGNAL (CRITICAL)
            price_signal = 0

            if snapshot:
                recent_prices = getattr(snapshot, "recent_prices", None)

                if recent_prices and len(recent_prices) >= 3:
                    if recent_prices[-1] < recent_prices[-2] < recent_prices[-3]:
                        price_signal = -1   # downtrend
                    elif recent_prices[-1] > recent_prices[-2] > recent_prices[-3]:
                        price_signal = 1    # uptrend
            
            logger.info(f"[PRICE SIGNAL] {price_signal}")

            # BUILD raw_score from OI signal + wall signal (was missing — caused NameError crash)
            raw_score = float(oi_signal) * 1.0 + float(wall_signal) * 0.8

            # Add price momentum
            if RISK_MODE == "AGGRESSIVE":
                raw_score += 1.2 * price_signal
            else:
                raw_score += 0.8 * price_signal
            adjusted_score = raw_score * regime_factor * 1.2
            
            # STEP 6: DECISION LOGIC
            
            threshold = 0.6
            if RISK_MODE == "AGGRESSIVE":
                threshold = 0.3

            if adjusted_score >= threshold:
                action = "BUY"
            elif adjusted_score <= -threshold:
                action = "SELL"
            else:
                # FORCE WEAK SIGNAL IN AGGRESSIVE MODE
                if RISK_MODE == "AGGRESSIVE":
                    if adjusted_score > 0:
                        action = "BUY"
                    elif adjusted_score < 0:
                        action = "SELL"
                    else:
                        action = "NO_TRADE"
                else:
                    action = "NO_TRADE"

            # QUALITY FILTER (CRITICAL)
            if RISK_MODE == "AGGRESSIVE":
                # Avoid flat noise trades
                if abs(adjusted_score) < 0.15:
                    action = "NO_TRADE"
                # Avoid zero momentum + zero OI
                if oi_signal == 0 and wall_signal == 0:
                    action = "NO_TRADE"
            
            # TRACE LOG
            logger.info(f"[RISK MODE] {RISK_MODE} action={action} confidence={confidence if 'confidence' in locals() else 0}")
            
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
            
            # Final Safety Filter (RELAXED)
            if RISK_MODE == "SAFE" and confidence < 0.12:
                action = "NO_TRADE"
                reasoning.append("Very low conviction")
            
            # Minimum Confidence Floor for active signals (CRITICAL)
            if action != "NO_TRADE" and confidence < 0.25:
                confidence = 0.25
            
            if action == "NO_TRADE":
                reasoning.append("Insufficient institutional pressure")
            
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
                confidence *= 0.8
            
            if trap_signal:
                confidence *= 0.85
                reasoning.append("Trap detected → confidence reduced")
            
            if entry_signal != "ENTER_NOW":
                confidence *= 0.9
                reasoning.append("Suboptimal entry timing")
            
            # STEP 7: ADD MULTI-TIMEFRAME FILTER (ADVANCED)
            htf_bias = features.get("htf_bias")
            
            if htf_bias:
                if htf_bias != action:
                    confidence *= 0.8
                    reasoning.append("Higher timeframe opposes trade")
            
            # STEP 8: LOW CONFIDENCE FILTER (RELAXED)
            if confidence < 0.18:
                reasoning.append("Very low confidence → weak signal")
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
            
            # STEP 11: CLEAN DECISION LOG
            log_decision(confidence, action)
            
            # TRADE SCORE (0 to 1)
            trade_score = 0
            # OI strength
            if abs(oi_signal) == 1:
                trade_score += 0.3
            # Wall strength
            if abs(wall_signal) == 1:
                trade_score += 0.3
            # Momentum strength
            if abs(price_signal) == 1:
                trade_score += 0.2
            # Gamma alignment
            if net_gex < 0:
                trade_score += 0.2
            # Clamp
            trade_score = min(trade_score, 1.0)

            # STEP 12: VERIFY STRATEGY OUTPUT
            strategy_decision = StrategyDecision(
                strategy=action,
                regime=regime,
                bias_confidence=confidence,
                execution_probability=probability,
                reasoning=reasoning,
                metadata={
                    "entry": entry_signal,
                    "trap": trap_signal,
                    "trade_score": trade_score
                }
            )
            
            # --- TRACE 3: PRODUCTION SAFE LIGHT TRACE ---
            import time
            now = time.time()
            if not hasattr(self, "_last_trace_ts"):
                self._last_trace_ts = 0
            
            if now - self._last_trace_ts > 10:
                score = adjusted_score
                log_market_data(price, pcr)
                self._last_trace_ts = now
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
