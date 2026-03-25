#!/usr/bin/env python3
"""
Verification - StrikeIQ Advanced Analytics
Tests equity curve, drawdown, and strategy performance tracking
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add backend to path
sys.path.append(str(Path(__file__).parent))

def test_advanced_analytics():
    """Test advanced analytics functionality"""
    
    print("=== 📈 ADVANCED ANALYTICS VERIFICATION ===\n")
    
    results = []
    engine = None  # Initialize engine variable
    
    # Test 1: Equity Curve
    print("🔧 Test 1: Equity Curve...")
    try:
        from app.services.trade_execution_engine import TradeExecutionEngine
        
        engine = TradeExecutionEngine()
        
        # Create trades with different PnL values
        trades = [
            {"symbol": "NIFTY", "signal": "BUY_CALL", "entry": 100, "stop_loss": 85, "target": 120, "quantity": 1, "strategy": "TREND"},
            {"symbol": "NIFTY", "signal": "BUY_PUT", "entry": 100, "stop_loss": 115, "target": 80, "quantity": 1, "strategy": "REVERSAL"},
            {"symbol": "NIFTY", "signal": "BUY_CALL", "entry": 100, "stop_loss": 85, "target": 120, "quantity": 1, "strategy": "TREND"},
            {"symbol": "NIFTY", "signal": "BUY_PUT", "entry": 100, "stop_loss": 115, "target": 80, "quantity": 1, "strategy": "WEAK_TREND"},
            {"symbol": "NIFTY", "signal": "BUY_CALL", "entry": 100, "stop_loss": 85, "target": 120, "quantity": 1, "strategy": "TREND"}
        ]
        
        # Simulate trade completion with different outcomes
        outcomes = [125, 120, 85, 75, 130]  # Win, Win, Loss, Win, Win
        
        for i, (trade_data, outcome) in enumerate(zip(trades, outcomes)):
            engine.try_enter(trade_data)
            engine.manage_trade(outcome)
        
        # Test equity curve
        equity_curve = engine.get_equity_curve()
        expected_curve = [25, 5, -10, 15, 45]  # Cumulative PnL (fixed based on actual calculations)
        
        if equity_curve == expected_curve:
            print("✅ Equity curve calculated correctly")
            results.append(True)
        else:
            print(f"❌ Equity curve incorrect: {equity_curve}")
            results.append(False)
            
    except Exception as e:
        print(f"❌ Test 1 error: {e}")
        results.append(False)
    
    # Test 2: Drawdown Calculation
    print("\n🔧 Test 2: Drawdown Calculation...")
    try:
        # Use engine from previous test
        if 'engine' not in locals():
            engine = TradeExecutionEngine()
        
        max_drawdown = engine.get_drawdown()
        
        # Expected: Peak was 25 (after 1st trade), then dropped to -10, so max drawdown = 35
        expected_dd = 35  # 25 - (-10) = 35
        
        if max_drawdown == expected_dd:
            print("✅ Maximum drawdown calculated correctly")
            results.append(True)
        else:
            print(f"❌ Drawdown incorrect: expected {expected_dd}, got {max_drawdown}")
            results.append(False)
            
    except Exception as e:
        print(f"❌ Test 2 error: {e}")
        results.append(False)
    
    # Test 3: Strategy Performance
    print("\n🔧 Test 3: Strategy Performance...")
    try:
        strategy_stats = engine.get_strategy_stats()
        print(f"[DEBUG] Strategy stats: {strategy_stats}")
        
        # Expected: TREND: 3 trades (2 wins, 1 loss), REVERSAL: 1 trade (0 wins, 1 loss), WEAK_TREND: 1 trade (1 win, 0 losses)
        expected_stats = {
            "TREND": {"trades": 3, "wins": 2, "losses": 1, "win_rate": 66.67},
            "REVERSAL": {"trades": 1, "wins": 0, "losses": 1, "win_rate": 0.0},
            "WEAK_TREND": {"trades": 1, "wins": 1, "losses": 0, "win_rate": 100.0}
        }
        
        checks = []
        for strategy, expected in expected_stats.items():
            if strategy in strategy_stats:
                actual = strategy_stats[strategy]
                print(f"[DEBUG] {strategy}: actual={actual}, expected={expected}")
                if (actual["trades"] == expected["trades"] and 
                    actual["wins"] == expected["wins"] and
                    actual["losses"] == expected["losses"] and
                    abs(actual["win_rate"] - expected["win_rate"]) < 1):
                    checks.append(True)
                else:
                    print(f"❌ {strategy} stats incorrect: {actual}")
                    checks.append(False)
            else:
                print(f"❌ Strategy {strategy} not found")
                checks.append(False)
        
        if all(checks):
            print("✅ Strategy performance calculated correctly")
            results.append(True)
        else:
            print("❌ Strategy performance incorrect")
            results.append(False)
            
    except Exception as e:
        print(f"❌ Test 3 error: {e}")
        results.append(False)
    
    # Test 4: Full Analytics
    print("\n🔧 Test 4: Full Analytics...")
    try:
        full_analytics = engine.get_full_analytics()
        
        required_fields = [
            "equity_curve", "max_drawdown", "strategy_stats", 
            "current_equity", "peak_equity", "total_trades"
        ]
        
        if all(field in full_analytics for field in required_fields):
            print("✅ Full analytics has all required fields")
            results.append(True)
        else:
            print("❌ Full analytics missing required fields")
            results.append(False)
            
        # Check specific values
        if (full_analytics["current_equity"] == 45 and 
            full_analytics["peak_equity"] == 45 and
            full_analytics["max_drawdown"] == 35):
            print("✅ Full analytics values correct")
            results.append(True)
        else:
            print(f"❌ Full analytics values incorrect: current={full_analytics['current_equity']}, peak={full_analytics['peak_equity']}, dd={full_analytics['max_drawdown']}")
            results.append(False)
            
    except Exception as e:
        print(f"❌ Test 4 error: {e}")
        results.append(False)
    
    # Test 5: UI Integration
    print("\n🔧 Test 5: UI Integration...")
    try:
        # Test that execution engine has full analytics method
        if hasattr(engine, 'get_full_analytics'):
            analytics = engine.get_full_analytics()
            
            # Check if analytics can be serialized (important for UI)
            try:
                import json
                json.dumps(analytics)  # Test serialization
                print("✅ Full analytics serializable for UI")
                results.append(True)
            except (TypeError, ValueError):
                print("❌ Full analytics not serializable")
                results.append(False)
        else:
            print("❌ Full analytics method missing")
            results.append(False)
            
    except Exception as e:
        print(f"❌ Test 5 error: {e}")
        results.append(False)
    
    # Test 6: Strategy Metadata
    print("\n🔧 Test 6: Strategy Metadata...")
    try:
        # Check if trades have strategy metadata
        if engine.trade_history:
            trade = engine.trade_history[0]
            
            if hasattr(trade, 'metadata') and trade.metadata:
                if 'strategy' in trade.metadata:
                    print("✅ Strategy metadata stored in trades")
                    results.append(True)
                else:
                    print("❌ Strategy not in metadata")
                    results.append(False)
            else:
                print("❌ No metadata in trade")
                results.append(False)
        else:
            print("❌ No trade history")
            results.append(False)
            
    except Exception as e:
        print(f"❌ Test 6 error: {e}")
        results.append(False)
    
    # Final Results
    print("\n" + "="*50)
    print("📈 ADVANCED ANALYTICS RESULTS:")
    print("="*50)
    
    all_passed = all(results)
    
    if all_passed:
        print("✅ ADVANCED ANALYTICS ACTIVE!")
        print("\n🎉 ANALYTICS FEATURES:")
        print("✅ Equity curve tracking")
        print("✅ Drawdown calculation")
        print("✅ Strategy performance analysis")
        print("✅ Full analytics output")
        print("✅ UI integration ready")
        print("✅ Strategy metadata tracking")
        print("\n📈 ADVANCED ANALYTICS READY!")
        print("📋 Equity curve shows PnL progression")
        print("📋 Drawdown tracks maximum loss")
        print("📋 Strategy stats per strategy type")
        print("📋 Complete analytics for UI")
        print("📋 Strategy performance breakdown")
        print("\n🚀 ADVANCED ANALYTICS IS PRODUCTION-READY!")
    else:
        print("❌ ADVANCED ANALYTICS INCOMPLETE!")
        failed_tests = [i+1 for i, r in enumerate(results) if not r]
        print(f"❌ Failed tests: {failed_tests}")
        print("\n⚠️  Fix failed tests before production")
    
    return all_passed

if __name__ == "__main__":
    success = test_advanced_analytics()
    sys.exit(0 if success else 1)
