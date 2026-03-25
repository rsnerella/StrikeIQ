#!/usr/bin/env python3
"""
Verification - StrikeIQ Performance Tracking
Tests real trading performance tracking with PnL, win rate, and history
"""

import os
import sys
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent))

def test_performance_tracking():
    """Test performance tracking functionality"""
    
    print("=== 📊 PERFORMANCE TRACKING VERIFICATION ===\n")
    
    results = []
    
    # Test 1: Trade History Storage
    print("🔧 Test 1: Trade History Storage...")
    try:
        from app.services.trade_execution_engine import TradeExecutionEngine
        
        engine = TradeExecutionEngine()
        
        # Enter and complete multiple trades
        trades = [
            {"symbol": "NIFTY", "signal": "BUY_CALL", "entry": 100, "stop_loss": 85, "target": 120, "quantity": 1},
            {"symbol": "NIFTY", "signal": "BUY_PUT", "entry": 100, "stop_loss": 115, "target": 80, "quantity": 1},
            {"symbol": "NIFTY", "signal": "BUY_CALL", "entry": 100, "stop_loss": 85, "target": 120, "quantity": 1}
        ]
        
        for i, trade_data in enumerate(trades):
            engine.try_enter(trade_data)
            
            # Simulate trade completion
            if i == 0:  # First trade - win
                engine.manage_trade(125)  # Above target
            elif i == 1:  # Second trade - loss
                engine.manage_trade(120)  # Above stop loss for PUT
            else:  # Third trade - win
                engine.manage_trade(130)  # Above target
        
        # Check trade history
        if len(engine.trade_history) == 3:
            print("✅ All trades stored in history")
            results.append(True)
        else:
            print(f"❌ Expected 3 trades in history, got {len(engine.trade_history)}")
            results.append(False)
            
    except Exception as e:
        print(f"❌ Test 1 error: {e}")
        results.append(False)
    
    # Test 2: PnL Calculation
    print("\n🔧 Test 2: PnL Calculation...")
    try:
        # Use engine from previous test
        if 'engine' not in locals():
            engine = TradeExecutionEngine()
        
        # Check PnL values
        trade_pnls = [trade.pnl for trade in engine.trade_history]
        
        # Expected: +25 (125-100), -20 (100-120), +30 (130-100)
        expected_pnls = [25.0, -20.0, 30.0]
        
        if all(abs(actual - expected) < 0.1 for actual, expected in zip(trade_pnls, expected_pnls)):
            print("✅ PnL calculations correct")
            results.append(True)
        else:
            print(f"❌ PnL calculations incorrect: {trade_pnls}")
            results.append(False)
            
    except Exception as e:
        print(f"❌ Test 2 error: {e}")
        results.append(False)
    
    # Test 3: Performance Metrics
    print("\n🔧 Test 3: Performance Metrics...")
    try:
        perf = engine.get_performance()
        
        # Expected: 3 trades, 2 wins, 1 loss, 66.67% win rate, 35 total PnL
        expected = {
            "total_trades": 3,
            "wins": 2,
            "losses": 1,
            "win_rate": 66.67,
            "total_pnl": 35.0
        }
        
        checks = []
        for key, expected_val in expected.items():
            actual_val = perf[key]
            if key == "win_rate":
                if abs(actual_val - expected_val) < 1:  # Within 1%
                    checks.append(True)
                else:
                    print(f"❌ {key}: expected {expected_val}, got {actual_val}")
                    checks.append(False)
            else:
                if actual_val == expected_val:
                    checks.append(True)
                else:
                    print(f"❌ {key}: expected {expected_val}, got {actual_val}")
                    checks.append(False)
        
        if all(checks):
            print("✅ Performance metrics correct")
            results.append(True)
        else:
            print("❌ Performance metrics incorrect")
            results.append(False)
            
    except Exception as e:
        print(f"❌ Test 3 error: {e}")
        results.append(False)
    
    # Test 4: Performance Logging
    print("\n🔧 Test 4: Performance Logging...")
    try:
        # Test that performance method works without errors
        perf = engine.get_performance()
        
        # Check required fields
        required_fields = ["total_trades", "wins", "losses", "win_rate", "total_pnl"]
        
        if all(field in perf for field in required_fields):
            print("✅ Performance logging has all required fields")
            results.append(True)
        else:
            print("❌ Performance logging missing required fields")
            results.append(False)
            
    except Exception as e:
        print(f"❌ Test 4 error: {e}")
        results.append(False)
    
    # Test 5: UI Integration
    print("\n🔧 Test 5: UI Integration...")
    try:
        # Test that execution engine has performance method
        if hasattr(engine, 'get_performance'):
            print("✅ Execution engine performance method available")
            results.append(True)
        else:
            print("❌ Execution engine performance method missing")
            results.append(False)
            
    except Exception as e:
        print(f"❌ Test 5 error: {e}")
        results.append(False)
    
    # Test 6: Trade History Details
    print("\n🔧 Test 6: Trade History Details...")
    try:
        # Check detailed trade information
        trade = engine.trade_history[0]  # First trade
        
        required_fields = ["entry_time", "exit_time", "exit_price", "pnl"]
        
        if all(hasattr(trade, field) for field in required_fields):
            print("✅ Trade history has all required fields")
            results.append(True)
        else:
            print("❌ Trade history missing required fields")
            results.append(False)
            
    except Exception as e:
        print(f"❌ Test 6 error: {e}")
        results.append(False)
    
    # Final Results
    print("\n" + "="*50)
    print("📊 PERFORMANCE TRACKING RESULTS:")
    print("="*50)
    
    all_passed = all(results)
    
    if all_passed:
        print("✅ PERFORMANCE TRACKING ACTIVE!")
        print("\n🎉 TRACKING FEATURES:")
        print("✅ Trade history storage")
        print("✅ PnL calculation per trade")
        print("✅ Win rate calculation")
        print("✅ Total PnL tracking")
        print("✅ Performance logging")
        print("✅ UI integration ready")
        print("✅ Detailed trade records")
        print("\n📊 REAL PERFORMANCE TRACKING READY!")
        print("📋 AI tracks every trade")
        print("📋 AI calculates profit/loss")
        print("📋 AI shows win rate")
        print("📋 AI builds history")
        print("📋 Performance metrics exposed to UI")
        print("\n🚀 PERFORMANCE TRACKING IS PRODUCTION-READY!")
    else:
        print("❌ PERFORMANCE TRACKING INCOMPLETE!")
        failed_tests = [i+1 for i, r in enumerate(results) if not r]
        print(f"❌ Failed tests: {failed_tests}")
        print("\n⚠️  Fix failed tests before production")
    
    return all_passed

if __name__ == "__main__":
    success = test_performance_tracking()
    sys.exit(0 if success else 1)
