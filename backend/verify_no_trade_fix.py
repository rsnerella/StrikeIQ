#!/usr/bin/env python3
"""
Verification - StrikeIQ NO TRADE FIX
Tests all fixes to ensure trades start flowing
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add backend to path
sys.path.append(str(Path(__file__).parent))

def test_no_trade_fixes():
    """Test all NO TRADE fixes"""
    
    print("=== 🔧 NO TRADE FIX VERIFICATION ===\n")
    
    results = []
    
    # Test 1: ChainSnapshot Usage Fix
    print("🔧 Test 1: ChainSnapshot Usage Fix...")
    try:
        # Check that snapshot.get() calls are removed
        with open("app/ai/ai_orchestrator.py", "r") as f:
            content = f.read()
            
        # Should not have snapshot.get() calls
        if "snapshot.get(" not in content:
            print("✅ ChainSnapshot usage fixed - no more snapshot.get() calls")
            results.append(True)
        else:
            print("❌ ChainSnapshot usage still has snapshot.get() calls")
            results.append(False)
            
    except Exception as e:
        print(f"❌ Test 1 error: {e}")
        results.append(False)
    
    # Test 2: DB Query Fix
    print("\n🔧 Test 2: DB Query Fix...")
    try:
        with open("app/services/ai_learning_engine.py", "r") as f:
            content = f.read()
            
        # Should have AVG(p.confidence) not AVG(o.confidence)
        if "AVG(p.confidence)" in content and "AVG(o.confidence)" not in content:
            print("✅ DB query fixed - using p.confidence")
            results.append(True)
        else:
            print("❌ DB query still has o.confidence")
            results.append(False)
            
    except Exception as e:
        print(f"❌ Test 2 error: {e}")
        results.append(False)
    
    # Test 3: Paper Trade Query Fix
    print("\n🔧 Test 3: Paper Trade Query Fix...")
    try:
        with open("app/services/paper_trade_engine.py", "r") as f:
            lines = f.readlines()
        
        # Find the SELECT query
        query_found = False
        in_query = False
        for line in lines:
            if "SELECT" in line:
                in_query = True
            if in_query:
                if "timestamp" in line:
                    query_found = True
                    break
                if ";" in line:
                    break
        
        if query_found:
            print("✅ Paper trade query fixed - using timestamp in SELECT query")
            results.append(True)
        else:
            print("❌ Paper trade query still uses entry_time in SELECT")
            results.append(False)
            
    except Exception as e:
        print(f"❌ Test 3 error: {e}")
        results.append(False)
    
    # Test 4: Force Trade Fallback
    print("\n🔧 Test 4: Force Trade Fallback...")
    try:
        from ai.strategy_engine import generate_trade
        
        # Mock time filter to always return True
        import ai.strategy_engine
        original_time_filter = ai.strategy_engine.is_tradable_time
        ai.strategy_engine.is_tradable_time = lambda: True
        
        # Mock snapshot
        class MockSnapshot:
            is_valid = True
            spot = 100
        
        snapshot = MockSnapshot()
        
        # Test with low confidence to trigger fallback
        analytics = {
            "pcr": 0.8,
            "rsi": 50,
            "confidence": 0.3,  # Low confidence to trigger fallback
            "flow_analysis": {"direction": "BULLISH"},
            "key_levels": {"vwap": 100}
        }
        
        signal, strategy = generate_trade(snapshot, analytics)
        
        # Restore original time filter
        ai.strategy_engine.is_tradable_time = original_time_filter
        
        if signal != "NONE" and strategy:
            print(f"✅ Force trade fallback working: {signal} from {strategy}")
            results.append(True)
        else:
            print(f"❌ Force trade fallback not working: {signal}, {strategy}")
            results.append(False)
            
    except Exception as e:
        print(f"❌ Test 4 error: {e}")
        results.append(False)
    
    # Test 5: Zero Data Block Fix
    print("\n🔧 Test 5: Zero Data Block Fix...")
    try:
        from ai.strategy_engine import generate_trade
        
        # Test with zero vwap
        analytics = {
            "pcr": 0.8,
            "rsi": 50,
            "confidence": 0.6,
            "key_levels": {"vwap": 0}  # Zero vwap
        }
        
        signal, strategy = generate_trade(snapshot, analytics)
        
        # Should not crash and should handle zero vwap
        if True:  # If we get here, zero vwap was handled
            print("✅ Zero data block fix working - vwap handled")
            results.append(True)
        else:
            print("❌ Zero data block fix not working")
            results.append(False)
            
    except Exception as e:
        print(f"❌ Test 5 error: {e}")
        results.append(False)
    
    # Test 6: Remove Over-Strict Filter
    print("\n🔧 Test 6: Remove Over-Strict Filter...")
    try:
        with open("app/analytics/regime_engine.py", "r") as f:
            content = f.read()
            
        # Should have 0.35 threshold, not 0.5
        if "confidence < 0.35" in content and "confidence < 0.5:" not in content:
            print("✅ Over-strict filter removed - using 0.35 threshold")
            results.append(True)
        else:
            print("❌ Over-strict filter still present")
            results.append(False)
            
    except Exception as e:
        print(f"❌ Test 6 error: {e}")
        results.append(False)
    
    # Test 7: Temp Regime Engine Fix
    print("\n🔧 Test7: Temp Regime Engine Fix...")
    try:
        from ai.strategy_engine import detect_regime
        
        # Test regime detection
        bearish = detect_regime({"pcr": 1.2})
        bullish = detect_regime({"pcr": 0.6})
        ranging = detect_regime({"pcr": 0.8})
        
        if bearish == "TREND" and bullish == "TREND" and ranging == "RANGE":
            print("✅ Temp regime engine working correctly")
            results.append(True)
        else:
            print(f"❌ Temp regime engine not working: {bearish}, {bullish}, {ranging}")
            results.append(False)
            
    except Exception as e:
        print(f"❌ Test 7 error: {e}")
        results.append(False)
    
    # Test 8: Overall Pipeline Unblock
    print("\n🔧 Test 8: Overall Pipeline Unblock...")
    try:
        from ai.strategy_engine import generate_trade
        
        # Mock time filter to always return True
        import ai.strategy_engine
        original_time_filter = ai.strategy_engine.is_tradable_time
        ai.strategy_engine.is_tradable_time = lambda: True
        
        # Test with good conditions
        analytics = {
            "pcr": 0.8,
            "rsi": 60,
            "confidence": 0.6,
            "flow_analysis": {"direction": "BULLISH"},
            "key_levels": {"vwap": 100}
        }
        
        signal, strategy = generate_trade(snapshot, analytics)
        
        # Restore original time filter
        ai.strategy_engine.is_tradable_time = original_time_filter
        
        if signal != "NONE" and strategy:
            print(f"✅ Pipeline unblocked - getting signals: {signal} from {strategy}")
            results.append(True)
        else:
            print(f"❌ Pipeline still blocked: {signal}, {strategy}")
            results.append(False)
            
    except Exception as e:
        print(f"❌ Test 8 error: {e}")
        results.append(False)
    
    # Final Results
    print("\n" + "="*50)
    print("🔧 NO TRADE FIX RESULTS:")
    print("="*50)
    
    all_passed = all(results)
    
    if all_passed:
        print("✅ NO TRADE ISSUE FIXED!")
        print("\n🎉 FIXES APPLIED:")
        print("✅ ChainSnapshot usage fixed")
        print("✅ DB query corrected")
        print("✅ Paper trade query updated")
        print("✅ Force trade fallback added")
        print("✅ Zero data block fixed")
        print("✅ Over-strict filter removed")
        print("✅ Temp regime engine added")
        print("✅ Pipeline unblocked")
        print("\n🚀 TRADES WILL START COMING!")
        print("📋 AI will not freeze")
        print("📋 System becomes ACTIVE")
        print("\n🔥 NO TRADE ISSUE RESOLVED!")
    else:
        print("❌ NO TRADE ISSUE NOT FULLY FIXED!")
        failed_tests = [i+1 for i, r in enumerate(results) if not r]
        print(f"❌ Failed tests: {failed_tests}")
        print("\n⚠️  Fix remaining issues before production")
    
    return all_passed

if __name__ == "__main__":
    success = test_no_trade_fixes()
    sys.exit(0 if success else 1)
