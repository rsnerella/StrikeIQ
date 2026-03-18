#!/usr/bin/env python3

# Direct test of strategy decision engine
from typing import Dict, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class StrategyDecision:
    """Strategy decision result"""
    strategy: str
    regime: str
    bias_confidence: float
    execution_probability: float
    reasoning: list[str]

class StrategyDecisionEngine:
    """Smart money strategy decision engine"""
    
    def __init__(self):
        logger.info("StrategyDecisionEngine initialized")
    
    def decide_strategy(self, bias_result, features, snapshot=None) -> StrategyDecision:
        """Smart money strategy decision based on institutional positioning"""
        print("[DEBUG] decide_strategy called with features:", list(features.keys()))
        try:
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
            distance_call = None
            distance_put = None
            call_pressure = None
            put_pressure = None
            
            if call_wall and put_wall:
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
            else:
                wall_signal = 0
            
            # STEP 4: UPGRADE GEX LOGIC (DYNAMIC)
            gex_strength = min(abs(net_gex) / 100000, 1.0)
            
            if net_gex > 0:
                regime_factor = 1 - (0.5 * gex_strength)   # mean reversion
            else:
                regime_factor = 1 + (0.5 * gex_strength)   # trending
            
            # STEP 5: FINAL SCORE
            raw_score = oi_signal + wall_signal
            adjusted_score = raw_score * regime_factor
            
            # STEP 6: DECISION LOGIC
            if adjusted_score >= 1:
                action = "BUY"
            elif adjusted_score <= -1:
                action = "SELL"
            else:
                action = "NO_TRADE"
            
            # STEP 7: REAL CONFIDENCE
            max_score = 2 * 1.5
            confidence = min(abs(adjusted_score) / max_score, 1.0)
            
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
            
            # STEP 9: DEBUG OUTPUT
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
            
            return StrategyDecision(
                strategy=action,
                regime='RANGING',
                bias_confidence=confidence,
                execution_probability=0.5,
                reasoning=reasoning
            )
            
        except Exception as e:
            print(f"Exception: {e}")
            import traceback
            traceback.print_exc()
            return StrategyDecision(
                strategy='NO_TRADE',
                regime='RANGING',
                bias_confidence=0.0,
                execution_probability=0.0,
                reasoning=['Error in strategy decision']
            )

class BiasResult:
    def __init__(self):
        self.bias = 'NEUTRAL'
        self.confidence = 0.5

# Test the logic
engine = StrategyDecisionEngine()

# Test Case 1: Strong call pressure → should SELL
print("=== TEST 1: STRONG CALL PRESSURE ===")
features1 = {
    'spot': 20000,
    'call_oi_distribution': {'20000': 1000000},
    'put_oi_distribution': {'20000': 500000},
    'oi_change_calls': 50000,
    'oi_change_puts': 10000,
    'call_wall_strike': 20100,
    'put_wall_strike': 19900,
    'gex_profile': {'net_gamma': -200000}
}

result1 = engine.decide_strategy(BiasResult(), features1)
print(f"Expected: SELL, Got: {result1.strategy}")
print(f"Confidence: {result1.bias_confidence:.3f}")
print(f"Reasoning: {result1.reasoning}")
print()

# Test Case 2: Strong put pressure → should BUY
print("=== TEST 2: STRONG PUT PRESSURE ===")
features2 = {
    'spot': 20000,
    'call_oi_distribution': {'20000': 500000},
    'put_oi_distribution': {'20000': 1000000},
    'oi_change_calls': 10000,
    'oi_change_puts': 50000,
    'call_wall_strike': 20100,
    'put_wall_strike': 19900,
    'gex_profile': {'net_gamma': -200000}
}

result2 = engine.decide_strategy(BiasResult(), features2)
print(f"Expected: BUY, Got: {result2.strategy}")
print(f"Confidence: {result2.bias_confidence:.3f}")
print(f"Reasoning: {result2.reasoning}")
print()

# Test Case 3: Balanced → should NO_TRADE
print("=== TEST 3: BALANCED MARKET ===")
features3 = {
    'spot': 20000,
    'call_oi_distribution': {'20000': 500000},
    'put_oi_distribution': {'20000': 500000},
    'oi_change_calls': 25000,
    'oi_change_puts': 25000,
    'call_wall_strike': 20100,
    'put_wall_strike': 19900,
    'gex_profile': {'net_gamma': 200000}
}

result3 = engine.decide_strategy(BiasResult(), features3)
print(f"Expected: NO_TRADE, Got: {result3.strategy}")
print(f"Confidence: {result3.bias_confidence:.3f}")
print(f"Reasoning: {result3.reasoning}")
print()

# Test Case 4: Deterministic check - same input twice
print("=== TEST 4: DETERMINISTIC CHECK ===")
result4a = engine.decide_strategy(BiasResult(), features1)
result4b = engine.decide_strategy(BiasResult(), features1)

print(f"First run: {result4a.strategy}, confidence: {result4a.bias_confidence:.3f}")
print(f"Second run: {result4b.strategy}, confidence: {result4b.bias_confidence:.3f}")
print(f"Deterministic: {result4a.strategy == result4b.strategy and abs(result4a.bias_confidence - result4b.bias_confidence) < 0.001}")
