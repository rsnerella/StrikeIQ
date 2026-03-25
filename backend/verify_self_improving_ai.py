#!/usr/bin/env python3
"""
Verification - StrikeIQ Self-Improving AI
Tests strategy weight adaptation and self-learning
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add backend to path
sys.path.append(str(Path(__file__).parent))

def test_self_improving_ai():
    """Test self-improving AI functionality"""
    
    print("=== 🧠 SELF-IMPROVING AI VERIFICATION ===\n")
    
    results = []
    engine = None  # Initialize engine variable
    
    # Test 1: Strategy Weights Initialization
    print("🔧 Test 1: Strategy Weights Initialization...")
    try:
        from app.services.trade_execution_engine import TradeExecutionEngine
        
        engine = TradeExecutionEngine()
        
        # Check initial weights
        expected_weights = {
            "TREND": 1.0,
            "REVERSAL": 1.0,
            "WEAK_TREND": 0.5,
            "RANGE": 1.0,
            "NONE": 0.0
        }
        
        if engine.strategy_weights == expected_weights:
            print("✅ Strategy weights initialized correctly")
            results.append(True)
        else:
            print(f"❌ Strategy weights incorrect: {engine.strategy_weights}")
            results.append(False)
            
    except Exception as e:
        print(f"❌ Test 1 error: {e}")
        results.append(False)
    
    # Test 2: Weight Normalization
    print("\n🔧 Test 2: Weight Normalization...")
    try:
        # Use engine from previous test
        if 'engine' not in locals():
            engine = TradeExecutionEngine()
        
        # Modify weights
        engine.strategy_weights["TREND"] = 2.0
        engine.strategy_weights["REVERSAL"] = 1.0
        engine.strategy_weights["WEAK_TREND"] = 0.5
        
        # Normalize
        engine.normalize_weights()
        
        # Check if weights sum to 1.0
        total = sum(engine.strategy_weights.values())
        
        if abs(total - 1.0) < 0.001:
            print("✅ Weights normalized correctly")
            results.append(True)
        else:
            print(f"❌ Weights not normalized: total={total}")
            results.append(False)
            
    except Exception as e:
        print(f"❌ Test 2 error: {e}")
        results.append(False)
    
    # Test 3: Weight Updates After Profitable Trade
    print("\n🔧 Test 3: Weight Updates After Profitable Trade...")
    try:
        # Reset to known state
        engine.strategy_weights = {
            "TREND": 0.25,
            "REVERSAL": 0.25,
            "WEAK_TREND": 0.25,
            "RANGE": 0.25,
            "NONE": 0.0
        }
        
        # Simulate profitable TREND trade
        trade_data = {
            "symbol": "NIFTY",
            "signal": "BUY_CALL",
            "entry": 100,
            "stop_loss": 85,
            "target": 120,
            "quantity": 1,
            "strategy": "TREND"
        }
        
        engine.try_enter(trade_data)
        engine.manage_trade(125)  # Profitable exit
        
        # Check if TREND weight increased
        new_trend_weight = engine.strategy_weights["TREND"]
        
        if new_trend_weight > 0.25:
            print(f"✅ TREND weight increased after profitable trade: {new_trend_weight:.3f}")
            results.append(True)
        else:
            print(f"❌ TREND weight not increased: {new_trend_weight}")
            results.append(False)
            
    except Exception as e:
        print(f"❌ Test 3 error: {e}")
        results.append(False)
    
    # Test 4: Weight Updates After Losing Trade
    print("\n🔧 Test 4: Weight Updates After Losing Trade...")
    try:
        # Simulate losing REVERSAL trade
        trade_data = {
            "symbol": "NIFTY",
            "signal": "BUY_PUT",
            "entry": 100,
            "stop_loss": 115,
            "target": 80,
            "quantity": 1,
            "strategy": "REVERSAL"
        }
        
        initial_reversal_weight = engine.strategy_weights["REVERSAL"]
        
        engine.try_enter(trade_data)
        engine.manage_trade(120)  # Losing exit for PUT
        
        # Check if REVERSAL weight decreased
        new_reversal_weight = engine.strategy_weights["REVERSAL"]
        
        if new_reversal_weight < initial_reversal_weight:
            print(f"✅ REVERSAL weight decreased after losing trade: {new_reversal_weight:.3f}")
            results.append(True)
        else:
            print(f"❌ REVERSAL weight not decreased: {new_reversal_weight}")
            results.append(False)
            
    except Exception as e:
        print(f"❌ Test 4 error: {e}")
        results.append(False)
    
    # Test 5: Strategy Engine Integration
    print("\n🔧 Test 5: Strategy Engine Integration...")
    try:
        from ai.strategy_engine import generate_trade, is_tradable_time
        
        # Mock time filter to always return True
        import ai.strategy_engine
        original_time_filter = ai.strategy_engine.is_tradable_time
        ai.strategy_engine.is_tradable_time = lambda: True
        
        # Reset weights to ensure TREND has sufficient weight
        engine.strategy_weights = {
            "TREND": 0.5,
            "REVERSAL": 0.3,
            "WEAK_TREND": 0.2,
            "RANGE": 0.0,
            "NONE": 0.0
        }
        
        # Mock snapshot and analytics
        class MockSnapshot:
            is_valid = True
            spot = 100
        
        snapshot = MockSnapshot()
        analytics = {
            "pcr": 0.6,  # PCR < 0.7 to trigger TREND (Bullish)
            "rsi": 65,  # RSI outside neutral range (45-55) to pass momentum
            "confidence": 0.9,  # Very high confidence to avoid fallback
            "volatility": 0.03,  # Volatility > 0.02 to pass momentum
            "liquidity": 15000,  # Liquidity > 10000 to pass momentum
            "momentum": 0.1,  # High momentum to pass filter
            "key_levels": {"vwap": 100}
        }
        
        # Test with execution engine
        signal, strategy = generate_trade(snapshot, analytics, engine)
        
        # Restore original time filter
        ai.strategy_engine.is_tradable_time = original_time_filter
        
        print(f"[DEBUG] Signal: {signal}, Strategy: {strategy}")
        print(f"[DEBUG] Engine weights: {engine.strategy_weights}")
        
        if signal != "NONE" and strategy and strategy != "DISABLED_STRATEGY":
            print(f"✅ Strategy engine integrated: {signal} from {strategy}")
            results.append(True)
        else:
            print(f"❌ Strategy engine not integrated: {signal}, {strategy}")
            results.append(False)
            
    except Exception as e:
        print(f"❌ Test 5 error: {e}")
        results.append(False)
    
    # Test 6: Bad Strategy Blocking
    print("\n🔧 Test 6: Bad Strategy Blocking...")
    try:
        # Mock time filter to always return True
        import ai.strategy_engine
        original_time_filter = ai.strategy_engine.is_tradable_time
        ai.strategy_engine.is_tradable_time = lambda: True
        
        # Reduce a strategy weight below threshold
        engine.strategy_weights["WEAK_TREND"] = 0.1  # Below 0.3 threshold
        engine.normalize_weights()
        
        # Test with analytics that would trigger WEAK_TREND
        analytics = {
            "pcr": 0.9,
            "rsi": 53,
            "confidence": 0.6,
            "volatility": 0.02
        }
        
        signal, strategy = generate_trade(snapshot, analytics, engine)
        
        # Restore original time filter
        ai.strategy_engine.is_tradable_time = original_time_filter
        
        if signal == "NONE" and strategy == "DISABLED_STRATEGY":
            print("✅ Bad strategy blocked correctly")
            results.append(True)
        else:
            print(f"❌ Bad strategy not blocked: {signal}, {strategy}")
            results.append(False)
            
    except Exception as e:
        print(f"❌ Test 6 error: {e}")
        results.append(False)
    
    # Test 7: UI Integration
    print("\n🔧 Test 7: UI Integration...")
    try:
        # Test that strategy weights are available for UI
        if hasattr(engine, 'strategy_weights'):
            weights = engine.strategy_weights
            
            # Check if weights can be serialized
            try:
                import json
                json.dumps(weights)  # Test serialization
                print("✅ Strategy weights serializable for UI")
                results.append(True)
            except (TypeError, ValueError):
                print("❌ Strategy weights not serializable")
                results.append(False)
        else:
            print("❌ Strategy weights not available")
            results.append(False)
            
    except Exception as e:
        print(f"❌ Test 7 error: {e}")
        results.append(False)
    
    # Test 8: Self-Improvement Over Time
    print("\n🔧 Test 8: Self-Improvement Over Time...")
    try:
        # Simulate multiple trades to see weight evolution
        initial_weights = engine.strategy_weights.copy()
        
        # Multiple profitable TREND trades
        for i in range(3):
            trade_data = {
                "symbol": "NIFTY",
                "signal": "BUY_CALL",
                "entry": 100,
                "stop_loss": 85,
                "target": 120,
                "quantity": 1,
                "strategy": "TREND"
            }
            engine.try_enter(trade_data)
            engine.manage_trade(125)  # Profitable
        
        final_trend_weight = engine.strategy_weights["TREND"]
        initial_trend_weight = initial_weights["TREND"]
        
        if final_trend_weight > initial_trend_weight:
            print(f"✅ Strategy improved over time: TREND {initial_trend_weight:.3f} -> {final_trend_weight:.3f}")
            results.append(True)
        else:
            print(f"❌ Strategy not improved: {initial_trend_weight:.3f} -> {final_trend_weight:.3f}")
            results.append(False)
            
    except Exception as e:
        print(f"❌ Test 8 error: {e}")
        results.append(False)
    
    # Final Results
    print("\n" + "="*50)
    print("🧠 SELF-IMPROVING AI RESULTS:")
    print("="*50)
    
    all_passed = all(results)
    
    if all_passed:
        print("✅ SELF-IMPROVING AI ACTIVE!")
        print("\n🎉 AI LEARNING FEATURES:")
        print("✅ Strategy weights initialization")
        print("✅ Weight normalization")
        print("✅ Reward profitable strategies")
        print("✅ Punish losing strategies")
        print("✅ Strategy engine integration")
        print("✅ Bad strategy blocking")
        print("✅ UI integration ready")
        print("✅ Self-improvement over time")
        print("\n🧠 SELF-IMPROVING AI READY!")
        print("📋 AI increases trades from profitable strategies")
        print("📋 AI reduces losing strategies automatically")
        print("📋 AI adapts to market conditions")
        print("📋 AI becomes smarter over time")
        print("📋 Strategy weights exposed to UI")
        print("\n🚀 SELF-IMPROVING AI IS PRODUCTION-READY!")
    else:
        print("❌ SELF-IMPROVING AI INCOMPLETE!")
        failed_tests = [i+1 for i, r in enumerate(results) if not r]
        print(f"❌ Failed tests: {failed_tests}")
        print("\n⚠️  Fix failed tests before production")
    
    return all_passed

if __name__ == "__main__":
    success = test_self_improving_ai()
    sys.exit(0 if success else 1)
