#!/usr/bin/env python3

from backend.ai.strategy_decision_engine import StrategyDecisionEngine

class BiasResult:
    def __init__(self):
        self.bias = 'NEUTRAL'
        self.confidence = 0.5

def test_smart_money():
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

if __name__ == "__main__":
    test_smart_money()
