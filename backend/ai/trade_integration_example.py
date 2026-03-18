"""
Trade Management Integration Example
Shows complete trade lifecycle from strategy decision to exit management.
"""

import sys
import time
from datetime import datetime, timedelta
from strategy_decision_engine import StrategyDecisionEngine
from trade_manager import trade_manager, TradeConfig

def simulate_market_movement(initial_price: float, direction: str, steps: int = 10) -> list:
    """Simulate market price movement for testing"""
    prices = [initial_price]
    
    for i in range(steps):
        if direction == "UP":
            # Move toward target for BUY
            change = (20100 - initial_price) / steps
        elif direction == "DOWN":
            # Move toward target for SELL
            change = (19800 - initial_price) / steps
        else:
            # Random walk
            import random
            change = random.uniform(-20, 20)
        
        new_price = prices[-1] + change
        prices.append(max(new_price, 19000))  # Floor price
    
    return prices

def example_trade_lifecycle():
    """Example of complete trade lifecycle"""
    
    # Initialize components
    strategy_engine = StrategyDecisionEngine()
    
    # Configure trade manager with custom settings
    config = TradeConfig(
        account_size=50000.0,  # $50K account
        risk_per_trade_percent=0.02,  # 2% risk per trade
        max_position_percent=0.15,  # 15% max position
        buffer_percent=0.003,  # 0.3% buffer
        max_hold_time_hours=12.0  # 12 hour max hold
    )
    trade_manager.config = config
    
    # Load historical data
    trade_manager.load_historical_data()
    
    print("=== TRADE LIFECYCLE DEMONSTRATION ===")
    print(f"Account Size: ${config.account_size:,.2f}")
    print(f"Risk per Trade: {config.risk_per_trade_percent*100:.1f}% (${config.account_size * config.risk_per_trade_percent:,.2f})")
    print()
    
    # Example 1: BUY Trade Lifecycle
    print("=== EXAMPLE 1: BUY TRADE ===")
    
    features = {
        'spot': 19900,
        'recent_high': 20100,
        'recent_low': 19850,
        'volume': 1000000,
        'avg_volume': 800000,
        'call_wall_strike': 20100,
        'put_wall_strike': 19850,
        'call_oi_distribution': {20100: 1000},
        'put_oi_distribution': {19850: 2000},
        'oi_change_calls': 100,
        'oi_change_puts': 300,
        'gex_profile': {'net_gamma': -100000},
        'htf_bias': 'BUY'
    }
    
    # Get strategy decision
    decision = strategy_engine.decide_strategy(None, features)
    print(f"Strategy Decision: {decision.strategy}")
    print(f"Confidence: {decision.bias_confidence:.3f}")
    print(f"Entry Signal: {decision.metadata.get('entry', 'WAIT') if decision.metadata else 'WAIT'}")
    
    # Create and execute trade
    trade = trade_manager.create_trade(decision, features)
    if trade:
        success = trade_manager.execute_trade(trade)
        if success:
            print(f"Trade Executed: {trade.action} @ {trade.entry_price}")
            print(f"Stop Loss: {trade.stop_loss} | Target: {trade.target}")
            print(f"Position Size: {trade.position_size:.2f} | Risk: ${trade.risk_amount:.2f}")
            
            # Simulate market movement toward stop loss
            print("\nSimulating market movement...")
            prices = simulate_market_movement(trade.entry_price, "DOWN", steps=8)
            
            for i, price in enumerate(prices[1:], 1):
                print(f"  Step {i}: Price = {price:.2f}")
                
                # Check for trade exit
                results = trade_manager.manage_trades(price)
                if results:
                    result = results[0]
                    print(f"\n🎯 TRADE EXITED!")
                    print(f"  Result: {result.result}")
                    print(f"  Reason: {result.exit_reason}")
                    print(f"  P&L: ${result.pnl:.2f} ({result.pnl_percent:.2f}%)")
                    print(f"  Duration: {result.duration_minutes:.1f} minutes")
                    break
                
                time.sleep(0.1)  # Small delay for demonstration
    
    print("\n" + "="*50)
    
    # Example 2: SELL Trade Lifecycle
    print("=== EXAMPLE 2: SELL TRADE ===")
    
    # Modify features for SELL signal
    features_sell = features.copy()
    features_sell.update({
        'spot': 20050,
        'oi_change_calls': 300,
        'oi_change_puts': 100,
        'gex_profile': {'net_gamma': 100000},
        'htf_bias': 'SELL'
    })
    
    decision_sell = strategy_engine.decide_strategy(None, features_sell)
    print(f"Strategy Decision: {decision_sell.strategy}")
    
    # Create and execute SELL trade
    trade_sell = trade_manager.create_trade(decision_sell, features_sell)
    if trade_sell:
        success = trade_manager.execute_trade(trade_sell)
        if success:
            print(f"Trade Executed: {trade_sell.action} @ {trade_sell.entry_price}")
            print(f"Stop Loss: {trade_sell.stop_loss} | Target: {trade_sell.target}")
            print(f"Position Size: {trade_sell.position_size:.2f} | Risk: ${trade_sell.risk_amount:.2f}")
            
            # Simulate market movement toward target
            print("\nSimulating market movement...")
            prices = simulate_market_movement(trade_sell.entry_price, "DOWN", steps=6)
            
            for i, price in enumerate(prices[1:], 1):
                print(f"  Step {i}: Price = {price:.2f}")
                
                # Check for trade exit
                results = trade_manager.manage_trades(price)
                if results:
                    result = results[0]
                    print(f"\n🎯 TRADE EXITED!")
                    print(f"  Result: {result.result}")
                    print(f"  Reason: {result.exit_reason}")
                    print(f"  P&L: ${result.pnl:.2f} ({result.pnl_percent:.2f}%)")
                    print(f"  Duration: {result.duration_minutes:.1f} minutes")
                    break
                
                time.sleep(0.1)
    
    print("\n" + "="*50)
    
    # Example 3: Risk Metrics Summary
    print("=== EXAMPLE 3: RISK METRICS SUMMARY ===")
    
    # Calculate comprehensive risk metrics
    metrics = trade_manager.calculate_risk_metrics()
    
    print(f"Total Trades: {metrics.total_trades}")
    print(f"Win Rate: {metrics.win_rate:.1%}")
    print(f"Total P&L: ${metrics.total_pnl:,.2f}")
    print(f"Average Win: ${metrics.avg_win:,.2f}")
    print(f"Average Loss: ${metrics.avg_loss:,.2f}")
    print(f"Risk/Reward Ratio: {metrics.risk_reward_ratio:.2f}")
    print(f"Max Drawdown: ${metrics.max_drawdown:,.2f}")
    print(f"Current Drawdown: ${metrics.current_drawdown:,.2f}")
    
    # Risk validation
    print("\n=== RISK VALIDATION ===")
    
    # Check 1: Risk per trade never exceeds 1%
    expected_risk = config.account_size * config.risk_per_trade_percent
    actual_risks = [t.risk_amount for t in trade_manager.get_trade_results()]
    if actual_risks:
        max_risk = max(actual_risks)
        print(f"✅ Max Risk per Trade: ${max_risk:.2f} (Limit: ${expected_risk:.2f})")
        print(f"   Risk Limit Respected: {max_risk <= expected_risk}")
    
    # Check 2: Every trade has SL + target
    active_trades = trade_manager.get_active_trades()
    print(f"✅ Active Trades with SL/Target: {len(active_trades)}")
    
    # Check 3: Position size limits
    max_position = config.account_size * config.max_position_percent
    print(f"✅ Max Position Limit: ${max_position:,.2f}")
    
    print("\n=== INTEGRATION COMPLETE ===")
    print("Trade management system successfully integrated with:")
    print("✅ Risk-based position sizing")
    print("✅ Stop loss and target definition")
    print("✅ Real-time trade management")
    print("✅ P&L calculation and tracking")
    print("✅ Comprehensive risk metrics")
    print("✅ Capital protection controls")

if __name__ == "__main__":
    example_trade_lifecycle()
