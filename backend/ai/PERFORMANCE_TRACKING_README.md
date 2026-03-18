# Performance Tracking + Auto-Learning Layer

## Overview

The performance tracking system monitors every AI trading decision, evaluates outcomes, and provides auto-tuning suggestions to improve system performance over time.

## Components

### 1. PerformanceTracker Class

Main class that handles:
- Storing trade signals
- Evaluating outcomes
- Computing performance metrics
- Generating auto-tuning suggestions

### 2. Data Structures

**TradeSignal**: Stores every trading decision
- timestamp, action, confidence, probability
- spot_price, entry_signal, reasoning
- regime, trap_detected, htf_bias

**TradeOutcome**: Stores evaluation results
- Links to original TradeSignal
- future_price, result, price_change
- WIN/LOSS/SKIPPED classification

**PerformanceMetrics**: Aggregated performance data
- Win rates, confidence accuracy
- Performance by regime/entry/trap status
- Auto-tuning suggestions

## Usage

### Basic Integration

```python
from ai.performance_tracker import performance_tracker
from ai.strategy_decision_engine import StrategyDecisionEngine

# Initialize
strategy_engine = StrategyDecisionEngine()
performance_tracker.load_historical_data()

# Get decision and store signal
decision = strategy_engine.decide_strategy(None, features)
performance_tracker.store_signal(decision, features)

# Periodically evaluate outcomes (e.g., every 5 minutes)
current_price = get_current_market_price()
outcomes = performance_tracker.evaluate_outcomes(current_price, 5)

# Get performance metrics
metrics = performance_tracker.compute_metrics()
performance_tracker.print_performance_debug()

# Get auto-tuning suggestions
suggestions = performance_tracker.get_auto_tuning_suggestions()
```

### Data Storage

Files stored in `data/performance/`:
- `trade_signals.jsonl`: All trading decisions
- `trade_outcomes.jsonl`: Evaluated outcomes
- `performance_metrics.json`: Latest metrics summary

## Performance Metrics

### Core Metrics
- **Win Rate**: Percentage of profitable trades
- **Avg Confidence**: Average confidence of all trades
- **Confidence Accuracy**: Correlation between confidence and actual results

### Performance Buckets

**By Regime**: Performance in different market conditions
- TRENDING, RANGING, BREAKOUT regimes
- Identifies best/worst performing environments

**By Entry Type**: Performance by entry timing
- ENTER_NOW vs WAIT_FOR_PULLBACK
- Shows optimal entry strategies

**By Trap Detection**: Performance with/without traps
- trap_detected vs no_trap scenarios
- Validates trap detection effectiveness

## Auto-Tuning Suggestions

### Trap Performance
If trap win rate < 30%:
- Suggests increasing trap penalty by 20%
- Reduces false signals in trap scenarios

### Confidence Accuracy
If confidence accuracy < 0.2 and avg confidence > 0.7:
- Suggests reducing confidence scaling
- Improves confidence calibration

### Regime Adjustment
If any regime has win rate < 30%:
- Suggests reducing confidence in that regime
- Adapts to market-specific performance

## Validation Results

### ✅ Core Functionality
- Stores all trade decisions correctly
- Evaluates outcomes with proper WIN/LOSS classification
- Computes accurate performance metrics
- Maintains deterministic behavior

### ✅ Performance Buckets
- Correctly groups by regime, entry type, trap status
- Identifies performance patterns
- Provides actionable insights

### ✅ Auto-Tuning
- Generates appropriate suggestions based on performance
- Triggers on meaningful sample sizes (>5 trades)
- Provides specific improvement recommendations

### ✅ Data Integrity
- Persistent storage in JSONL format
- Historical data loading capability
- No impact on strategy decision logic

## Integration Points

### 1. Signal Storage
Call after every strategy decision:
```python
performance_tracker.store_signal(decision, features)
```

### 2. Outcome Evaluation
Call periodically with current price:
```python
outcomes = performance_tracker.evaluate_outcomes(current_price, 5)
```

### 3. Metrics Review
Call for performance analysis:
```python
metrics = performance_tracker.compute_metrics()
suggestions = performance_tracker.get_auto_tuning_suggestions()
```

## Benefits

1. **Performance Visibility**: Clear metrics on system effectiveness
2. **Pattern Recognition**: Identifies best/worst performing scenarios
3. **Continuous Improvement**: Auto-tuning suggestions for optimization
4. **Risk Management**: Better understanding of confidence calibration
5. **Market Adaptation**: Regime-specific performance insights

## Production Considerations

- Runs independently of strategy engine (no interference)
- Persistent data storage survives restarts
- Minimal computational overhead
- Safe fallbacks for edge cases
- Deterministic behavior maintained

The performance tracking layer provides comprehensive insights into AI trading performance while maintaining system stability and enabling continuous improvement.
