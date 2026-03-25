"""
Trade Execution Engine for StrikeIQ
Handles real trade execution with entry, exit, trailing stop loss, and position management
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)

@dataclass
class ActiveTrade:
    symbol: str
    signal: str
    entry: float
    stop_loss: float
    target: float
    quantity: int
    status: str = "OPEN"
    trailing_sl: Optional[float] = None
    entry_time: Optional[float] = None
    exit_time: Optional[float] = None
    exit_price: Optional[float] = None
    pnl: float = 0.0
    metadata: Optional[Dict[str, Any]] = None


class TradeExecutionEngine:
    """
    Real trade execution engine with position management
    Handles entry, exit, trailing stop loss, and trade lifecycle
    """

    def __init__(self):
        self.active_trade: Optional[ActiveTrade] = None
        self.trade_history: List[ActiveTrade] = []
        self.total_trades: int = 0
        self.winning_trades: int = 0
        self.losing_trades: int = 0
        
        # 🔥 STEP 1: ADD STRATEGY WEIGHTS
        self.strategy_weights = {
            "TREND": 1.0,
            "REVERSAL": 1.0,
            "WEAK_TREND": 0.5,
            "RANGE": 1.0,
            "NONE": 0.0
        }

    def normalize_weights(self):
        """
        🔥 STEP 3: NORMALIZE WEIGHTS
        Ensures all weights sum to 1.0 for fair comparison
        
        Returns:
            None (modifies in-place)
        """
        total = sum(self.strategy_weights.values())
        if total > 0:
            for k in self.strategy_weights:
                self.strategy_weights[k] /= total

    # ---------------- ENTRY ----------------
    def try_enter(self, signal_data: Dict[str, Any]) -> Optional[ActiveTrade]:
        """
        Try to enter a new trade based on signal data
        
        Args:
            signal_data: Dictionary containing trade signal information
            
        Returns:
            ActiveTrade object if trade entered, None otherwise
        """
        try:
            # 🚫 RULE 4: NO FORCE TRADE
            if signal_data.get("signal") == "NONE":
                logger.info("[NO TRADE] Signal is NONE, skipping entry")
                return None

            # Check if already in trade
            if self.active_trade and self.active_trade.status == "OPEN":
                logger.info("[SKIP ENTRY] Already in active trade")
                return None

            # Validate required fields
            required_fields = ["symbol", "signal", "entry", "stop_loss", "target"]
            for field in required_fields:
                if field not in signal_data:
                    logger.error(f"[ENTRY ERROR] Missing required field: {field}")
                    return None

            # Validate trade logic
            entry = signal_data["entry"]
            stop_loss = signal_data["stop_loss"]
            target = signal_data["target"]
            
            if entry <= 0 or stop_loss <= 0 or target <= 0:
                logger.error(f"[ENTRY ERROR] Invalid prices: entry={entry}, sl={stop_loss}, target={target}")
                return None

            # Create new trade
            import time
            trade = ActiveTrade(
                symbol=signal_data["symbol"],
                signal=signal_data["signal"],
                entry=entry,
                stop_loss=stop_loss,
                target=target,
                quantity=signal_data.get("quantity", 1),
                entry_time=time.time(),
                metadata={
                    "strategy": signal_data.get("strategy", "UNKNOWN"),
                    "confidence": signal_data.get("confidence", 0.0),
                    "regime": signal_data.get("regime", "UNKNOWN")
                }
            )

            self.active_trade = trade
            self.total_trades += 1
            
            logger.info(f"[TRADE ENTERED] {trade.signal} @ {trade.entry}")
            logger.info(f"[TRADE DETAILS] SL={trade.stop_loss}, Target={trade.target}")
            
            return trade

        except Exception as e:
            logger.error(f"[ENTRY ERROR] {e}")
            return None

    # ---------------- MANAGEMENT ----------------
    def manage_trade(self, current_price: float) -> Optional[str]:
        """
        Manage active trade with stop loss, target, and trailing stop
        
        Args:
            current_price: Current market price
            
        Returns:
            Trade status: "TARGET_HIT", "STOP_LOSS", "TRAILING_SL", "HOLD", or None
        """
        try:
            trade = self.active_trade
            if not trade or trade.status != "OPEN":
                return None

            # Calculate PnL
            if trade.signal == "BUY_CALL":
                pnl = (current_price - trade.entry) / trade.entry
            else:  # BUY_PUT
                pnl = (trade.entry - current_price) / trade.entry

            # 🔥 TARGET HIT
            if trade.signal == "BUY_CALL" and current_price >= trade.target:
                return self._close_trade("TARGET_HIT", current_price, pnl)
            elif trade.signal == "BUY_PUT" and current_price <= trade.target:
                return self._close_trade("TARGET_HIT", current_price, pnl)

            # 🔥 STOP LOSS
            if trade.signal == "BUY_CALL" and current_price <= trade.stop_loss:
                return self._close_trade("STOP_LOSS", current_price, pnl)
            elif trade.signal == "BUY_PUT" and current_price >= trade.stop_loss:
                return self._close_trade("STOP_LOSS", current_price, pnl)

            # 🔥 TRAILING SL (LOCK PROFIT)
            # Check trailing SL hit first (if already set)
            if trade.trailing_sl:
                # CALL
                if trade.signal == "BUY_CALL" and current_price <= trade.trailing_sl:
                    return self._close_trade("TRAILING_SL", current_price, pnl)
                # PUT
                if trade.signal == "BUY_PUT" and current_price >= trade.trailing_sl:
                    return self._close_trade("TRAILING_SL", current_price, pnl)
            
            # Set trailing SL if profit threshold reached
            if pnl >= 0.2:  # 20% profit trigger trailing SL (>= to be inclusive)
                # Initialize trailing SL only once
                if trade.trailing_sl is None:
                    trade.trailing_sl = trade.entry * 0.9
                
                # Update trailing SL only if price moves in favor
                if trade.signal == "BUY_CALL":
                    new_sl = current_price * 0.9
                    trade.trailing_sl = max(trade.trailing_sl, new_sl)
                elif trade.signal == "BUY_PUT":
                    new_sl = current_price * 1.1
                    trade.trailing_sl = min(trade.trailing_sl, new_sl)
                
                logger.info(f"[TRAILING SL UPDATED] Entry: {trade.entry}, Current: {current_price}, Trailing SL: {trade.trailing_sl}")

            return "HOLD"

        except Exception as e:
            logger.error(f"[MANAGEMENT ERROR] {e}")
            return None

    def _close_trade(self, reason: str, exit_price: float, pnl: float) -> str:
        """
        Internal method to close trade and update statistics
        
        Args:
            reason: Reason for closing trade
            exit_price: Exit price
            pnl: Profit/Loss percentage
            
        Returns:
            Close reason string
        """
        import time
        
        if self.active_trade:
            trade = self.active_trade
            trade.status = "CLOSED"
            trade.exit_price = exit_price
            trade.exit_time = time.time()

            # 🔥 STEP 3: PnL calc
            if trade.signal == "BUY_CALL":
                trade.pnl = (exit_price - trade.entry)
            elif trade.signal == "BUY_PUT":
                trade.pnl = (trade.entry - exit_price)

            # Update statistics
            if trade.pnl > 0:
                self.winning_trades += 1
            else:
                self.losing_trades += 1
            
            # Add to history
            self.trade_history.append(trade)
            
            # 🔥 STEP 2: UPDATE WEIGHTS AFTER EACH TRADE
            strategy = trade.metadata.get("strategy", "UNKNOWN") if trade.metadata else "UNKNOWN"
            
            if strategy in self.strategy_weights:
                if trade.pnl > 0:
                    self.strategy_weights[strategy] *= 1.05  # reward profitable strategy
                    logger.info(f"[STRATEGY REWARD] {strategy} weight increased to {self.strategy_weights[strategy]:.3f}")
                else:
                    self.strategy_weights[strategy] *= 0.95  # punish losing strategy
                    logger.info(f"[STRATEGY PUNISH] {strategy} weight decreased to {self.strategy_weights[strategy]:.3f}")
                
                # 🔥 STEP 3: NORMALIZE WEIGHTS
                self.normalize_weights()
            
            # 🔥 STEP 5: LOG AFTER EVERY EXIT
            perf = self.get_performance()
            logger.info(f"[PERF] Trades={perf['total_trades']} | WinRate={perf['win_rate']:.2f}% | PnL={perf['total_pnl']:.2f}")
            
            logger.info(f"[TRADE EXIT] {reason} @ {exit_price}, PnL: {trade.pnl:.2f}")
            
            # Clear active trade
            self.active_trade = None
            
        return reason

    def get_performance(self) -> Dict[str, Any]:
        """
        🔥 STEP 4: Get performance metrics
        
        Returns:
            Dictionary with comprehensive performance statistics
        """
        total = len(self.trade_history)
        
        wins = len([t for t in self.trade_history if t.pnl > 0])
        losses = len([t for t in self.trade_history if t.pnl <= 0])
        
        total_pnl = sum([t.pnl for t in self.trade_history])
        
        win_rate = (wins / total * 100) if total > 0 else 0
        
        # Additional metrics
        avg_win = sum([t.pnl for t in self.trade_history if t.pnl > 0]) / wins if wins > 0 else 0
        avg_loss = sum([t.pnl for t in self.trade_history if t.pnl <= 0]) / losses if losses > 0 else 0
        
        return {
            "total_trades": total,
            "wins": wins,
            "losses": losses,
            "win_rate": win_rate,
            "total_pnl": total_pnl,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "profit_factor": abs(avg_win / avg_loss) if avg_loss != 0 else 0
        }
    
    def get_equity_curve(self) -> List[float]:
        """
        🔥 STEP 1: Calculate equity curve over time
        Shows cumulative PnL progression
        
        Returns:
            List of cumulative equity values
        """
        equity = 0
        curve = []

        for trade in self.trade_history:
            equity += trade.pnl
            curve.append(equity)

        return curve
    
    def get_drawdown(self) -> float:
        """
        🔥 STEP 2: Calculate maximum drawdown
        Maximum loss from peak equity
        
        Returns:
            Maximum drawdown value
        """
        peak = 0
        max_dd = 0
        equity = 0

        for trade in self.trade_history:
            equity += trade.pnl
            peak = max(peak, equity)
            dd = peak - equity
            max_dd = max(max_dd, dd)

        return max_dd
    
    def get_strategy_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        🔥 STEP 3: Get performance by strategy
        Analyzes performance per strategy type
        
        Returns:
            Dictionary with strategy-wise statistics
        """
        stats = {}

        for trade in self.trade_history:
            # Get strategy from metadata if available
            strategy = "UNKNOWN"
            if hasattr(trade, 'metadata') and trade.metadata:
                strategy = trade.metadata.get("strategy", "UNKNOWN")
            elif hasattr(trade, 'strategy'):
                strategy = trade.strategy

            if strategy not in stats:
                stats[strategy] = {"wins": 0, "losses": 0, "pnl": 0, "trades": 0}

            stats[strategy]["trades"] += 1
            
            if trade.pnl > 0:
                stats[strategy]["wins"] += 1
            else:
                stats[strategy]["losses"] += 1

            stats[strategy]["pnl"] += trade.pnl
            
            # Calculate win rate for strategy
            if stats[strategy]["trades"] > 0:
                stats[strategy]["win_rate"] = (stats[strategy]["wins"] / stats[strategy]["trades"]) * 100
            else:
                stats[strategy]["win_rate"] = 0

        return stats
    
    def get_full_analytics(self) -> Dict[str, Any]:
        """
        🔥 STEP 4: Get comprehensive analytics
        Combines all performance metrics into single output
        
        Returns:
            Dictionary with complete analytics data
        """
        base_performance = self.get_performance()
        
        return {
            **base_performance,
            "equity_curve": self.get_equity_curve(),
            "max_drawdown": self.get_drawdown(),
            "strategy_stats": self.get_strategy_stats(),
            "current_equity": sum(trade.pnl for trade in self.trade_history),
            "peak_equity": max(self.get_equity_curve()) if self.get_equity_curve() else 0
        }
    
    def get_trade_status(self) -> Dict[str, Any]:
        """
        Get current trade status and statistics
        
        Returns:
            Dictionary with trade status and performance metrics
        """
        performance = self.get_performance()
        
        status = {
            "active_trade": None,
            "performance": performance,
            "total_trades": performance["total_trades"],
            "winning_trades": performance["wins"],
            "losing_trades": performance["losses"],
            "win_rate": performance["win_rate"]
        }
        
        if self.active_trade:
            status["active_trade"] = {
                "symbol": self.active_trade.symbol,
                "signal": self.active_trade.signal,
                "entry": self.active_trade.entry,
                "stop_loss": self.active_trade.stop_loss,
                "target": self.active_trade.target,
                "trailing_sl": self.active_trade.trailing_sl,
                "status": self.active_trade.status,
                "entry_time": self.active_trade.entry_time,
                "pnl": self.active_trade.pnl
            }
        
        return status

    def reset(self):
        """Reset all trades and statistics"""
        self.active_trade = None
        self.trade_history = []
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        logger.info("[TRADE ENGINE RESET] All trades cleared")
