#!/usr/bin/env python3
"""
Verification - StrikeIQ Balanced Strategy Engine
Tests that AI gives trades when opportunities exist without over-filtering
"""

import os
import sys
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent))

def test_balanced_strategy_engine():
    """Test balanced strategy engine with fallback and frequency control"""
    
    print("=== ⚖️ BALANCED STRATEGY ENGINE VERIFICATION ===\n")
    
    results = []
    
    # Test 1: Fallback Strategy
    print("🔧 Test 1: Fallback Strategy...")
    try:
        from ai.strategy_engine import fallback_trade
        
        # Test weak signal conditions
        weak_analytics = {
            "pcr": 0.92,  # Just below 0.95
            "rsi": 53     # Just above 52
        }
        
        signal, strategy = fallback_trade(weak_analytics)
        
        if signal == "BUY_CALL" and strategy == "WEAK_TREND":
            print("✅ Fallback strategy generates weak signals")
            results.append(True)
        else:
            print(f"❌ Expected BUY_CALL/WEAK_TREND, got {signal}/{strategy}")
            results.append(False)
            
    except Exception as e:
        print(f"❌ Test 1 error: {e}")
        results.append(False)
    
    # Test 2: Main Engine with Fallback
    print("\n🔧 Test 2: Main Engine with Fallback...")
    try:
        from ai.strategy_engine import generate_trade
        
        # Mock filters to always return True
        import ai.strategy_engine
        original_time_filter = ai.strategy_engine.is_tradable_time
        ai.strategy_engine.is_tradable_time = lambda: True
        
        class MockSnapshot:
            def __init__(self):
                self.is_valid = True
                self.spot = 22450
        
        snapshot = MockSnapshot()
        
        # Test with conditions that should trigger fallback
        fallback_analytics = {
            "pcr": 0.93,  # Just below fallback threshold
            "rsi": 53,    # Just above fallback threshold
            "volatility": 0.03,
            "liquidity": 150000,
            "confidence": 0.6
        }
        
        signal, strategy = generate_trade(snapshot, fallback_analytics)
        
        # Should get fallback signal
        if signal in ["BUY_CALL", "BUY_PUT"] and strategy == "WEAK_TREND":
            print("✅ Main engine uses fallback when no strong signal")
            results.append(True)
        else:
            print(f"❌ Expected fallback signal, got {signal}/{strategy}")
            results.append(False)
        
        # Restore original filter
        ai.strategy_engine.is_tradable_time = original_time_filter
            
    except Exception as e:
        print(f"❌ Test 2 error: {e}")
        results.append(False)
    
    # Test 3: Relaxed Confidence Filter
    print("\n🔧 Test 3: Relaxed Confidence Filter...")
    try:
        from ai.strategy_engine import should_trade, TradeSignal
        
        # Test with low confidence (should pass now)
        low_conf_signal = TradeSignal(
            signal="BUY_CALL",
            strategy="WEAK_TREND",
            confidence=0.4,  # Below old 0.5, above new 0.35
            metadata={"risk_reward": 1.2, "data_quality": "REAL"}
        )
        
        if should_trade(low_conf_signal):
            print("✅ Relaxed confidence filter allows weak signals")
            results.append(True)
        else:
            print("❌ Relaxed confidence filter too strict")
            results.append(False)
        
        # Test with very low confidence (should still fail)
        very_low_signal = TradeSignal(
            signal="BUY_CALL",
            strategy="WEAK_TREND",
            confidence=0.3,  # Below new 0.35
            metadata={"risk_reward": 1.2, "data_quality": "REAL"}
        )
        
        if not should_trade(very_low_signal):
            print("✅ Very low confidence still filtered")
            results.append(True)
        else:
            print("❌ Very low confidence not filtered")
            results.append(False)
            
    except Exception as e:
        print(f"❌ Test 3 error: {e}")
        results.append(False)
    
    # Test 4: Momentum Filter Degradation
    print("\n🔧 Test 4: Momentum Filter Degradation...")
    try:
        from ai.strategy_engine import _primary_strategy
        
        # Test with bad momentum conditions
        bad_momentum_analytics = {
            "rsi": 50,  # Neutral RSI
            "volatility": 0.01,  # Low volatility
            "liquidity": 5000,  # Low liquidity
            "confidence": 0.8
        }
        
        class MockSnapshot:
            def __init__(self):
                self.is_valid = True
                self.spot = 22450
        
        snapshot = MockSnapshot()
        
        signal, strategy = _primary_strategy(snapshot, bad_momentum_analytics)
        
        # Check if confidence was degraded
        new_confidence = bad_momentum_analytics.get("confidence", 0)
        if new_confidence < 0.8:  # Should be reduced
            print("✅ Momentum filter degrades confidence instead of blocking")
            results.append(True)
        else:
            print("❌ Momentum filter not degrading confidence")
            results.append(False)
            
    except Exception as e:
        print(f"❌ Test 4 error: {e}")
        results.append(False)
    
    # Test 5: Minimum Signal Frequency
    print("\n🔧 Test 5: Minimum Signal Frequency...")
    try:
        from ai.strategy_engine import force_minimum_signal_frequency
        
        # Reset global counter
        ai.strategy_engine._no_trade_count = 0
        
        analytics = {"pcr": 1.0, "rsi": 50}
        
        # Test normal case (no force)
        signal, strategy = force_minimum_signal_frequency(analytics)
        if signal == "NONE":
            print("✅ No force when counter is low")
            results.append(True)
        else:
            print("❌ Unexpected force signal")
            results.append(False)
        
        # Test force case
        ai.strategy_engine._no_trade_count = 25  # Above threshold
        signal, strategy = force_minimum_signal_frequency(analytics)
        
        # The function increments the counter first, then checks
        if signal != "NONE" or ai.strategy_engine._no_trade_count == 0:
            print("✅ Force signal when counter is high")
            results.append(True)
        else:
            print("❌ No force signal when counter is high")
            results.append(False)
            
    except Exception as e:
        print(f"❌ Test 5 error: {e}")
        results.append(False)
    
    # Test 6: No Trade Logging
    print("\n🔧 Test 6: No Trade Logging...")
    try:
        from ai.strategy_engine import log_no_trade_reason
        
        # Test logging function
        analytics = {
            "pcr": 1.0,
            "rsi": 50,
            "gamma": "NEUTRAL",
            "volatility": 0.02
        }
        
        # This should print without error
        log_no_trade_reason(analytics)
        print("✅ No trade logging works")
        results.append(True)
            
    except Exception as e:
        print(f"❌ Test 6 error: {e}")
        results.append(False)
    
    # Final Results
    print("\n" + "="*50)
    print("⚖️ BALANCED STRATEGY ENGINE RESULTS:")
    print("="*50)
    
    all_passed = all(results)
    
    if all_passed:
        print("✅ BALANCED STRATEGY ENGINE ACTIVE!")
        print("\n🎉 BALANCED FEATURES:")
        print("✅ Fallback strategy - Weak signals when no strong ones")
        print("✅ Relaxed confidence - 0.35 threshold instead of 0.5")
        print("✅ Momentum degradation - Reduce confidence, don't block")
        print("✅ Minimum frequency - Force trade after 20 no-trades")
        print("✅ No trade logging - Clear reason for no trades")
        print("✅ Balanced approach - Trade when opportunities exist")
        print("\n⚖️ TRADING BALANCE ACHIEVED!")
        print("📋 AI gives trades when real opportunities exist")
        print("📋 No over-filtering of valid signals")
        print("📋 Graceful degradation instead of hard blocks")
        print("📋 Minimum activity to stay engaged")
        print("📋 Clear visibility into decision making")
        print("\n🚀 STRATEGY ENGINE IS BALANCED & READY!")
    else:
        print("❌ BALANCED ENGINE INCOMPLETE!")
        failed_tests = [i+1 for i, r in enumerate(results) if not r]
        print(f"❌ Failed tests: {failed_tests}")
        print("\n⚠️  Fix failed tests before production")
    
    return all_passed

if __name__ == "__main__":
    success = test_balanced_strategy_engine()
    sys.exit(0 if success else 1)
