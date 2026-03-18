# StrikeIQ Backtest Engine Documentation

## Overview

The StrikeIQ Backtest Engine is a comprehensive backtesting and real market simulation system designed to validate trading strategies using historical data with exact trade simulation and real-world trading costs.

## Features

### Core Capabilities
- **Historical Data Loading**: Supports loading historical OHLC candle data
- **Sample Data Generation**: Automatically generates realistic sample data for testing
- **Real Cost Simulation**: Includes brokerage fees and slippage in trade calculations
- **Equity Curve Tracking**: Monitors capital over time with drawdown analysis
- **Comprehensive Metrics**: Calculates win rate, profit factor, Sharpe ratio, and more
- **Trade Management**: Simulates trade entries, exits, and position sizing

### Key Components

#### 1. Data Classes
- `BacktestConfig`: Configuration parameters for backtest runs
- `HistoricalCandle`: OHLC candle data structure
- `BacktestTrade`: Individual trade record with costs and P&L
- `BacktestResult`: Summary statistics and equity curve

#### 2. BacktestEngine Class
Main engine class that orchestrates the backtesting process:
- Load historical data
- Generate features for strategy engine
- Execute trades with real costs
- Track equity curve
- Calculate performance metrics

## Installation & Setup

### Prerequisites
- Python 3.8+
- Required packages: pandas, numpy, dataclasses, pathlib, json, logging

### File Structure
```
backend/ai/
├── backtest_engine.py          # Main backtest engine
├── strategy_decision_engine.py # Strategy decision engine (required)
└── data/backtest/              # Data directory (auto-created)
    ├── historical_candles.json
    ├── backtest_results.json
    ├── backtest_trades.jsonl
    └── equity_curve.json
```

## Usage

### Basic Usage

```python
from ai.backtest_engine import BacktestEngine, BacktestConfig

# Create backtest engine
engine = BacktestEngine()

# Load historical data (or generate sample data)
engine.load_historical_data()

# Configure backtest parameters
config = BacktestConfig(
    initial_capital=100000.0,  # $100K starting capital
    brokerage_per_trade=20.0,  # $20 per trade
    slippage_percent=0.0005,   # 0.05% slippage
    start_date="2024-01-01",
    end_date="2024-12-31",
    timeframe="5min"
)
engine.config = config

# Run backtest
result = engine.run_backtest()

# View results
print(f"Total Trades: {result.total_trades}")
print(f"Win Rate: {result.win_rate:.1%}")
print(f"Net P&L: ${result.net_pnl:,.2f}")
print(f"Sharpe Ratio: {result.sharpe_ratio:.2f}")
```

### Advanced Configuration

```python
# Custom configuration
config = BacktestConfig(
    initial_capital=50000.0,     # Custom starting capital
    brokerage_per_trade=15.0,     # Custom brokerage
    slippage_percent=0.001,       # 0.1% slippage
    start_date="2023-01-01",      # Custom date range
    end_date="2023-12-31",
    timeframe="1min"              # Different timeframe
)
```

## Backtest Process

### Step 1: Data Loading
The engine first loads historical candle data:
- Attempts to load from `data/backtest/historical_candles.json`
- If file doesn't exist, generates 1000 sample candles with realistic price movements
- Sample data uses random walk with slight upward bias

### Step 2: Simulation Loop
For each historical candle:
1. **Feature Generation**: Creates features from OHLC data
2. **Strategy Decision**: Calls strategy engine for trade signals
3. **Trade Creation**: Simulates trade execution with costs
4. **Position Management**: Tracks open trades and exits

### Step 3: Cost Simulation
Real trading costs are applied:
- **Brokerage**: Fixed cost per trade (entry + exit)
- **Slippage**: Percentage of price (0.05% default)
- Total costs deducted from trade P&L

### Step 4: Equity Tracking
- Updates equity after each trade
- Tracks running maximum for drawdown calculation
- Saves equity curve for analysis

### Step 5: Metrics Calculation
Comprehensive performance metrics:
- **Win Rate**: Percentage of profitable trades
- **Profit Factor**: Gross profit / gross loss
- **Max Drawdown**: Peak-to-trough decline
- **Sharpe Ratio**: Risk-adjusted return (annualized)
- **Total P&L**: Net profit/loss after costs

## Output Format

