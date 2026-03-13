"""
Learning Engine - Tracks and learns from trade outcomes
Lightweight, optimized for Intel i5 CPU, 8GB RAM
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)

@dataclass
class FormulaPerformance:
    """Formula performance tracking"""
    formula_id: str
    total_predictions: int
    successful_predictions: int
    success_rate: float
    avg_confidence: float
    last_updated: datetime

@dataclass
class StrategyPerformance:
    """Strategy performance tracking"""
    strategy: str
    total_trades: int
    profitable_trades: int
    win_rate: float
    avg_return: float
    max_drawdown: float
    last_updated: datetime

class LearningEngine:
    """
    Tracks and learns from trade outcomes
    Updates formula and strategy performance based on results
    """
    
    def __init__(self):
        # Performance tracking
        self.formula_performance: Dict[str, FormulaPerformance] = {}
        self.strategy_performance: Dict[str, StrategyPerformance] = {}
        
        # Learning parameters
        self.min_predictions_for_learning = 10  # Minimum predictions before adjusting confidence
        self.learning_rate = 0.1  # How quickly to adjust confidence
        
        # Initialize with default values
        self._initialize_default_performance()
    
    def _initialize_default_performance(self):
        """Initialize default performance metrics"""
        formulas = ["F01", "F02", "F03", "F04", "F05", "F06", "F07", "F08", "F09", "F10"]
        strategies = ["Long Call", "Long Put", "Bull Call Spread", "Bear Put Spread", "Iron Condor", "Straddle", "Strangle"]
        
        for formula_id in formulas:
            self.formula_performance[formula_id] = FormulaPerformance(
                formula_id=formula_id,
                total_predictions=0,
                successful_predictions=0,
                success_rate=0.5,  # Default 50% success rate
                avg_confidence=0.6,
                last_updated=datetime.now()
            )
        
        for strategy in strategies:
            self.strategy_performance[strategy] = StrategyPerformance(
                strategy=strategy,
                total_trades=0,
                profitable_trades=0,
                win_rate=0.5,  # Default 50% win rate
                avg_return=0.0,
                max_drawdown=0.0,
                last_updated=datetime.now()
            )
    
    def record_prediction(self, formula_signals: Dict[str, Any], trade_suggestion: Any, prediction_id: str = None):
        """
        Record a prediction for later outcome tracking
        """
        try:
            # Store prediction data (simplified - in production would use database)
            prediction_data = {
                'timestamp': datetime.now().isoformat(),
                'prediction_id': prediction_id or f"pred_{datetime.now().timestamp()}",
                'formula_signals': {fid: {
                    'signal': signal.signal,
                    'confidence': signal.confidence,
                    'reason': signal.reason
                } for fid, signal in formula_signals.items()},
                'trade_suggestion': {
                    'strategy': trade_suggestion.strategy,
                    'confidence': trade_suggestion.confidence,
                    'entry_price': trade_suggestion.entry_price,
                    'target_price': trade_suggestion.target_price,
                    'stoploss_price': trade_suggestion.stoploss_price
                }
            }
            
            # Update formula prediction counts
            for formula_id, signal in formula_signals.items():
                if formula_id in self.formula_performance:
                    perf = self.formula_performance[formula_id]
                    perf.total_predictions += 1
                    
                    # Update average confidence
                    total_conf = perf.avg_confidence * (perf.total_predictions - 1) + signal.confidence
                    perf.avg_confidence = total_conf / perf.total_predictions
                    perf.last_updated = datetime.now()
            
            # Update strategy trade counts
            if trade_suggestion.strategy in self.strategy_performance:
                strat_perf = self.strategy_performance[trade_suggestion.strategy]
                strat_perf.total_trades += 1
                strat_perf.last_updated = datetime.now()
            
            logger.info(f"Recorded prediction: {prediction_data['prediction_id']}")
            return prediction_data['prediction_id']
            
        except Exception as e:
            logger.error(f"Prediction recording error: {e}")
            return None
    
    def record_outcome(self, prediction_id: str, outcome_data: Dict[str, Any]):
        """
        Record the outcome of a prediction
        """
        try:
            # Extract outcome information
            success = outcome_data.get('success', False)
            return_pct = outcome_data.get('return_pct', 0.0)
            strategy = outcome_data.get('strategy', '')
            formula_results = outcome_data.get('formula_results', {})
            
            # Update formula performance
            for formula_id, was_correct in formula_results.items():
                if formula_id in self.formula_performance:
                    perf = self.formula_performance[formula_id]
                    
                    if was_correct:
                        perf.successful_predictions += 1
                    
                    # Update success rate
                    if perf.total_predictions > 0:
                        perf.success_rate = perf.successful_predictions / perf.total_predictions
                    
                    perf.last_updated = datetime.now()
            
            # Update strategy performance
            if strategy in self.strategy_performance:
                strat_perf = self.strategy_performance[strategy]
                
                if success:
                    strat_perf.profitable_trades += 1
                
                # Update win rate
                if strat_perf.total_trades > 0:
                    strat_perf.win_rate = strat_perf.profitable_trades / strat_perf.total_trades
                
                # Update average return
                total_return = strat_perf.avg_return * (strat_perf.total_trades - 1) + return_pct
                strat_perf.avg_return = total_return / strat_perf.total_trades
                
                # Update max drawdown (simplified)
                if return_pct < strat_perf.max_drawdown:
                    strat_perf.max_drawdown = return_pct
                
                strat_perf.last_updated = datetime.now()
            
            logger.info(f"Recorded outcome for prediction {prediction_id}: success={success}, return={return_pct:.2%}")
            
        except Exception as e:
            logger.error(f"Outcome recording error: {e}")
    
    def adjust_confidence(self, formula_signals: Dict[str, Any]) -> Dict[str, float]:
        """
        Adjust formula confidence based on historical performance
        """
        try:
            adjusted_signals = {}
            
            for formula_id, signal in formula_signals.items():
                if formula_id in self.formula_performance:
                    perf = self.formula_performance[formula_id]
                    
                    if perf.total_predictions >= self.min_predictions_for_learning:
                        # Calculate confidence adjustment
                        success_rate_diff = perf.success_rate - 0.5  # Difference from 50% baseline
                        confidence_adjustment = success_rate_diff * self.learning_rate
                        
                        # Apply adjustment
                        original_confidence = signal.confidence
                        adjusted_confidence = original_confidence + confidence_adjustment
                        
                        # Clamp to valid range
                        adjusted_confidence = max(0.1, min(1.0, adjusted_confidence))
                        
                        # Create adjusted signal
                        adjusted_signals[formula_id] = adjusted_confidence
                    else:
                        # Not enough data, use original confidence
                        adjusted_signals[formula_id] = signal.confidence
                else:
                    adjusted_signals[formula_id] = signal.confidence
            
            return adjusted_signals
            
        except Exception as e:
            logger.error(f"Confidence adjustment error: {e}")
            # Return original confidences on error
            return {fid: signal.confidence for fid, signal in formula_signals.items()}
    
    def get_strategy_ranking(self) -> List[Tuple[str, float]]:
        """
        Get strategies ranked by performance
        """
        try:
            strategy_scores = []
            
            for strategy, perf in self.strategy_performance.items():
                if perf.total_trades >= 5:  # Minimum trades for ranking
                    # Composite score: win rate * average return (with some adjustments)
                    score = perf.win_rate * (1 + perf.avg_return)
                    
                    # Penalty for high drawdown
                    if perf.max_drawdown < -0.2:  # More than 20% drawdown
                        score *= 0.8
                    
                    strategy_scores.append((strategy, score))
            
            # Sort by score (descending)
            strategy_scores.sort(key=lambda x: x[1], reverse=True)
            
            return strategy_scores
            
        except Exception as e:
            logger.error(f"Strategy ranking error: {e}")
            return []
    
    def get_formula_effectiveness(self) -> Dict[str, Dict[str, float]]:
        """
        Get formula effectiveness metrics
        """
        try:
            effectiveness = {}
            
            for formula_id, perf in self.formula_performance.items():
                if perf.total_predictions >= self.min_predictions_for_learning:
                    effectiveness[formula_id] = {
                        'success_rate': perf.success_rate,
                        'avg_confidence': perf.avg_confidence,
                        'predictions': perf.total_predictions,
                        'reliability': perf.success_rate / perf.avg_confidence if perf.avg_confidence > 0 else 0.5
                    }
                else:
                    effectiveness[formula_id] = {
                        'success_rate': 0.5,
                        'avg_confidence': 0.6,
                        'predictions': perf.total_predictions,
                        'reliability': 0.83  # Default
                    }
            
            return effectiveness
            
        except Exception as e:
            logger.error(f"Formula effectiveness error: {e}")
            return {}
    
    def should_adjust_strategy(self, strategy: str, current_confidence: float) -> Tuple[bool, float, str]:
        """
        Determine if strategy confidence should be adjusted based on performance
        """
        try:
            if strategy not in self.strategy_performance:
                return False, current_confidence, "No performance data"
            
            perf = self.strategy_performance[strategy]
            
            if perf.total_trades < 5:
                return False, current_confidence, "Insufficient data"
            
            # Calculate adjustment based on win rate and average return
            performance_factor = perf.win_rate * (1 + perf.avg_return)
            
            if performance_factor > 0.6:  # Good performance
                adjustment = 0.05
                reason = f"Strong performance: {perf.win_rate:.1%} win rate, {perf.avg_return:.1%} avg return"
            elif performance_factor < 0.4:  # Poor performance
                adjustment = -0.05
                reason = f"Weak performance: {perf.win_rate:.1%} win rate, {perf.avg_return:.1%} avg return"
            else:
                return False, current_confidence, "Performance within normal range"
            
            new_confidence = max(0.5, min(1.0, current_confidence + adjustment))
            
            return True, new_confidence, reason
            
        except Exception as e:
            logger.error(f"Strategy adjustment error: {e}")
            return False, current_confidence, "Error in adjustment calculation"
    
    def get_learning_summary(self) -> Dict[str, Any]:
        """
        Get summary of learning engine status
        """
        try:
            total_predictions = sum(perf.total_predictions for perf in self.formula_performance.values())
            total_trades = sum(perf.total_trades for perf in self.strategy_performance.values())
            
            best_formula = max(self.formula_performance.items(), 
                             key=lambda x: x[1].success_rate if x[1].total_predictions >= 5 else 0)
            
            best_strategy = max(self.strategy_performance.items(),
                              key=lambda x: x[1].win_rate if x[1].total_trades >= 5 else 0)
            
            return {
                'total_predictions': total_predictions,
                'total_trades': total_trades,
                'formulas_tracked': len(self.formula_performance),
                'strategies_tracked': len(self.strategy_performance),
                'best_formula': {
                    'id': best_formula[0],
                    'success_rate': best_formula[1].success_rate,
                    'predictions': best_formula[1].total_predictions
                },
                'best_strategy': {
                    'name': best_strategy[0],
                    'win_rate': best_strategy[1].win_rate,
                    'trades': best_strategy[1].total_trades,
                    'avg_return': best_strategy[1].avg_return
                },
                'learning_rate': self.learning_rate,
                'min_predictions_threshold': self.min_predictions_for_learning
            }
            
        except Exception as e:
            logger.error(f"Learning summary error: {e}")
            return {'error': str(e)}
