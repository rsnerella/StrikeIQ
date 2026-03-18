"""
Backtest + Real Market Simulation Engine for StrikeIQ
Validates strategy using historical data with exact trade simulation and real costs.
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import json
import logging
import os
from pathlib import Path
import statistics
import pandas as pd
import numpy as np

# Import real engines
from .feature_engine import FeatureEngine
from .strategy_decision_engine import StrategyDecisionEngine

logger = logging.getLogger(__name__)

# Mock option chain snapshot class for feature engine compatibility
class MockOptionChainSnapshot:
    """Mock option chain snapshot that matches feature engine expectations"""
    def __init__(self, spot: float, timestamp: str, strikes: Dict, expiry: str, symbol: str):
        self.spot = spot
        self.timestamp = timestamp
        self.strikes = strikes  # Feature engine expects 'strikes' attribute
        self.expiry = expiry
        self.symbol = symbol

@dataclass
class BacktestConfig:
    """Backtest configuration"""
    initial_capital: float = 100000.0
    brokerage_per_trade: float = 20.0  # Fixed cost per trade
    slippage_percent: float = 0.0005  # 0.05% slippage
    start_date: str = "2024-01-01"
    end_date: str = "2024-12-31"
    timeframe: str = "5min"  # Candle timeframe

@dataclass
class HistoricalCandle:
    """Historical OHLC candle data"""
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: int

@dataclass
class BacktestTrade:
    """Backtest trade record"""
    entry_time: str
    exit_time: str
    action: str
    entry_price: float
    exit_price: float
    position_size: float
    pnl: float
    commission: float
    slippage: float
    net_pnl: float
    result: str
    exit_reason: str

@dataclass
class BacktestResult:
    """Backtest results summary"""
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    total_commission: float
    total_slippage: float
    net_pnl: float
    max_drawdown: float
    profit_factor: float
    sharpe_ratio: float
    equity_curve: List[Tuple[str, float]]
    final_capital: float

class BacktestEngine:
    """Backtest and simulation engine"""
    
    def __init__(self, config: Optional[BacktestConfig] = None, data_dir: str = "data/backtest"):
        self.config = config or BacktestConfig()
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.historical_data_file = self.data_dir / "historical_candles.json"
        self.backtest_results_file = self.data_dir / "backtest_results.json"
        
        # In-memory data
        self._candles: List[HistoricalCandle] = []
        self._trades: List[BacktestTrade] = []
        self._equity_curve: List[Tuple[str, float]] = []
        
        # Initialize real engines
        self.feature_engine = FeatureEngine()
        self.strategy_engine = StrategyDecisionEngine()
        
        logger.info(f"BacktestEngine initialized with capital: {self.config.initial_capital}")
    
    def load_real_market_data(self, file_path: Optional[str] = None) -> bool:
        """Load real historical NIFTY market data"""
        try:
            # Try to load existing historical data
            data_file = Path(file_path) if file_path else self.historical_data_file
            
            if not data_file.exists():
                logger.warning(f"Real market data file not found: {data_file}")
                # Fall back to sample data for testing
                self._generate_sample_data()
                return False
            
            with open(data_file, 'r') as f:
                data = json.load(f)
                
            self._candles = [HistoricalCandle(**candle) for candle in data]
            logger.info(f"Loaded {len(self._candles)} real historical candles")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load real market data: {e}")
            return False
    
    def split_train_test_data(self, train_ratio: float = 0.7) -> Tuple[List[HistoricalCandle], List[HistoricalCandle]]:
        """Split data into training and testing sets"""
        if len(self._candles) < 100:
            logger.warning("Insufficient data for train/test split")
            return self._candles, []
        
        split_point = int(len(self._candles) * train_ratio)
        train_data = self._candles[:split_point]
        test_data = self._candles[split_point:]
        
        logger.info(f"Data split: {len(train_data)} train, {len(test_data)} test")
        return train_data, test_data
    
    def _generate_sample_data(self) -> None:
        """Generate sample historical data for demonstration"""
        logger.info("Generating sample historical data...")
        
        # Generate 1000 candles with realistic price movement
        np.random.seed(42)  # For reproducible results
        
        base_price = 20000
        candles = []
        current_time = datetime.strptime(self.config.start_date, "%Y-%m-%d")
        
        for i in range(1000):
            # Random walk with slight upward bias
            change = np.random.normal(0, 50)  # Mean 0, std 50
            new_price = max(base_price + change, 19000)  # Floor at 19000
            
            # Generate OHLC
            high = new_price + abs(np.random.normal(0, 20))
            low = new_price - abs(np.random.normal(0, 20))
            close = new_price + np.random.normal(0, 10)
            volume = np.random.randint(100000, 1000000)
            
            candle = HistoricalCandle(
                timestamp=current_time.isoformat(),
                open=new_price,
                high=max(high, new_price),
                low=min(low, new_price),
                close=max(close, new_price),
                volume=volume
            )
            
            candles.append(candle)
            base_price = close
            current_time += timedelta(minutes=5)
        
        self._candles = candles
        
        # Save sample data
        with open(self.historical_data_file, 'w') as f:
            json.dump([asdict(candle) for candle in candles], f, indent=2, default=str)
        
        logger.info(f"Generated {len(candles)} sample candles")
    
    def run_validation_backtest(self) -> Dict[str, Any]:
        """Run train/test validation backtest"""
        try:
            logger.info("Starting validation backtest with train/test split...")
            
            # Load real data
            if not self.load_real_market_data():
                logger.warning("Using sample data for validation")
            
            # Split data
            train_data, test_data = self.split_train_test_data(0.7)
            
            if not test_data:
                logger.error("No test data available")
                return {"error": "No test data"}
            
            # Run backtest on training data
            logger.info("Running backtest on training data...")
            self._candles = train_data
            train_result = self.run_backtest()
            
            # Run backtest on test data
            logger.info("Running backtest on test data...")
            self._candles = test_data
            test_result = self.run_backtest()
            
            # Validation analysis
            validation = {
                "train_trades": train_result.total_trades,
                "test_trades": test_result.total_trades,
                "train_win_rate": train_result.win_rate,
                "test_win_rate": test_result.win_rate,
                "train_pnl": train_result.net_pnl,
                "test_pnl": test_result.net_pnl,
                "train_profit_factor": train_result.profit_factor,
                "test_profit_factor": test_result.profit_factor,
                "validation_status": "UNKNOWN"
            }
            
            # Validate strategy performance
            if test_result.total_trades > 0:
                performance_diff = abs(test_result.win_rate - train_result.win_rate)
                pnl_diff = abs(test_result.net_pnl - train_result.net_pnl)
                
                if performance_diff < 0.1 and pnl_diff < (train_result.net_pnl * 0.2):
                    validation["validation_status"] = "VALID"
                    validation["validation_reason"] = "Test performance close to training - strategy is valid"
                else:
                    validation["validation_status"] = "OVERFITTED"
                    validation["validation_reason"] = "Test performance differs significantly from training - strategy may be overfitted"
            else:
                validation["validation_status"] = "INSUFFICIENT_DATA"
                validation["validation_reason"] = "No trades generated in test period"
            
            return validation
            
        except Exception as e:
            logger.error(f"Validation backtest failed: {e}")
            return {"error": str(e)}
    
    def run_backtest(self) -> BacktestResult:
        """Run complete backtest simulation"""
        try:
            logger.info("Starting backtest simulation...")
            
            # Reset state
            self._trades = []
            self._equity_curve = []
            current_capital = self.config.initial_capital
            
            # Add initial equity point
            self._equity_curve.append((self._candles[0].timestamp if self._candles else datetime.now().isoformat(), current_capital))
            
            # STEP 2: SIMULATION LOOP
            for i, candle in enumerate(self._candles):
                if i == 0:
                    continue  # Skip first candle for feature generation
                
                # Generate features from historical data using real feature engine
                features = self._generate_features(candle, i)
                
                if not features:
                    continue
                
                # Use real strategy engine
                decision = self.strategy_engine.decide_strategy(None, features)
                
                # Debug output
                print("[BACKTEST DEBUG]", {
                    "features": list(features.keys()) if isinstance(features, dict) else "invalid",
                    "decision": decision.strategy if hasattr(decision, 'strategy') else "invalid",
                    "confidence": getattr(decision, 'bias_confidence', 0.0)
                })
                
                # Create trade if signal is valid
                if decision.strategy != "NO_TRADE":
                    trade = self._create_backtest_trade(decision, features, candle)
                    if trade:
                        self._trades.append(trade)
                        
                        # Deduct commission and slippage
                        current_capital += trade.net_pnl
                        
                        # Update equity curve
                        self._equity_curve.append((candle.timestamp, current_capital))
                
                # Check for trade exits on each candle
                self._manage_open_trades(candle, current_capital)
            
            # Calculate final results
            result = self._calculate_backtest_results(current_capital)
            
            # Save results
            self._save_backtest_results(result)
            
            # Print results
            self._print_backtest_results(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Backtest failed: {e}")
            return self._get_default_result()
    
    def _generate_features(self, candle: HistoricalCandle, index: int) -> Optional[Dict[str, Any]]:
        """Generate features using real feature engine"""
        try:
            if index < 20:  # Need enough history
                return None
            
            # Get recent candles for additional features
            recent_candles = self._candles[max(0, index-20):index]
            recent_high = max(c.high for c in recent_candles)
            recent_low = min(c.low for c in recent_candles)
            avg_volume = statistics.mean([c.volume for c in recent_candles])
            
            # Create mock option chain snapshot from historical data
            option_chain_snapshot = self._create_mock_option_chain(candle, index)
            
            # Use real feature engine
            feature_snapshot = self.feature_engine.compute_features(option_chain_snapshot, candle.close)
            
            # Extract OI distribution from mock option chain
            call_oi_distribution = {}
            put_oi_distribution = {}
            oi_change_calls = 0
            oi_change_puts = 0
            
            for strike, data in option_chain_snapshot.strikes.items():
                if 'CE' in data:
                    call_oi_distribution[strike] = data['CE']['oi']
                    oi_change_calls += data['CE']['change_oi']
                if 'PE' in data:
                    put_oi_distribution[strike] = data['PE']['oi']
                    oi_change_puts += data['PE']['change_oi']
            
            # Convert FeatureSnapshot to dict for compatibility with strategy engine
            features = {
                'spot': feature_snapshot.spot,
                'recent_high': recent_high,
                'recent_low': recent_low,
                'volume': candle.volume,
                'avg_volume': avg_volume,
                'gex_profile': feature_snapshot.gex_profile,
                'gamma_flip_probability': feature_snapshot.gamma_flip_probability,
                'call_wall_strength': feature_snapshot.call_wall_strength,
                'put_wall_strength': feature_snapshot.put_wall_strength,
                'call_wall_strike': feature_snapshot.call_wall_strike,
                'put_wall_strike': feature_snapshot.put_wall_strike,
                'pcr_trend': feature_snapshot.pcr_trend,
                'oi_concentration': feature_snapshot.oi_concentration,
                'oi_buildup_rate': feature_snapshot.oi_buildup_rate,
                'call_oi_distribution': call_oi_distribution,
                'put_oi_distribution': put_oi_distribution,
                'oi_change_calls': oi_change_calls,
                'oi_change_puts': oi_change_puts,
                'iv': 0.2,  # Default IV
                'volatility': 0.2,  # Default volatility
                'timestamp': candle.timestamp
            }
            
            return features
            
        except Exception as e:
            logger.error(f"Feature generation failed: {e}")
            return None
    
    def _create_mock_option_chain(self, candle: HistoricalCandle, index: int) -> MockOptionChainSnapshot:
        """Create mock option chain snapshot from historical data"""
        try:
            spot = candle.close
            
            # Generate strikes around ATM
            atm_strike = round(spot / 100) * 100  # Round to nearest 100
            strikes = []
            for i in range(-10, 11):  # 10 strikes above and below ATM
                strikes.append(atm_strike + (i * 100))
            
            # Generate mock option data
            strikes_data = {}
            
            for strike in strikes:
                # Generate realistic option prices based on distance from ATM
                distance = abs(strike - spot)
                time_value = max(0.1, distance * 0.002)  # Simple time value calc
                
                # CE option
                ce_price = max(0.05, spot - strike + time_value) if strike <= spot else time_value
                ce_oi = max(100, int(10000 / (1 + distance * 0.1)))
                ce_gamma = max(0.001, 0.01 / (1 + distance * 0.01))  # Mock gamma
                
                # PE option
                pe_price = max(0.05, strike - spot + time_value) if strike >= spot else time_value
                pe_oi = max(100, int(15000 / (1 + distance * 0.1)))
                pe_gamma = max(0.001, 0.01 / (1 + distance * 0.01))  # Mock gamma
                
                strikes_data[strike] = {
                    'CE': {
                        'strike': strike,
                        'ltp': ce_price,
                        'oi': ce_oi,
                        'volume': int(ce_oi * 0.1),
                        'change_oi': np.random.randint(-500, 500),
                        'gamma': ce_gamma
                    },
                    'PE': {
                        'strike': strike,
                        'ltp': pe_price,
                        'oi': pe_oi,
                        'volume': int(pe_oi * 0.1),
                        'change_oi': np.random.randint(-500, 500),
                        'gamma': pe_gamma
                    }
                }
            
            return MockOptionChainSnapshot(
                spot=spot,
                timestamp=candle.timestamp,
                strikes=strikes_data,
                expiry='2024-01-31',  # Mock expiry
                symbol='NIFTY'
            )
            
        except Exception as e:
            logger.error(f"Failed to create mock option chain: {e}")
            return MockOptionChainSnapshot(
                spot=candle.close,
                timestamp=candle.timestamp,
                strikes={},
                expiry='2024-01-31',
                symbol='NIFTY'
            )
    
    def _create_backtest_trade(self, decision, features: Dict[str, Any], candle: HistoricalCandle) -> Optional[BacktestTrade]:
        """Create backtest trade with real costs"""
        try:
            # Get trade parameters
            spot = features.get("spot", candle.close)
            call_wall = features.get("call_wall_strike")
            put_wall = features.get("put_wall_strike")
            
            # Use defaults if walls are None (same as strategy engine)
            if not call_wall:
                call_wall = spot + 200
            if not put_wall:
                put_wall = spot - 200
            
            # Calculate stop loss and target
            buffer = spot * self.config.slippage_percent * 10  # Larger buffer for stops
            
            if decision.strategy == "BUY":
                stop_loss = put_wall - buffer
                target = call_wall
                direction = 1
            elif decision.strategy == "SELL":
                stop_loss = call_wall + buffer
                target = put_wall
                direction = -1
            else:
                return None
            
            # Calculate position size (simplified risk management)
            risk_per_trade = self.config.initial_capital * 0.01  # 1% risk
            risk_per_unit = abs(spot - stop_loss)
            position_size = risk_per_trade / risk_per_unit if risk_per_unit > 0 else 1
            
            # STEP 3: ADD REAL COSTS
            # Apply slippage to entry price
            slippage_cost = spot * self.config.slippage_percent
            adjusted_entry_price = spot + (slippage_cost * direction)
            
            # Calculate commission
            commission = self.config.brokerage_per_trade
            
            trade = BacktestTrade(
                entry_time=candle.timestamp,
                exit_time="",  # Will be set on exit
                action=decision.strategy,
                entry_price=adjusted_entry_price,
                exit_price=0.0,  # Will be set on exit
                position_size=position_size,
                pnl=0.0,  # Will be calculated on exit
                commission=commission,
                slippage=slippage_cost,
                net_pnl=-commission - slippage_cost,  # Initial cost
                result="OPEN",
                exit_reason="OPEN"
            )
            
            return trade
            
        except Exception as e:
            logger.error(f"Trade creation failed: {e}")
            return None
    
    def _manage_open_trades(self, candle: HistoricalCandle, current_capital: float) -> None:
        """Manage and exit open trades based on candle data"""
        trades_to_close = []
        
        for trade in self._trades:
            if trade.result != "OPEN":
                continue
            
            try:
                # Check exit conditions
                should_exit = False
                exit_price = 0.0
                exit_reason = ""
                
                if trade.action == "BUY":
                    if candle.low <= trade.entry_price * 0.98:  # 2% stop loss
                        exit_price = candle.low
                        exit_reason = "STOP_LOSS"
                        should_exit = True
                    elif candle.high >= trade.entry_price * 1.03:  # 3% target
                        exit_price = candle.high
                        exit_reason = "TARGET_HIT"
                        should_exit = True
                
                elif trade.action == "SELL":
                    if candle.high >= trade.entry_price * 1.02:  # 2% stop loss
                        exit_price = candle.high
                        exit_reason = "STOP_LOSS"
                        should_exit = True
                    elif candle.low <= trade.entry_price * 0.97:  # 3% target
                        exit_price = candle.low
                        exit_reason = "TARGET_HIT"
                        should_exit = True
                
                if should_exit:
                    # Apply slippage to exit
                    slippage_cost = exit_price * self.config.slippage_percent
                    adjusted_exit_price = exit_price - (slippage_cost * (1 if trade.action == "SELL" else -1))
                    
                    # Calculate P&L
                    direction = 1 if trade.action == "BUY" else -1
                    gross_pnl = (adjusted_exit_price - trade.entry_price) * direction * trade.position_size
                    
                    # Total costs
                    total_commission = trade.commission * 2  # Entry + exit
                    total_slippage = trade.slippage + slippage_cost
                    
                    # Net P&L
                    net_pnl = gross_pnl - total_commission - total_slippage
                    result = "WIN" if net_pnl > 0 else "LOSS"
                    
                    # Update trade
                    trade.exit_time = candle.timestamp
                    trade.exit_price = adjusted_exit_price
                    trade.pnl = gross_pnl
                    trade.net_pnl = net_pnl
                    trade.result = result
                    trade.exit_reason = exit_reason
                    
                    trades_to_close.append(trade)
                    
            except Exception as e:
                logger.error(f"Trade management failed: {e}")
    
    def _calculate_backtest_results(self, final_capital: float) -> BacktestResult:
        """Calculate comprehensive backtest results"""
        try:
            # Basic metrics
            total_trades = len(self._trades)
            completed_trades = [t for t in self._trades if t.result in ["WIN", "LOSS"]]
            winning_trades = len([t for t in completed_trades if t.result == "WIN"])
            losing_trades = len([t for t in completed_trades if t.result == "LOSS"])
            
            win_rate = winning_trades / len(completed_trades) if completed_trades else 0.0
            
            # P&L calculations
            total_pnl = sum(t.pnl for t in completed_trades)
            total_commission = sum(t.commission * 2 for t in completed_trades)  # Entry + exit
            total_slippage = sum(t.slippage for t in completed_trades) + sum(abs(t.exit_price - t.entry_price) * self.config.slippage_percent for t in completed_trades if t.exit_price > 0)
            net_pnl = sum(t.net_pnl for t in completed_trades)
            
            # STEP 5: METRICS
            # Profit factor
            gross_wins = sum(t.net_pnl for t in completed_trades if t.result == "WIN")
            gross_losses = abs(sum(t.net_pnl for t in completed_trades if t.result == "LOSS"))
            profit_factor = gross_wins / gross_losses if gross_losses > 0 else 0.0
            
            # Max drawdown from equity curve
            equity_values = [equity for _, equity in self._equity_curve]
            peak = equity_values[0] if equity_values else self.config.initial_capital
            max_drawdown = 0.0
            
            for equity in equity_values[1:]:
                if equity > peak:
                    peak = equity
                drawdown = peak - equity
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
            
            # Sharpe ratio (simplified)
            if len(equity_values) > 1:
                returns = [(equity_values[i] - equity_values[i-1]) / equity_values[i-1] for i in range(1, len(equity_values))]
                avg_return = statistics.mean(returns) if returns else 0
                std_return = statistics.stdev(returns) if len(returns) > 1 else 0
                sharpe_ratio = (avg_return / std_return) * (252**0.5) if std_return > 0 else 0.0  # Annualized
            else:
                sharpe_ratio = 0.0
            
            return BacktestResult(
                total_trades=total_trades,
                winning_trades=winning_trades,
                losing_trades=losing_trades,
                win_rate=win_rate,
                total_pnl=total_pnl,
                total_commission=total_commission,
                total_slippage=total_slippage,
                net_pnl=net_pnl,
                max_drawdown=max_drawdown,
                profit_factor=profit_factor,
                sharpe_ratio=sharpe_ratio,
                equity_curve=self._equity_curve,
                final_capital=final_capital
            )
            
        except Exception as e:
            logger.error(f"Results calculation failed: {e}")
            return self._get_default_result()
    
    def _save_backtest_results(self, result: BacktestResult) -> None:
        """Save backtest results to file"""
        try:
            # Save trades
            trades_file = self.data_dir / "backtest_trades.jsonl"
            with open(trades_file, 'w') as f:
                for trade in self._trades:
                    f.write(json.dumps(asdict(trade), default=str) + "\n")
            
            # Save results summary
            with open(self.backtest_results_file, 'w') as f:
                json.dump(asdict(result), f, indent=2, default=str)
            
            # Save equity curve
            equity_file = self.data_dir / "equity_curve.json"
            with open(equity_file, 'w') as f:
                json.dump(result.equity_curve, f, indent=2, default=str)
            
            logger.info(f"Backtest results saved to {self.data_dir}")
            
        except Exception as e:
            logger.error(f"Failed to save results: {e}")
    
    def _print_backtest_results(self, result: BacktestResult) -> None:
        """Print backtest results in required format"""
        print("\n" + "="*60)
        print("[BACKTEST RESULT]")
        print(f"win_rate: {result.win_rate:.3f}")
        print(f"total_pnl: {result.total_pnl:.2f}")
        print(f"max_drawdown: {result.max_drawdown:.2f}")
        print(f"profit_factor: {result.profit_factor:.2f}")
        print(f"sharpe_ratio: {result.sharpe_ratio:.2f}")
        print(f"total_trades: {result.total_trades}")
        print(f"winning_trades: {result.winning_trades}")
        print(f"net_pnl: {result.net_pnl:.2f}")
        print(f"total_commission: {result.total_commission:.2f}")
        print(f"total_slippage: {result.total_slippage:.2f}")
        print(f"final_capital: {result.final_capital:.2f}")
        print("="*60)
    
    def _get_default_result(self) -> BacktestResult:
        """Get default backtest result"""
        return BacktestResult(
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate=0.0,
            total_pnl=0.0,
            total_commission=0.0,
            total_slippage=0.0,
            net_pnl=0.0,
            max_drawdown=0.0,
            profit_factor=0.0,
            sharpe_ratio=0.0,
            equity_curve=[],
            final_capital=self.config.initial_capital
        )

# Global instance for application-wide use
backtest_engine = BacktestEngine()
