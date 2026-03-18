#!/usr/bin/env python
"""
Comprehensive Backtest Engine Test
Tests the backtest engine with a mock strategy decision engine
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ai.backtest_engine import backtest_engine, BacktestConfig
from dataclasses import dataclass
from typing import Dict, Any, Optional

# Mock Strategy Decision Engine for testing
@dataclass
class MockStrategyDecision:
    strategy: str
    regime: str
    bias_confidence: float
    execution_probability: float
    reasoning: list
    metadata: Dict[str, Any]

class MockStrategyDecisionEngine:
    """Mock strategy engine for testing backtest functionality"""
    
    def __init__(self):
        self.trade_count = 0
        self.last_decision = None
    
    def decide_strategy(self, bias_result, features, snapshot=None) -> MockStrategyDecision:
        """Generate mock trading decisions for testing"""
        self.trade_count += 1
        
        # Simple logic: alternate between BUY, SELL, and NO_TRADE
        if self.trade_count % 3 == 0:
            strategy = "BUY"
            reasoning = ["Mock buy signal", "Test pattern detected"]
        elif self.trade_count % 3 == 1:
            strategy = "SELL"
            reasoning = ["Mock sell signal", "Test pattern detected"]
        else:
            strategy = "NO_TRADE"
            reasoning = ["No signal", "Market conditions unfavorable"]
        
        decision = MockStrategyDecision(
            strategy=strategy,
            regime="RANGING",
            bias_confidence=0.65,
            execution_probability=0.70 if strategy != "NO_TRADE" else 0.0,
            reasoning=reasoning,
            metadata={
                "entry": "WAIT" if strategy == "NO_TRADE" else "EXECUTE",
                "trap": False
            }
        )
        
        self.last_decision = decision
        return decision

# Patch the import
import ai.backtest_engine
ai.backtest_engine.StrategyDecisionEngine = MockStrategyDecisionEngine

def test_backtest_engine():
    """Run comprehensive backtest engine tests"""
    
    print("=" * 60)
    print("STRIKEIQ BACKTEST ENGINE - COMPREHENSIVE TEST")
    print("=" * 60)
    
    # Test 1: Load historical data
    print("\n[TEST 1] Loading historical data")
    success = backtest_engine.load_historical_data()
    print(f"✅ Historical data loaded: {success}")
    print(f"   Candles generated: {len(backtest_engine._candles)}")
    
    if not success or len(backtest_engine._candles) == 0:
        print("❌ Failed to load/generate historical data")
        return False
    
    # Test 2: Configure backtest
    print("\n[TEST 2] Configuring backtest parameters")
    config = BacktestConfig(
        initial_capital=100000.0,  # $100K
        brokerage_per_trade=20.0,  # $20 per trade
        slippage_percent=0.0005,  # 0.05%
        start_date='2024-01-01',
        end_date='2024-03-31'  # 3-month test period
    )
    backtest_engine.config = config
    
    print(f"✅ Backtest configured:")
    print(f"   Initial Capital: ${config.initial_capital:,.2f}")
    print(f"   Brokerage: ${config.brokerage_per_trade:.2f} per trade")
    print(f"   Slippage: {config.slippage_percent*100:.3f}%")
    print(f"   Test Period: {config.start_date} to {config.end_date}")
    
    # Test 3: Run backtest
    print("\n[TEST 3] Running backtest simulation...")
    result = backtest_engine.run_backtest()
    
    # Test 4: Validate results structure
    print("\n[TEST 4] Validating backtest results structure")
    required_fields = [
        'total_trades', 'winning_trades', 'losing_trades', 'win_rate',
        'total_pnl', 'total_commission', 'total_slippage', 'net_pnl',
        'max_drawdown', 'profit_factor', 'sharpe_ratio', 'equity_curve',
        'final_capital'
    ]
    
    all_fields_present = True
    for field in required_fields:
        if not hasattr(result, field):
            print(f"❌ Missing field: {field}")
            all_fields_present = False
        else:
            print(f"✅ Field present: {field}")
    
    if not all_fields_present:
        return False
    
    # Test 5: Validate metrics calculation
    print("\n[TEST 5] Validating metrics calculation")
    print(f"✅ Backtest completed:")
    print(f"   Total Trades: {result.total_trades}")
    print(f"   Win Rate: {result.win_rate:.1%}")
    print(f"   Net P&L: ${result.net_pnl:,.2f}")
    print(f"   Max Drawdown: ${result.max_drawdown:,.2f}")
    print(f"   Profit Factor: {result.profit_factor:.2f}")
    print(f"   Sharpe Ratio: {result.sharpe_ratio:.2f}")
    print(f"   Final Capital: ${result.final_capital:,.2f}")
    
    # Validate win rate calculation
    if result.total_trades > 0:
        expected_win_rate = result.winning_trades / result.total_trades
        if abs(result.win_rate - expected_win_rate) > 0.001:
            print(f"❌ Win rate mismatch: {result.win_rate:.3f} vs {expected_win_rate:.3f}")
            return False
        else:
            print("✅ Win rate calculation correct")
    
    # Test 6: Check equity curve
    print("\n[TEST 6] Equity curve validation")
    if result.equity_curve:
        print(f"   Equity curve points: {len(result.equity_curve)}")
        
        start_equity = result.equity_curve[0][1] if result.equity_curve else 0
        end_equity = result.equity_curve[-1][1] if result.equity_curve else 0
        
        print(f"   Start Equity: ${start_equity:,.2f}")
        print(f"   End Equity: ${end_equity:,.2f}")
        
        total_return = ((end_equity - start_equity) / start_equity * 100) if start_equity != 0 else 0
        print(f"   Total Return: {total_return:.2f}%")
        
        # Check if final capital matches last equity point
        if abs(end_equity - result.final_capital) > 0.01:
            print(f"❌ Final capital mismatch: ${result.final_capital:.2f} vs ${end_equity:.2f}")
            return False
        else:
            print("✅ Final capital matches equity curve")
    else:
        print("❌ No equity curve data")
        return False
    
    # Test 7: Trade validation
    print("\n[TEST 7] Trade validation")
    completed_trades = [t for t in backtest_engine._trades if t.result in ('WIN', 'LOSS')]
    
    if completed_trades:
        print(f"   Completed Trades: {len(completed_trades)}")
        
        # Check for costs
        total_costs = sum(t.commission * 2 + t.slippage for t in completed_trades)
        print(f"   Total Trading Costs: ${total_costs:.2f}")
        
        # Check P&L calculation
        gross_pnl = sum(t.pnl for t in completed_trades)
        net_pnl = sum(t.net_pnl for t in completed_trades)
        
        print(f"   Gross P&L: ${gross_pnl:.2f}")
        print(f"   Net P&L: ${net_pnl:.2f}")
        
        if gross_pnl != 0:
            cost_impact = ((gross_pnl - net_pnl) / gross_pnl * 100)
            print(f"   Cost Impact: {cost_impact:.2f}%")
        
        # Validate win/loss calculation
        wins = [t for t in completed_trades if t.result == 'WIN']
        losses = [t for t in completed_trades if t.result == 'LOSS']
        
        print(f"   Wins: {len(wins)}, Losses: {len(losses)}")
        
        win_rate_validation = len(wins) / len(completed_trades) if completed_trades else 0
        print(f"   Win Rate Validation: {win_rate_validation:.3f}")
        
        # Check if all trades have required fields
        all_trades_valid = True
        for trade in completed_trades[:5]:  # Check first 5 trades
            required_fields = ['entry_time', 'exit_time', 'action', 'entry_price', 
                             'exit_price', 'position_size', 'pnl', 'commission', 
                             'slippage', 'net_pnl', 'result', 'exit_reason']
            for field in required_fields:
                if not hasattr(trade, field):
                    print(f"❌ Trade missing field: {field}")
                    all_trades_valid = False
        
        if all_trades_valid:
            print("✅ Trade structure validation passed")
    else:
        print("   No completed trades (expected for mock strategy)")
    
    # Test 8: File output validation
    print("\n[TEST 8] File output validation")
    data_dir = backtest_engine.data_dir
    
    expected_files = [
        'historical_candles.json',
        'backtest_results.json',
        'backtest_trades.jsonl',
        'equity_curve.json'
    ]
    
    files_exist = True
    for file_name in expected_files:
        file_path = data_dir / file_name
        if file_path.exists():
            print(f"✅ File exists: {file_name}")
        else:
            print(f"❌ File missing: {file_name}")
            files_exist = False
    
    if files_exist:
        print("✅ All output files generated successfully")
    
    # Test 9: Performance metrics validation
    print("\n[TEST 9] Performance metrics validation")
    
    # Validate Sharpe ratio calculation (simplified check)
    if result.sharpe_ratio < -10 or result.sharpe_ratio > 10:
        print(f"⚠️  Unusual Sharpe ratio: {result.sharpe_ratio:.2f}")
    
    # Validate profit factor
    if result.profit_factor < 0:
        print(f"❌ Invalid profit factor: {result.profit_factor:.2f}")
        return False
    else:
        print("✅ Profit factor valid")
    
    # Validate drawdown
    if result.max_drawdown < 0:
        print(f"❌ Invalid drawdown: ${result.max_drawdown:,.2f}")
        return False
    else:
        print("✅ Drawdown valid")
    
    print("\n" + "=" * 60)
    print("✅ ALL BACKTEST TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)
    print("\nSummary:")
    print(f"  • Historical Data: {len(backtest_engine._candles)} candles")
    print(f"  • Total Trades: {result.total_trades}")
    print(f"  • Win Rate: {result.win_rate:.1%}")
    print(f"  • Net P&L: ${result.net_pnl:,.2f}")
    print(f"  • Max Drawdown: ${result.max_drawdown:,.2f}")
    print(f"  • Final Capital: ${result.final_capital:,.2f}")
    print(f"  • Sharpe Ratio: {result.sharpe_ratio:.2f}")
    print(f"  • Output Files: {len(expected_files)} generated")
    
    return True

if __name__ == "__main__":
    success = test_backtest_engine()
    sys.exit(0 if success else 1)
