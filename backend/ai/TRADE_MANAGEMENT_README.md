# Risk Management + Position Sizing + Exit Engine

## Overview

The trade management system transforms StrikeIQ into a full trade lifecycle engine with comprehensive risk management, position sizing, and exit management while maintaining capital protection.

## Components

### 1. TradeManager Class

Main class that handles:
- Trade creation from strategy decisions
- Risk-based position sizing
- Stop loss and target definition
- Real-time trade management
- P&L calculation and tracking
- Comprehensive risk metrics

### 2. Data Structures

**Trade**: Active trade object
- timestamp, action, entry_price, confidence
- stop_loss, target, position_size, risk_amount
- direction (+1 for BUY, -1 for SELL)

**TradeResult**: Completed trade outcome
- Entry/exit prices, P&L, result (WIN/LOSS)
- exit_reason (STOP_LOSS, TARGET_HIT, TIME_EXIT)
- duration, confidence tracking

**TradeConfig**: Risk management configuration
- Account size, risk per trade percentage
- Maximum position size, buffer settings
- Time limits and minimum tick size

**RiskMetrics**: Comprehensive risk analytics
- Win rates, P&L tracking, drawdown analysis
- Risk/reward ratios, performance statistics

## Core Features

### 1. Risk-Based Position Sizing

```python
# Fixed 1% risk per trade
risk_per_trade = account_size * 0.01
position_size = risk_per_trade / risk_per_unit

# Maximum 10% exposure cap
position_size = min(position_size, account_size * 0.1)
```

### 2. Intelligent Stop Loss & Targets

```python
# 0.2% buffer for realistic exits
buffer = spot * 0.002

if action == "BUY":
    stop_loss = put_wall - buffer
    target = call_wall
elif action == "SELL":
    stop_loss = call_wall + buffer
    target = put_wall
```

### 3. Real-Time Trade Management

Continuous monitoring of:
- Stop loss triggers (capital protection)
- Target hits (profit taking)
- Time-based exits (risk control)
- P&L calculation and tracking

### 4. Comprehensive Risk Metrics

- **Win Rate**: Percentage of profitable trades
- **Risk/Reward Ratio**: Average win vs average loss
- **Maximum Drawdown**: Largest peak-to-trough decline
- **Current Drawdown**: Current underwater amount
- **Average Win/Loss**: Performance by outcome type

## Usage

### Basic Integration

```python
from ai.trade_manager import trade_manager, TradeConfig
from ai.strategy_decision_engine import StrategyDecisionEngine

# Initialize with custom config
config = TradeConfig(
    account_size=100000.0,  # $100K account
    risk_per_trade_percent=0.01,  # 1% risk
    max_position_percent=0.1,  # 10% max
)
trade_manager.config = config

# Load historical data
trade_manager.load_historical_data()
```

### Trade Creation & Execution

```python
# Get strategy decision
decision = strategy_engine.decide_strategy(None, features)

# Create trade with risk management
trade = trade_manager.create_trade(decision, features)
if trade:
    # Execute trade
    success = trade_manager.execute_trade(trade)
    
    # Monitor for exits
    results = trade_manager.manage_trades(current_price)
```

### Risk Monitoring

```python
# Calculate comprehensive metrics
metrics = trade_manager.calculate_risk_metrics()
trade_manager.print_risk_debug()

# Access specific data
active_trades = trade_manager.get_active_trades()
trade_results = trade_manager.get_trade_results()
```

## Risk Controls

### 1. Capital Protection

- ✅ Maximum 1% risk per trade
- ✅ 10% maximum position size
- ✅ Stop loss always defined
- ✅ Minimum tick size validation

### 2. Position Sizing Logic

- ✅ Risk-based calculation
- ✅ Account size consideration
- ✅ Volatility-adjusted sizing
- ✅ Maximum exposure limits

### 3. Exit Management

- ✅ Stop loss enforcement
- ✅ Target hit detection
- ✅ Time-based exits (24h max)
- ✅ P&L calculation accuracy

### 4. Drawdown Protection

- ✅ Continuous drawdown monitoring
- ✅ Peak-to-trough tracking
- ✅ Current risk assessment
- ✅ Historical risk analysis

## Validation Results

### ✅ Risk Management Rules

1. **Risk per trade never exceeds 1%**
   - Fixed 1% of account size
   - Position sizing based on stop loss distance
   - Maximum exposure caps

2. **Every trade has SL + target**
   - Stop loss at support/resistance levels
   - Targets at opposite walls
   - 0.2% buffer for realistic exits

3. **P&L always calculated**
   - Direction-aware calculation
   - Position size consideration
   - Percentage and absolute P&L

4. **No trade without proper risk**
   - Minimum tick validation
   - Price data verification
   - Configuration enforcement

5. **Same input → same trade setup**
   - Deterministic calculations
   - Consistent position sizing
   - Reproducible risk metrics

### ✅ Trade Lifecycle Management

- **Entry**: Strategy decision → Trade creation → Execution
- **Management**: Real-time monitoring → Exit detection
- **Exit**: P&L calculation → Result storage
- **Analysis**: Risk metrics → Performance tracking

### ✅ Data Integrity

- **Persistent Storage**: JSONL for results, JSON for active trades
- **Historical Loading**: Complete data recovery on restart
- **Atomic Operations**: Safe file handling
- **Error Recovery**: Graceful failure handling

## Production Benefits

### 1. Capital Protection
- Fixed risk per trade prevents catastrophic losses
- Stop loss enforcement limits downside
- Position sizing prevents over-leveraging

### 2. Consistent Performance
- Deterministic trade setup
- Reproducible risk calculations
- Reliable exit management

### 3. Comprehensive Analytics
- Complete trade lifecycle tracking
- Detailed risk metrics
- Performance analysis capabilities

### 4. Configurable Risk
- Adjustable account size
- Customizable risk percentages
- Flexible time limits

## Configuration Options

```python
TradeConfig(
    account_size=100000.0,        # Trading account size
    risk_per_trade_percent=0.01,     # 1% risk per trade
    max_position_percent=0.1,        # 10% max position
    minimum_tick=0.01,              # Minimum price movement
    max_hold_time_hours=24.0,         # Maximum hold time
    buffer_percent=0.002              # 0.2% SL/target buffer
)
```

## File Structure

```
data/trades/
├── active_trades.json      # Current open positions
├── trade_results.jsonl     # Completed trade history
└── risk_metrics.json       # Latest risk analytics
```

## Integration Points

1. **Strategy Engine**: Receives decisions, creates trades
2. **Price Feed**: Provides current prices for exit checks
3. **Risk Dashboard**: Displays metrics and active trades
4. **Configuration**: Allows runtime parameter adjustment

The trade management system provides enterprise-grade risk management while maintaining deterministic behavior and capital protection required for production trading systems.
