#!/usr/bin/env python3
"""
Strategy Validation Test Script
Tests strategy performance on real market data with train/test split
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ai.backtest_engine import BacktestEngine, BacktestConfig

def main():
    print("🔍 STRATEGY VALIDATION WITH REAL MARKET DATA")
    print("=" * 60)
    
    # Create backtest engine
    engine = BacktestEngine()
    
    # Configure for validation
    engine.config = BacktestConfig(
        initial_capital=100000,
        brokerage_per_trade=20,
        slippage_percent=0.0005
    )
    
    # Run validation backtest
    print("📊 Running train/test validation...")
    validation_results = engine.run_validation_backtest()
    
    if "error" in validation_results:
        print(f"❌ Validation failed: {validation_results['error']}")
        return
    
    print("\n📈 VALIDATION RESULTS")
    print("=" * 60)
    print(f"Training Data:")
    print(f"  Trades: {validation_results['train_trades']}")
    print(f"  Win Rate: {validation_results['train_win_rate']:.2%}")
    print(f"  Net P&L: ${validation_results['train_pnl']:,.2f}")
    print(f"  Profit Factor: {validation_results['train_profit_factor']:.2f}")
    
    print(f"\nTest Data:")
    print(f"  Trades: {validation_results['test_trades']}")
    print(f"  Win Rate: {validation_results['test_win_rate']:.2%}")
    print(f"  Net P&L: ${validation_results['test_pnl']:,.2f}")
    print(f"  Profit Factor: {validation_results['test_profit_factor']:.2f}")
    
    print(f"\n🎯 VALIDATION STATUS")
    print("=" * 60)
    status = validation_results['validation_status']
    reason = validation_results['validation_reason']
    
    if status == "VALID":
        print(f"✅ {status}")
        print(f"   {reason}")
        print("\n🎉 STRATEGY IS VALID - Ready for production!")
    elif status == "OVERFITTED":
        print(f"⚠️  {status}")
        print(f"   {reason}")
        print("\n🔧 STRATEGY NEEDS ADJUSTMENT")
        print("   Consider reducing complexity or adding regularization")
    elif status == "INSUFFICIENT_DATA":
        print(f"📊 {status}")
        print(f"   {reason}")
        print("\n📈 NEED MORE DATA OR DIFFERENT CONDITIONS")
    else:
        print(f"❓ {status}")
        print(f"   {reason}")
    
    print("\n" + "=" * 60)
    print("🔍 VALIDATION COMPLETE")
    
    # Performance comparison
    if validation_results['test_trades'] > 0 and validation_results['train_trades'] > 0:
        train_performance = validation_results['train_win_rate']
        test_performance = validation_results['test_win_rate']
        performance_gap = abs(test_performance - train_performance)
        
        print(f"\n📊 PERFORMANCE ANALYSIS")
        print(f"  Training Win Rate: {train_performance:.2%}")
        print(f"  Test Win Rate: {test_performance:.2%}")
        print(f"  Performance Gap: {performance_gap:.2%}")
        
        if performance_gap < 0.05:
            print("  ✅ Excellent consistency between train/test")
        elif performance_gap < 0.10:
            print("  ✅ Good consistency between train/test")
        elif performance_gap < 0.20:
            print("  ⚠️  Moderate consistency - monitor for overfitting")
        else:
            print("  ❌ Poor consistency - likely overfitted")

if __name__ == "__main__":
    main()
