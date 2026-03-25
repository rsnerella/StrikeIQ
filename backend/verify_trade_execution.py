#!/usr/bin/env python3
"""
Verification - StrikeIQ Trade Execution Engine
Tests real trade execution with entry, exit, trailing stop loss, and position management
"""

import os
import sys
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent))

def test_trade_execution_engine():
    """Test trade execution engine functionality"""
    
    print("=== 🏭 TRADE EXECUTION ENGINE VERIFICATION ===\n")
    
    results = []
    
    # Test 1: Trade Entry
    print("🔧 Test 1: Trade Entry...")
    try:
        from app.services.trade_execution_engine import TradeExecutionEngine
        
        engine = TradeExecutionEngine()
        
        # Test valid trade entry
        signal_data = {
            "symbol": "NIFTY",
            "signal": "BUY_CALL",
            "entry": 120,
            "stop_loss": 85,
            "target": 180,
            "quantity": 1
        }
        
        trade = engine.try_enter(signal_data)
        
        if trade and trade.signal == "BUY_CALL" and trade.entry == 120:
            print("✅ Trade entered successfully")
            results.append(True)
        else:
            print("❌ Trade entry failed")
            results.append(False)
        
        # Test duplicate entry (should be blocked)
        duplicate_trade = engine.try_enter(signal_data)
        if duplicate_trade is None:
            print("✅ Duplicate entry blocked")
            results.append(True)
        else:
            print("❌ Duplicate entry not blocked")
            results.append(False)
            
    except Exception as e:
        print(f"❌ Test 1 error: {e}")
        results.append(False)
    
    # Test 2: Trade Management - Target Hit
    print("\n🔧 Test 2: Trade Management - Target Hit...")
    try:
        # Use engine from previous test
        if 'engine' not in locals():
            engine = TradeExecutionEngine()
            signal_data = {
                "symbol": "NIFTY",
                "signal": "BUY_CALL",
                "entry": 120,
                "stop_loss": 85,
                "target": 180,
                "quantity": 1
            }
            engine.try_enter(signal_data)
        
        # Test target hit
        status = engine.manage_trade(185)  # Above target
        
        if status == "TARGET_HIT":
            print("✅ Target hit detected")
            results.append(True)
        else:
            print(f"❌ Expected TARGET_HIT, got {status}")
            results.append(False)
            
    except Exception as e:
        print(f"❌ Test 2 error: {e}")
        results.append(False)
    
    # Test 3: Trade Management - Stop Loss
    print("\n🔧 Test 3: Trade Management - Stop Loss...")
    try:
        engine = TradeExecutionEngine()
        
        # Enter new trade
        signal_data = {
            "symbol": "NIFTY",
            "signal": "BUY_CALL",
            "entry": 120,
            "stop_loss": 85,
            "target": 180,
            "quantity": 1
        }
        engine.try_enter(signal_data)
        
        # Test stop loss hit
        status = engine.manage_trade(80)  # Below stop loss
        
        if status == "STOP_LOSS":
            print("✅ Stop loss detected")
            results.append(True)
        else:
            print(f"❌ Expected STOP_LOSS, got {status}")
            results.append(False)
            
    except Exception as e:
        print(f"❌ Test 3 error: {e}")
        results.append(False)
    
    # Test 4: Trade Management - Trailing Stop Loss
    print("\n🔧 Test 4: Trade Management - Trailing Stop Loss...")
    try:
        engine = TradeExecutionEngine()
        
        # Enter new trade
        signal_data = {
            "symbol": "NIFTY",
            "signal": "BUY_CALL",
            "entry": 120,
            "stop_loss": 85,
            "target": 180,
            "quantity": 1
        }
        engine.try_enter(signal_data)
        
        # Move price up to trigger trailing SL (20% profit)
        status = engine.manage_trade(145)  # 20% profit
        
        if status == "HOLD":
            print("✅ Trade held during profit")
        else:
            print(f"❌ Expected HOLD, got {status}")
            results.append(False)
        
        # Check trailing SL was set
        if engine.active_trade and engine.active_trade.trailing_sl:
            print("✅ Trailing stop loss set")
            results.append(True)
        else:
            print("❌ Trailing stop loss not set")
            results.append(False)
        
        # Test trailing SL hit
        status = engine.manage_trade(125)  # Below trailing SL (145 * 0.9 = 130.5)
        
        if status == "TRAILING_SL":
            print("✅ Trailing stop loss triggered")
            results.append(True)
        else:
            print(f"❌ Expected TRAILING_SL, got {status}")
            results.append(False)
            
    except Exception as e:
        print(f"❌ Test 4 error: {e}")
        results.append(False)
    
    # Test 5: PUT Option Logic
    print("\n🔧 Test 5: PUT Option Logic...")
    try:
        engine = TradeExecutionEngine()
        
        # Enter PUT trade
        signal_data = {
            "symbol": "NIFTY",
            "signal": "BUY_PUT",
            "entry": 120,
            "stop_loss": 135,
            "target": 85,
            "quantity": 1
        }
        trade = engine.try_enter(signal_data)
        
        if trade and trade.signal == "BUY_PUT":
            print("✅ PUT trade entered")
            
            # Test PUT target hit (price goes down)
            status = engine.manage_trade(80)  # Below target
            if status == "TARGET_HIT":
                print("✅ PUT target hit correctly")
                results.append(True)
            else:
                print(f"❌ Expected PUT TARGET_HIT, got {status}")
                results.append(False)
        else:
            print("❌ PUT trade entry failed")
            results.append(False)
            
    except Exception as e:
        print(f"❌ Test 5 error: {e}")
        results.append(False)
    
    # Test 6: No Force Trade
    print("\n🔧 Test 6: No Force Trade...")
    try:
        engine = TradeExecutionEngine()
        
        # Test NONE signal (should be blocked)
        none_signal = {
            "symbol": "NIFTY",
            "signal": "NONE",
            "entry": 120,
            "stop_loss": 85,
            "target": 180,
            "quantity": 1
        }
        
        trade = engine.try_enter(none_signal)
        
        if trade is None:
            print("✅ NONE signal blocked")
            results.append(True)
        else:
            print("❌ NONE signal not blocked")
            results.append(False)
            
    except Exception as e:
        print(f"❌ Test 6 error: {e}")
        results.append(False)
    
    # Test 7: Trade Status and Statistics
    print("\n🔧 Test 7: Trade Status and Statistics...")
    try:
        engine = TradeExecutionEngine()
        
        # Enter and close a trade to generate statistics
        signal_data = {
            "symbol": "NIFTY",
            "signal": "BUY_CALL",
            "entry": 120,
            "stop_loss": 85,
            "target": 180,
            "quantity": 1
        }
        engine.try_enter(signal_data)
        engine.manage_trade(185)  # Close at target
        
        # Get status
        status = engine.get_trade_status()
        
        if status["total_trades"] == 1 and status["winning_trades"] == 1:
            print("✅ Trade statistics tracked correctly")
            results.append(True)
        else:
            print(f"❌ Statistics incorrect: {status}")
            results.append(False)
            
    except Exception as e:
        print(f"❌ Test 7 error: {e}")
        results.append(False)
    
    # Final Results
    print("\n" + "="*50)
    print("🏭 TRADE EXECUTION ENGINE RESULTS:")
    print("="*50)
    
    all_passed = all(results)
    
    if all_passed:
        print("✅ TRADE EXECUTION ENGINE ACTIVE!")
        print("\n🎉 EXECUTION FEATURES:")
        print("✅ Trade entry with validation")
        print("✅ Duplicate entry prevention")
        print("✅ Target hit detection")
        print("✅ Stop loss detection")
        print("✅ Trailing stop loss with profit locking")
        print("✅ PUT option logic (inverse)")
        print("✅ No force trade (NONE signal blocked)")
        print("✅ Trade statistics tracking")
        print("\n🏭 REAL TRADE EXECUTION READY!")
        print("📋 AI detects opportunity")
        print("📋 AI enters trade")
        print("📋 AI manages trade")
        print("📋 AI exits trade")
        print("📋 AI locks profit")
        print("\n🚀 EXECUTION ENGINE IS PRODUCTION-READY!")
    else:
        print("❌ EXECUTION ENGINE INCOMPLETE!")
        failed_tests = [i+1 for i, r in enumerate(results) if not r]
        print(f"❌ Failed tests: {failed_tests}")
        print("\n⚠️  Fix failed tests before production")
    
    return all_passed

if __name__ == "__main__":
    success = test_trade_execution_engine()
    sys.exit(0 if success else 1)
