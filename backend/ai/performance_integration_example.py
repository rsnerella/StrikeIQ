"""
Performance Tracking Integration Example
Shows how to integrate performance tracking with the strategy decision engine.
"""

import sys
from datetime import datetime, timedelta
from strategy_decision_engine import StrategyDecisionEngine
from performance_tracker import performance_tracker

def example_integration():
    """Example of integrating performance tracking with strategy engine"""
    
    # Initialize components
    strategy_engine = StrategyDecisionEngine()
    
    # Load historical data
    performance_tracker.load_historical_data()
    
    # Example features
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
    
    print("=== STRATEGY DECISION + PERFORMANCE TRACKING ===")
    
    # Get strategy decision
    decision = strategy_engine.decide_strategy(None, features)
    
    # Store the signal for performance tracking
    performance_tracker.store_signal(decision, features)
    
    print(f"Decision: {decision.strategy}")
    print(f"Confidence: {decision.bias_confidence:.3f}")
    print(f"Entry Signal: {decision.metadata.get('entry', 'WAIT') if decision.metadata else 'WAIT'}")
    print(f"Trap Detected: {decision.metadata.get('trap', False) if decision.metadata else False}")
    
    # Simulate time passing and price movement
    current_price = 19950  # Price moved up by 50 points
    
    # Evaluate outcomes for signals older than 5 minutes
    outcomes = performance_tracker.evaluate_outcomes(current_price, evaluation_window_minutes=5)
    
    if outcomes:
        print(f"\n=== EVALUATED {len(outcomes)} OUTCOMES ===")
        for outcome in outcomes:
            print(f"{outcome.original_signal.action}: {outcome.result} ({outcome.price_change_pct:.2f}%)")
    
    # Compute and display performance metrics
    print("\n=== PERFORMANCE METRICS ===")
    performance_tracker.print_performance_debug()
    
    # Get auto-tuning suggestions
    suggestions = performance_tracker.get_auto_tuning_suggestions()
    if suggestions:
        print("\n=== AUTO-TUNING SUGGESTIONS ===")
        for key, suggestion in suggestions.items():
            print(f"{key}: {suggestion}")
    
    print("\n=== INTEGRATION COMPLETE ===")

if __name__ == "__main__":
    example_integration()