### Console Output
```
============================================================
[BACKTEST RESULT]
win_rate: 0.650
total_pnl: 12500.00
max_drawdown: 2500.00
profit_factor: 2.15
sharpe_ratio: 1.85
total_trades: 40
winning_trades: 26
net_pnl: 11800.00
total_commission: 800.00
total_slippage: 900.00
final_capital: 111800.00
============================================================
```

### File Output
- `historical_candles.json`: Raw OHLC data
- `backtest_results.json`: Summary statistics
- `backtest_trades.jsonl`: Individual trade records
- `equity_curve.json`: Equity curve data points

## Trade Management

### Entry Logic
- Position sizing based on 1% risk per trade
- Stop loss and target levels calculated from market data
- Slippage applied to entry price

### Exit Logic
- Stop loss: 2% move against position
- Target: 3% move in favor of position
- Slippage applied to exit price
- Trade marked as WIN/LOSS based on net P&L

### Cost Calculation
```python
# Entry costs
entry_slippage = entry_price * slippage_percent
adjusted_entry = entry_price + (entry_slippage * direction)
entry_commission = brokerage_per_trade

# Exit costs
exit_slippage = exit_price * slippage_percent
adjusted_exit = exit_price - (exit_slippage * direction)
exit_commission = brokerage_per_trade

# Net P&L
gross_pnl = (adjusted_exit - adjusted_entry) * direction * position_size
total_costs = entry_commission + exit_commission + entry_slippage + exit_slippage
net_pnl = gross_pnl - total_costs
```

## Performance Metrics

### Win Rate
- Calculation: `winning_trades / total_completed_trades`
- Range: 0.0 to 1.0 (0% to 100%)

### Profit Factor
- Calculation: `gross_wins / abs(gross_losses)`
- Values > 1.0 indicate profitable system
- Values < 1.0 indicate losing system

### Max Drawdown
- Calculation: `peak - trough` from equity curve
- Represents maximum loss from peak
- Important for risk assessment

### Sharpe Ratio
- Simplified calculation using returns standard deviation
- Annualized: `(mean_return / std_return) * sqrt(252)`
- Higher values indicate better risk-adjusted returns

## Integration with Strategy Engine

The backtest engine integrates with the existing strategy decision engine:

```python
# Inside backtest loop
from strategy_decision_engine import StrategyDecisionEngine
strategy_engine = StrategyDecisionEngine()
decision = strategy_engine.decide_strategy(None, features)

if decision.strategy != "NO_TRADE":
    # Create and execute trade
    trade = self._create_backtest_trade(decision, features, candle)
```

## Error Handling

The engine includes robust error handling:
- Graceful fallback when strategy engine unavailable
- Safe defaults for missing data
- Comprehensive logging for debugging
- Default result object for error cases

## Testing

### Unit Tests
Run comprehensive tests:
```bash
cd backend
python test_backtest_engine.py
```

### Manual Testing
```python
# Quick test
engine = BacktestEngine()
engine.load_historical_data()
result = engine.run_backtest()
print(f"Test completed: {result.total_trades} trades")
```

## Best Practices

1. **Data Quality**: Use high-quality historical data for accurate results
2. **Cost Realism**: Set realistic brokerage and slippage values
3. **Sample Size**: Use sufficient data (1000+ candles) for statistical significance
4. **Multiple Runs**: Test different date ranges for robustness
5. **Validation**: Compare results with expected outcomes

## Troubleshooting

### Common Issues

1. **No Strategy Engine**
   - Error: "No module named 'strategy_decision_engine'"
   - Solution: Ensure strategy engine is available or use mock

2. **No Historical Data**
   - Error: "Historical data file not found"
   - Solution: Engine auto-generates sample data

3. **Zero Trades**
   - Issue: Strategy returns NO_TRADE for all signals
   - Solution: Check strategy logic and feature generation

### Debug Logging
Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Future Enhancements

Planned improvements:
- Multi-asset backtesting
- Portfolio-level risk management
- Advanced order types
- Monte Carlo simulation
- Walk-forward analysis
- Performance attribution

## Conclusion

The StrikeIQ Backtest Engine provides a robust framework for validating trading strategies with realistic market conditions. By incorporating real trading costs and comprehensive performance metrics, it ensures that backtested strategies are more likely to perform well in live trading environments.
