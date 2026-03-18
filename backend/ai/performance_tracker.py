"""
Performance Tracking + Auto-Learning Layer for StrikeIQ
Tracks every AI decision and evaluates performance to improve system over time.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import json
import logging
import os
from pathlib import Path
import statistics

logger = logging.getLogger(__name__)

@dataclass
class TradeSignal:
    """Single trade signal record"""
    timestamp: str
    action: str
    confidence: float
    probability: float
    spot_price: float
    entry_signal: str
    reasoning: List[str]
    regime: str
    trap_detected: bool
    htf_bias: Optional[str] = None

@dataclass
class TradeOutcome:
    """Trade outcome evaluation"""
    timestamp: str
    original_signal: TradeSignal
    future_price: float
    result: str  # WIN, LOSS, SKIPPED
    price_change: float
    price_change_pct: float

@dataclass
class PerformanceMetrics:
    """Performance metrics summary"""
    total_trades: int
    winning_trades: int
    win_rate: float
    avg_confidence: float
    confidence_accuracy: float
    regime_performance: Dict[str, Dict[str, Any]]
    entry_performance: Dict[str, Dict[str, Any]]
    trap_performance: Dict[str, Dict[str, Any]]

class PerformanceTracker:
    """Performance tracking and auto-learning system"""
    
    def __init__(self, data_dir: str = "data/performance"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.signals_file = self.data_dir / "trade_signals.jsonl"
        self.outcomes_file = self.data_dir / "trade_outcomes.jsonl"
        self.metrics_file = self.data_dir / "performance_metrics.json"
        
        # In-memory cache for performance
        self._signals_cache: List[TradeSignal] = []
        self._outcomes_cache: List[TradeOutcome] = []
        self._metrics_cache: Optional[PerformanceMetrics] = None
        
        logger.info(f"PerformanceTracker initialized with data dir: {data_dir}")
    
    def store_signal(self, strategy_decision, features: Dict[str, Any]) -> None:
        """Store every trade signal for later evaluation"""
        try:
            signal = TradeSignal(
                timestamp=datetime.utcnow().isoformat(),
                action=strategy_decision.strategy,
                confidence=strategy_decision.bias_confidence,
                probability=strategy_decision.execution_probability,
                spot_price=features.get("spot", 0),
                entry_signal=strategy_decision.metadata.get("entry", "WAIT") if strategy_decision.metadata else "WAIT",
                reasoning=strategy_decision.reasoning,
                regime=strategy_decision.regime,
                trap_detected=strategy_decision.metadata.get("trap", False) if strategy_decision.metadata else False,
                htf_bias=features.get("htf_bias")
            )
            
            # Store in memory
            self._signals_cache.append(signal)
            
            # Append to file
            with open(self.signals_file, "a") as f:
                f.write(json.dumps(asdict(signal)) + "\n")
            
            logger.debug(f"Stored signal: {signal.action} at {signal.spot_price}")
            
        except Exception as e:
            logger.error(f"Failed to store signal: {e}")
    
    def evaluate_outcomes(self, current_price: float, evaluation_window_minutes: int = 5) -> List[TradeOutcome]:
        """Evaluate outcomes for signals in the evaluation window"""
        outcomes = []
        cutoff_time = datetime.utcnow() - timedelta(minutes=evaluation_window_minutes)
        
        # Find signals to evaluate
        signals_to_evaluate = [
            s for s in self._signals_cache 
            if datetime.fromisoformat(s.timestamp) < cutoff_time 
            and s.action in ["BUY", "SELL"]
        ]
        
        for signal in signals_to_evaluate:
            try:
                # Calculate result
                if signal.action == "BUY":
                    result = "WIN" if current_price > signal.spot_price else "LOSS"
                elif signal.action == "SELL":
                    result = "WIN" if current_price < signal.spot_price else "LOSS"
                else:
                    result = "SKIPPED"
                
                # Calculate price change
                price_change = current_price - signal.spot_price
                price_change_pct = (price_change / signal.spot_price) * 100 if signal.spot_price > 0 else 0
                
                outcome = TradeOutcome(
                    timestamp=datetime.utcnow().isoformat(),
                    original_signal=signal,
                    future_price=current_price,
                    result=result,
                    price_change=price_change,
                    price_change_pct=price_change_pct
                )
                
                outcomes.append(outcome)
                self._outcomes_cache.append(outcome)
                
                # Store to file
                with open(self.outcomes_file, "a") as f:
                    f.write(json.dumps(asdict(outcome)) + "\n")
                
                logger.debug(f"Evaluated outcome: {signal.action} -> {result} ({price_change_pct:.2f}%)")
                
            except Exception as e:
                logger.error(f"Failed to evaluate outcome for signal {signal.timestamp}: {e}")
        
        return outcomes
    
    def compute_metrics(self) -> PerformanceMetrics:
        """Compute performance metrics from historical data"""
        try:
            if not self._outcomes_cache:
                return PerformanceMetrics(
                    total_trades=0,
                    winning_trades=0,
                    win_rate=0.0,
                    avg_confidence=0.0,
                    confidence_accuracy=0.0,
                    regime_performance={},
                    entry_performance={},
                    trap_performance={}
                )
            
            # Basic metrics
            total_trades = len([o for o in self._outcomes_cache if o.original_signal.action in ["BUY", "SELL"]])
            winning_trades = len([o for o in self._outcomes_cache if o.result == "WIN"])
            win_rate = winning_trades / total_trades if total_trades > 0 else 0.0
            
            # Confidence metrics
            trade_outcomes = [o for o in self._outcomes_cache if o.original_signal.action in ["BUY", "SELL"]]
            avg_confidence = statistics.mean([o.original_signal.confidence for o in trade_outcomes]) if trade_outcomes else 0.0
            
            # Confidence accuracy (correlation between confidence and actual wins)
            confidence_accuracy = self._compute_confidence_accuracy(trade_outcomes)
            
            # Performance by regime
            regime_performance = self._compute_regime_performance(trade_outcomes)
            
            # Performance by entry type
            entry_performance = self._compute_entry_performance(trade_outcomes)
            
            # Performance by trap detection
            trap_performance = self._compute_trap_performance(trade_outcomes)
            
            metrics = PerformanceMetrics(
                total_trades=total_trades,
                winning_trades=winning_trades,
                win_rate=win_rate,
                avg_confidence=avg_confidence,
                confidence_accuracy=confidence_accuracy,
                regime_performance=regime_performance,
                entry_performance=entry_performance,
                trap_performance=trap_performance
            )
            
            self._metrics_cache = metrics
            
            # Save metrics to file
            with open(self.metrics_file, "w") as f:
                json.dump(asdict(metrics), f, indent=2, default=str)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to compute metrics: {e}")
            return self._get_default_metrics()
    
    def _compute_confidence_accuracy(self, trade_outcomes: List[TradeOutcome]) -> float:
        """Compute correlation between confidence and actual wins"""
        try:
            if len(trade_outcomes) < 2:
                return 0.0
            
            # Convert wins to 1, losses to 0
            actual_results = [1 if o.result == "WIN" else 0 for o in trade_outcomes]
            confidences = [o.original_signal.confidence for o in trade_outcomes]
            
            # Simple correlation: higher confidence should correlate with wins
            if len(set(actual_results)) < 2:  # All wins or all losses
                return 0.5
            
            # Compute correlation coefficient
            n = len(trade_outcomes)
            sum_actual = sum(actual_results)
            sum_conf = sum(confidences)
            sum_actual_sq = sum(x*x for x in actual_results)
            sum_conf_sq = sum(x*x for x in confidences)
            sum_products = sum(actual_results[i] * confidences[i] for i in range(n))
            
            numerator = n * sum_products - sum_actual * sum_conf
            denominator = ((n * sum_actual_sq - sum_actual**2) * (n * sum_conf_sq - sum_conf**2))**0.5
            
            if denominator == 0:
                return 0.0
            
            correlation = numerator / denominator
            return max(-1.0, min(1.0, correlation))
            
        except Exception as e:
            logger.error(f"Failed to compute confidence accuracy: {e}")
            return 0.0
    
    def _compute_regime_performance(self, trade_outcomes: List[TradeOutcome]) -> Dict[str, Dict[str, Any]]:
        """Compute performance by market regime"""
        regime_stats = {}
        
        for outcome in trade_outcomes:
            regime = outcome.original_signal.regime
            if regime not in regime_stats:
                regime_stats[regime] = {"trades": 0, "wins": 0, "total_confidence": 0}
            
            regime_stats[regime]["trades"] += 1
            if outcome.result == "WIN":
                regime_stats[regime]["wins"] += 1
            regime_stats[regime]["total_confidence"] += outcome.original_signal.confidence
        
        # Calculate rates
        for regime, stats in regime_stats.items():
            stats["win_rate"] = stats["wins"] / stats["trades"] if stats["trades"] > 0 else 0.0
            stats["avg_confidence"] = stats["total_confidence"] / stats["trades"] if stats["trades"] > 0 else 0.0
        
        return regime_stats
    
    def _compute_entry_performance(self, trade_outcomes: List[TradeOutcome]) -> Dict[str, Dict[str, Any]]:
        """Compute performance by entry type"""
        entry_stats = {}
        
        for outcome in trade_outcomes:
            entry = outcome.original_signal.entry_signal
            if entry not in entry_stats:
                entry_stats[entry] = {"trades": 0, "wins": 0, "total_confidence": 0}
            
            entry_stats[entry]["trades"] += 1
            if outcome.result == "WIN":
                entry_stats[entry]["wins"] += 1
            entry_stats[entry]["total_confidence"] += outcome.original_signal.confidence
        
        # Calculate rates
        for entry, stats in entry_stats.items():
            stats["win_rate"] = stats["wins"] / stats["trades"] if stats["trades"] > 0 else 0.0
            stats["avg_confidence"] = stats["total_confidence"] / stats["trades"] if stats["trades"] > 0 else 0.0
        
        return entry_stats
    
    def _compute_trap_performance(self, trade_outcomes: List[TradeOutcome]) -> Dict[str, Dict[str, Any]]:
        """Compute performance by trap detection"""
        trap_stats = {"trap_detected": {"trades": 0, "wins": 0, "total_confidence": 0},
                      "no_trap": {"trades": 0, "wins": 0, "total_confidence": 0}}
        
        for outcome in trade_outcomes:
            trap_key = "trap_detected" if outcome.original_signal.trap_detected else "no_trap"
            trap_stats[trap_key]["trades"] += 1
            if outcome.result == "WIN":
                trap_stats[trap_key]["wins"] += 1
            trap_stats[trap_key]["total_confidence"] += outcome.original_signal.confidence
        
        # Calculate rates
        for trap_key, stats in trap_stats.items():
            stats["win_rate"] = stats["wins"] / stats["trades"] if stats["trades"] > 0 else 0.0
            stats["avg_confidence"] = stats["total_confidence"] / stats["trades"] if stats["trades"] > 0 else 0.0
        
        return trap_stats
    
    def get_auto_tuning_suggestions(self) -> Dict[str, Any]:
        """Generate auto-tuning suggestions based on performance"""
        try:
            if not self._metrics_cache:
                return {}
            
            metrics = self._metrics_cache
            suggestions = {}
            
            # Check trap performance
            trap_perf = metrics.trap_performance.get("trap_detected", {})
            if trap_perf.get("trades", 0) > 5:  # Minimum sample size
                trap_win_rate = trap_perf.get("win_rate", 0)
                if trap_win_rate < 0.3:  # Low win rate in traps
                    suggestions["increase_trap_penalty"] = {
                        "current_win_rate": trap_win_rate,
                        "suggestion": "Increase trap detection penalty by 20%"
                    }
            
            # Check confidence accuracy
            if metrics.confidence_accuracy < 0.2 and metrics.avg_confidence > 0.7:
                suggestions["reduce_confidence_scaling"] = {
                    "current_accuracy": metrics.confidence_accuracy,
                    "avg_confidence": metrics.avg_confidence,
                    "suggestion": "Reduce confidence scaling factor"
                }
            
            # Check regime performance
            regime_perf = metrics.regime_performance
            if regime_perf:
                worst_regime = min(regime_perf.items(), key=lambda x: x[1].get("win_rate", 0))
                if worst_regime[1].get("trades", 0) > 5 and worst_regime[1].get("win_rate", 0) < 0.3:
                    suggestions["regime_adjustment"] = {
                        "worst_regime": worst_regime[0],
                        "win_rate": worst_regime[1].get("win_rate", 0),
                        "suggestion": f"Reduce confidence in {worst_regime[0]} regime"
                    }
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Failed to generate auto-tuning suggestions: {e}")
            return {}
    
    def print_performance_debug(self) -> None:
        """Print performance debug output"""
        try:
            metrics = self.compute_metrics()
            
            print("[PERFORMANCE]", {
                "win_rate": round(metrics.win_rate, 3),
                "avg_confidence": round(metrics.avg_confidence, 3),
                "confidence_accuracy": round(metrics.confidence_accuracy, 3),
                "total_trades": metrics.total_trades,
                "winning_trades": metrics.winning_trades
            })
            
            # Print bucket performance
            if metrics.regime_performance:
                print("[REGIME PERFORMANCE]", metrics.regime_performance)
            
            if metrics.entry_performance:
                print("[ENTRY PERFORMANCE]", metrics.entry_performance)
            
            if metrics.trap_performance:
                print("[TRAP PERFORMANCE]", metrics.trap_performance)
            
            # Print auto-tuning suggestions
            suggestions = self.get_auto_tuning_suggestions()
            if suggestions:
                print("[AUTO-TUNING SUGGESTIONS]", suggestions)
            
        except Exception as e:
            logger.error(f"Failed to print performance debug: {e}")
    
    def load_historical_data(self) -> None:
        """Load historical data from files"""
        try:
            # Load signals
            if self.signals_file.exists():
                with open(self.signals_file, "r") as f:
                    for line in f:
                        if line.strip():
                            data = json.loads(line)
                            signal = TradeSignal(**data)
                            self._signals_cache.append(signal)
            
            # Load outcomes
            if self.outcomes_file.exists():
                with open(self.outcomes_file, "r") as f:
                    for line in f:
                        if line.strip():
                            data = json.loads(line)
                            # Reconstruct TradeSignal
                            signal_data = data["original_signal"]
                            signal = TradeSignal(**signal_data)
                            outcome = TradeOutcome(
                                timestamp=data["timestamp"],
                                original_signal=signal,
                                future_price=data["future_price"],
                                result=data["result"],
                                price_change=data["price_change"],
                                price_change_pct=data["price_change_pct"]
                            )
                            self._outcomes_cache.append(outcome)
            
            logger.info(f"Loaded {len(self._signals_cache)} signals and {len(self._outcomes_cache)} outcomes")
            
        except Exception as e:
            logger.error(f"Failed to load historical data: {e}")
    
    def _get_default_metrics(self) -> PerformanceMetrics:
        """Get default performance metrics"""
        return PerformanceMetrics(
            total_trades=0,
            winning_trades=0,
            win_rate=0.0,
            avg_confidence=0.0,
            confidence_accuracy=0.0,
            regime_performance={},
            entry_performance={},
            trap_performance={}
        )

# Global instance for application-wide use
performance_tracker = PerformanceTracker()
