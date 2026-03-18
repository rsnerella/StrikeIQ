"""
Risk Management + Position Sizing + Exit Engine for StrikeIQ
Transforms system into full trade lifecycle engine with capital protection.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import json
import logging
import os
from pathlib import Path
import statistics

logger = logging.getLogger(__name__)

@dataclass
class TradeConfig:
    """Trade management configuration"""
    account_size: float = 100000.0  # Default account size
    risk_per_trade_percent: float = 0.01  # 1% risk per trade
    max_position_percent: float = 0.1  # 10% max position size
    minimum_tick: float = 0.01  # Minimum price movement
    max_hold_time_hours: float = 24.0  # Maximum hold time
    buffer_percent: float = 0.002  # 0.2% buffer for stops/targets

@dataclass
class Trade:
    """Active trade object"""
    timestamp: str
    action: str  # BUY or SELL
    entry_price: float
    confidence: float
    probability: float
    entry_type: str
    stop_loss: float
    target: float
    position_size: float
    risk_amount: float
    direction: int  # +1 for BUY, -1 for SELL

@dataclass
class TradeResult:
    """Completed trade result"""
    timestamp: str
    entry_timestamp: str
    action: str
    entry_price: float
    exit_price: float
    position_size: float
    pnl: float
    pnl_percent: float
    result: str  # WIN, LOSS
    exit_reason: str  # STOP_LOSS, TARGET_HIT, TIME_EXIT
    duration_minutes: float
    confidence: float
    entry_type: str

@dataclass
class RiskMetrics:
    """Risk management metrics"""
    total_trades: int
    winning_trades: int
    losing_trades: int
    total_pnl: float
    max_drawdown: float
    avg_win: float
    avg_loss: float
    risk_reward_ratio: float
    win_rate: float
    current_drawdown: float

class TradeManager:
    """Risk management and position sizing engine"""
    
    def __init__(self, config: Optional[TradeConfig] = None, data_dir: str = "data/trades"):
        self.config = config or TradeConfig()
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.active_trades_file = self.data_dir / "active_trades.json"
        self.trade_results_file = self.data_dir / "trade_results.jsonl"
        self.risk_metrics_file = self.data_dir / "risk_metrics.json"
        
        # In-memory storage
        self._active_trades: List[Trade] = []
        self._trade_results: List[TradeResult] = []
        self._risk_metrics: Optional[RiskMetrics] = None
        
        logger.info(f"TradeManager initialized with account_size: {self.config.account_size}")
    
    def create_trade(self, strategy_decision, features: Dict[str, Any]) -> Optional[Trade]:
        """Create trade from strategy decision with risk management"""
        try:
            # Only create trades for valid actions
            if strategy_decision.strategy == "NO_TRADE":
                logger.debug("Skipping NO_TRADE signal")
                return None
            
            # Extract required data
            spot = features.get("spot", 0)
            call_wall = features.get("call_wall_strike", 0)
            put_wall = features.get("put_wall_strike", 0)
            confidence = strategy_decision.bias_confidence
            probability = strategy_decision.execution_probability
            entry_signal = strategy_decision.metadata.get("entry", "WAIT") if strategy_decision.metadata else "WAIT"
            
            if spot <= 0 or call_wall <= 0 or put_wall <= 0:
                logger.warning("Invalid price data for trade creation")
                return None
            
            # STEP 2: DEFINE STOP LOSS + TARGET
            buffer = spot * self.config.buffer_percent
            
            if strategy_decision.strategy == "BUY":
                stop_loss = put_wall - buffer
                target = call_wall
                direction = 1
            elif strategy_decision.strategy == "SELL":
                stop_loss = call_wall + buffer
                target = put_wall
                direction = -1
            else:
                logger.warning(f"Unknown action: {strategy_decision.strategy}")
                return None
            
            # Ensure valid distances
            risk_per_unit = abs(spot - stop_loss)
            if risk_per_unit < self.config.minimum_tick:
                logger.warning(f"Risk per unit too small: {risk_per_unit}")
                return None
            
            # STEP 3: POSITION SIZING (RISK BASED)
            risk_per_trade = self.config.account_size * self.config.risk_per_trade_percent
            position_size = risk_per_trade / risk_per_unit
            
            # Cap max exposure
            max_position = self.config.account_size * self.config.max_position_percent
            position_size = min(position_size, max_position)
            
            # Calculate actual risk amount
            risk_amount = risk_per_unit * position_size
            
            # Create trade object
            trade = Trade(
                timestamp=datetime.utcnow().isoformat(),
                action=strategy_decision.strategy,
                entry_price=spot,
                confidence=confidence,
                probability=probability,
                entry_type=entry_signal,
                stop_loss=stop_loss,
                target=target,
                position_size=position_size,
                risk_amount=risk_amount,
                direction=direction
            )
            
            logger.info(f"Created {trade.action} trade: entry={trade.entry_price}, "
                       f"stop={trade.stop_loss}, target={trade.target}, size={trade.position_size}")
            
            return trade
            
        except Exception as e:
            logger.error(f"Failed to create trade: {e}")
            return None
    
    def execute_trade(self, trade: Trade) -> bool:
        """Execute and store active trade"""
        try:
            self._active_trades.append(trade)
            self.save_active_trades()
            
            # Debug output
            print("[TRADE ENGINE]", {
                "action": trade.action,
                "entry": trade.entry_price,
                "stop_loss": trade.stop_loss,
                "target": trade.target,
                "size": trade.position_size,
                "risk_amount": trade.risk_amount,
                "confidence": trade.confidence
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to execute trade: {e}")
            return False
    
    def manage_trades(self, current_price: float) -> List[TradeResult]:
        """Manage active trades and check for exits"""
        results = []
        trades_to_remove = []
        
        for trade in self._active_trades:
            try:
                result = self._check_trade_exit(trade, current_price)
                
                if result:
                    results.append(result)
                    trades_to_remove.append(trade)
                    
            except Exception as e:
                logger.error(f"Failed to manage trade {trade.timestamp}: {e}")
        
        # Remove completed trades
        for trade in trades_to_remove:
            self._active_trades.remove(trade)
        
        # Save results
        for result in results:
            self._trade_results.append(result)
            self.save_trade_result(result)
        
        # Update active trades file
        if trades_to_remove:
            self.save_active_trades()
        
        return results
    
    def _check_trade_exit(self, trade: Trade, current_price: float) -> Optional[TradeResult]:
        """Check if trade should be exited"""
        try:
            # Check time-based exit
            entry_time = datetime.fromisoformat(trade.timestamp)
            current_time = datetime.utcnow()
            duration_minutes = (current_time - entry_time).total_seconds() / 60
            
            if duration_minutes > (self.config.max_hold_time_hours * 60):
                return self._create_trade_result(trade, current_price, "TIME_EXIT", duration_minutes)
            
            # Check price-based exits
            if trade.action == "BUY":
                if current_price <= trade.stop_loss:
                    return self._create_trade_result(trade, current_price, "STOP_LOSS", duration_minutes)
                elif current_price >= trade.target:
                    return self._create_trade_result(trade, current_price, "TARGET_HIT", duration_minutes)
            
            elif trade.action == "SELL":
                if current_price >= trade.stop_loss:
                    return self._create_trade_result(trade, current_price, "STOP_LOSS", duration_minutes)
                elif current_price <= trade.target:
                    return self._create_trade_result(trade, current_price, "TARGET_HIT", duration_minutes)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to check trade exit: {e}")
            return None
    
    def _create_trade_result(self, trade: Trade, exit_price: float, exit_reason: str, duration_minutes: float) -> TradeResult:
        """Create trade result from exit"""
        # STEP 7: P&L CALCULATION
        pnl = (exit_price - trade.entry_price) * trade.direction * trade.position_size
        pnl_percent = (pnl / (trade.entry_price * trade.position_size)) * 100 if trade.entry_price > 0 else 0
        
        # Determine result
        result = "WIN" if pnl > 0 else "LOSS"
        
        return TradeResult(
            timestamp=datetime.utcnow().isoformat(),
            entry_timestamp=trade.timestamp,
            action=trade.action,
            entry_price=trade.entry_price,
            exit_price=exit_price,
            position_size=trade.position_size,
            pnl=pnl,
            pnl_percent=pnl_percent,
            result=result,
            exit_reason=exit_reason,
            duration_minutes=duration_minutes,
            confidence=trade.confidence,
            entry_type=trade.entry_type
        )
    
    def calculate_risk_metrics(self) -> RiskMetrics:
        """Calculate risk management metrics"""
        try:
            if not self._trade_results:
                return self._get_default_risk_metrics()
            
            # Basic metrics
            total_trades = len(self._trade_results)
            winning_trades = len([r for r in self._trade_results if r.result == "WIN"])
            losing_trades = len([r for r in self._trade_results if r.result == "LOSS"])
            total_pnl = sum(r.pnl for r in self._trade_results)
            
            # Win/Loss averages
            wins = [r.pnl for r in self._trade_results if r.result == "WIN"]
            losses = [r.pnl for r in self._trade_results if r.result == "LOSS"]
            avg_win = statistics.mean(wins) if wins else 0.0
            avg_loss = statistics.mean(losses) if losses else 0.0
            
            # Win rate
            win_rate = winning_trades / total_trades if total_trades > 0 else 0.0
            
            # Risk/Reward ratio
            risk_reward_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else 0.0
            
            # Drawdown calculation
            cumulative_pnl = []
            running_total = 0
            for result in self._trade_results:
                running_total += result.pnl
                cumulative_pnl.append(running_total)
            
            peak = max(cumulative_pnl) if cumulative_pnl else 0
            current_drawdown = peak - (cumulative_pnl[-1] if cumulative_pnl else 0)
            max_drawdown = max([peak - x for x in cumulative_pnl]) if cumulative_pnl else 0.0
            
            metrics = RiskMetrics(
                total_trades=total_trades,
                winning_trades=winning_trades,
                losing_trades=losing_trades,
                total_pnl=total_pnl,
                max_drawdown=max_drawdown,
                avg_win=avg_win,
                avg_loss=avg_loss,
                risk_reward_ratio=risk_reward_ratio,
                win_rate=win_rate,
                current_drawdown=current_drawdown
            )
            
            self._risk_metrics = metrics
            self.save_risk_metrics()
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to calculate risk metrics: {e}")
            return self._get_default_risk_metrics()
    
    def get_active_trades(self) -> List[Trade]:
        """Get list of active trades"""
        return self._active_trades.copy()
    
    def get_trade_results(self) -> List[TradeResult]:
        """Get list of completed trade results"""
        return self._trade_results.copy()
    
    def print_risk_debug(self) -> None:
        """Print risk management debug output"""
        try:
            metrics = self.calculate_risk_metrics()
            
            print("[RISK METRICS]", {
                "total_trades": metrics.total_trades,
                "win_rate": round(metrics.win_rate, 3),
                "total_pnl": round(metrics.total_pnl, 2),
                "max_drawdown": round(metrics.max_drawdown, 2),
                "avg_win": round(metrics.avg_win, 2),
                "avg_loss": round(metrics.avg_loss, 2),
                "risk_reward_ratio": round(metrics.risk_reward_ratio, 2),
                "current_drawdown": round(metrics.current_drawdown, 2),
                "active_trades": len(self._active_trades)
            })
            
        except Exception as e:
            logger.error(f"Failed to print risk debug: {e}")
    
    def save_active_trades(self) -> None:
        """Save active trades to file"""
        try:
            trades_data = [asdict(trade) for trade in self._active_trades]
            with open(self.active_trades_file, "w") as f:
                json.dump(trades_data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save active trades: {e}")
    
    def save_trade_result(self, result: TradeResult) -> None:
        """Save trade result to file"""
        try:
            with open(self.trade_results_file, "a") as f:
                f.write(json.dumps(asdict(result), default=str) + "\n")
        except Exception as e:
            logger.error(f"Failed to save trade result: {e}")
    
    def save_risk_metrics(self) -> None:
        """Save risk metrics to file"""
        try:
            if self._risk_metrics:
                with open(self.risk_metrics_file, "w") as f:
                    json.dump(asdict(self._risk_metrics), f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save risk metrics: {e}")
    
    def load_historical_data(self) -> None:
        """Load historical trade data"""
        try:
            # Load active trades
            if self.active_trades_file.exists():
                with open(self.active_trades_file, "r") as f:
                    trades_data = json.load(f)
                    self._active_trades = [Trade(**data) for data in trades_data]
            
            # Load trade results
            if self.trade_results_file.exists():
                with open(self.trade_results_file, "r") as f:
                    for line in f:
                        if line.strip():
                            data = json.loads(line)
                            result = TradeResult(**data)
                            self._trade_results.append(result)
            
            # Load risk metrics
            if self.risk_metrics_file.exists():
                with open(self.risk_metrics_file, "r") as f:
                    metrics_data = json.load(f)
                    self._risk_metrics = RiskMetrics(**metrics_data)
            
            logger.info(f"Loaded {len(self._active_trades)} active trades and {len(self._trade_results)} trade results")
            
        except Exception as e:
            logger.error(f"Failed to load historical data: {e}")
    
    def _get_default_risk_metrics(self) -> RiskMetrics:
        """Get default risk metrics"""
        return RiskMetrics(
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            total_pnl=0.0,
            max_drawdown=0.0,
            avg_win=0.0,
            avg_loss=0.0,
            risk_reward_ratio=0.0,
            win_rate=0.0,
            current_drawdown=0.0
        )

# Global instance for application-wide use
trade_manager = TradeManager()
