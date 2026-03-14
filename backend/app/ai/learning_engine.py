"""
Learning Engine - Enhanced with ML Feedback Loop
Tracks and learns from trade outcomes and ML model performance
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
from sqlalchemy.orm import Session
from app.models.ai_predictions import AIPrediction
from app.models.signal_outcomes import SignalOutcome

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
    
    def __init__(self, db_session: Optional[Session] = None):
        # Database session for ML feedback
        self.db_session = db_session
        
        # Performance tracking
        self.formula_performance: Dict[str, FormulaPerformance] = {}
        self.strategy_performance: Dict[str, StrategyPerformance] = {}
        
        # ML model performance tracking
        self.ml_model_performance: Dict[str, Any] = {
            'total_predictions': 0,
            'correct_predictions': 0,
            'accuracy': 0.0,
            'avg_confidence': 0.0,
            'feature_importance': {},
            'last_updated': datetime.now()
        }
        
        # Learning parameters
        self.min_predictions_for_learning = 10  # Minimum predictions before adjusting confidence
        self.learning_rate = 0.1  # How quickly to adjust confidence
        
        # Feedback loop parameters
        self.feedback_interval = timedelta(hours=1)  # How often to run feedback loop
        self.last_feedback_time = datetime.now()
        
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
                'min_predictions_threshold': self.min_predictions_for_learning,
                'ml_performance': self.ml_model_performance
            }
            
        except Exception as e:
            logger.error(f"Learning summary error: {e}")
            return {'error': str(e)}
    
    # NEW ML FEEDBACK LOOP METHODS
    
    async def evaluate_prediction_accuracy(self, symbol: Optional[str] = None, days_back: int = 7) -> Dict[str, Any]:
        """Evaluate ML model prediction accuracy against actual outcomes"""
        try:
            if not self.db_session:
                return {'error': 'No database session available'}
            
            # Get recent predictions
            cutoff_date = datetime.now() - timedelta(days=days_back)
            
            predictions_query = self.db_session.query(AIPrediction).filter(
                AIPrediction.timestamp >= cutoff_date
            )
            
            if symbol:
                predictions_query = predictions_query.filter(AIPrediction.symbol == symbol)
            
            predictions = predictions_query.all()
            
            if not predictions:
                return {'error': 'No predictions found for evaluation', 'symbol': symbol, 'days_back': days_back}
            
            # Match predictions with outcomes
            correct_predictions = 0
            total_evaluated = 0
            accuracy_by_confidence = {}
            
            for prediction in predictions:
                # Find corresponding outcome
                outcome = self.db_session.query(SignalOutcome).filter(
                    SignalOutcome.signal_id == f"pred_{prediction.timestamp.strftime('%Y%m%d_%H%M%S')}_{prediction.symbol}"
                ).first()
                
                if outcome:
                    total_evaluated += 1
                    
                    # Determine if prediction was correct
                    predicted_direction = 'buy' if prediction.buy_probability > prediction.sell_probability else 'sell'
                    actual_direction = 'buy' if outcome.profit_loss > 0 else 'sell'
                    
                    if predicted_direction == actual_direction:
                        correct_predictions += 1
                    
                    # Track accuracy by confidence range
                    conf_range = int(prediction.confidence_score * 10) / 10  # 0.1, 0.2, ..., 1.0
                    if conf_range not in accuracy_by_confidence:
                        accuracy_by_confidence[conf_range] = {'correct': 0, 'total': 0}
                    
                    accuracy_by_confidence[conf_range]['total'] += 1
                    if predicted_direction == actual_direction:
                        accuracy_by_confidence[conf_range]['correct'] += 1
            
            # Calculate overall accuracy
            accuracy = correct_predictions / total_evaluated if total_evaluated > 0 else 0
            
            # Calculate accuracy by confidence
            accuracy_by_confidence_result = {}
            for conf_range, stats in accuracy_by_confidence.items():
                accuracy_by_confidence_result[conf_range] = (
                    stats['correct'] / stats['total'] if stats['total'] > 0 else 0
                )
            
            # Update ML model performance
            self.ml_model_performance.update({
                'total_predictions': self.ml_model_performance['total_predictions'] + total_evaluated,
                'correct_predictions': self.ml_model_performance['correct_predictions'] + correct_predictions,
                'accuracy': accuracy,
                'last_updated': datetime.now()
            })
            
            result = {
                'symbol': symbol,
                'days_back': days_back,
                'total_evaluated': total_evaluated,
                'correct_predictions': correct_predictions,
                'accuracy': accuracy,
                'accuracy_by_confidence': accuracy_by_confidence_result,
                'ml_performance': self.ml_model_performance
            }
            
            logger.info(f"ML prediction accuracy evaluated: {accuracy:.3f} ({correct_predictions}/{total_evaluated})")
            return result
            
        except Exception as e:
            logger.error(f"Error evaluating prediction accuracy: {e}")
            return {'error': str(e)}
    
    async def update_strategy_weights(self, accuracy_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update strategy weights based on ML accuracy"""
        try:
            updated_weights = {}
            
            # Get current strategy performance
            current_ranking = self.get_strategy_ranking()
            
            # Adjust weights based on accuracy
            for strategy, current_score in current_ranking:
                # Get ML accuracy for this strategy
                strategy_accuracy = accuracy_data.get('accuracy', 0.5)
                
                # Calculate weight adjustment
                if strategy_accuracy > 0.6:  # High accuracy
                    weight_adjustment = 0.1
                    reason = f"High accuracy: {strategy_accuracy:.2%}"
                elif strategy_accuracy < 0.4:  # Low accuracy
                    weight_adjustment = -0.1
                    reason = f"Low accuracy: {strategy_accuracy:.2%}"
                else:
                    weight_adjustment = 0.0
                    reason = "Average accuracy"
                
                new_weight = max(0.1, min(1.0, current_score + weight_adjustment))
                updated_weights[strategy] = {
                    'old_weight': current_score,
                    'new_weight': new_weight,
                    'adjustment': weight_adjustment,
                    'reason': reason,
                    'accuracy': strategy_accuracy
                }
            
            logger.info(f"Strategy weights updated based on ML accuracy: {len(updated_weights)} strategies")
            return updated_weights
            
        except Exception as e:
            logger.error(f"Error updating strategy weights: {e}")
            return {}
    
    async def track_model_performance(self, symbol: str, features: Dict[str, Any], prediction: Dict[str, Any], outcome: Dict[str, Any]) -> None:
        """Track individual model performance for feature importance analysis"""
        try:
            if not prediction.get('prediction_successful', False):
                return
            
            # Determine if prediction was correct
            predicted_direction = 'buy' if prediction.get('buy_probability', 0.5) > prediction.get('sell_probability', 0.5) else 'sell'
            actual_direction = 'buy' if outcome.get('profit_loss', 0) > 0 else 'sell'
            
            is_correct = predicted_direction == actual_direction
            
            # Update overall performance
            self.ml_model_performance['total_predictions'] += 1
            if is_correct:
                self.ml_model_performance['correct_predictions'] += 1
            
            # Update accuracy
            total = self.ml_model_performance['total_predictions']
            correct = self.ml_model_performance['correct_predictions']
            self.ml_model_performance['accuracy'] = correct / total if total > 0 else 0
            
            # Update average confidence
            current_conf = self.ml_model_performance['avg_confidence']
            new_conf = prediction.get('confidence_score', 0)
            self.ml_model_performance['avg_confidence'] = (current_conf * (total - 1) + new_conf) / total
            
            # Update feature importance (simplified)
            feature_importance = prediction.get('feature_importance', {})
            if feature_importance and is_correct:
                # Increase importance of features that led to correct predictions
                for feature, importance in feature_importance.items():
                    if feature in self.ml_model_performance['feature_importance']:
                        self.ml_model_performance['feature_importance'][feature] = (
                            self.ml_model_performance['feature_importance'][feature] * 0.9 + importance * 0.1
                        )
                    else:
                        self.ml_model_performance['feature_importance'][feature] = importance
            
            self.ml_model_performance['last_updated'] = datetime.now()
            
            logger.debug(f"Tracked model performance for {symbol}: correct={is_correct}, accuracy={self.ml_model_performance['accuracy']:.3f}")
            
        except Exception as e:
            logger.error(f"Error tracking model performance: {e}")
    
    async def run_feedback_loop(self) -> Dict[str, Any]:
        """Run the ML feedback loop"""
        try:
            logger.info("Starting ML feedback loop")
            
            # Step 1: Evaluate prediction accuracy
            accuracy_result = await self.evaluate_prediction_accuracy()
            
            if 'error' in accuracy_result:
                return accuracy_result
            
            # Step 2: Update strategy weights
            weight_updates = await self.update_strategy_weights(accuracy_result)
            
            # Step 3: Generate learning insights
            insights = self._generate_learning_insights(accuracy_result, weight_updates)
            
            # Update feedback time
            self.last_feedback_time = datetime.now()
            
            result = {
                'feedback_time': self.last_feedback_time.isoformat(),
                'accuracy_evaluation': accuracy_result,
                'strategy_weight_updates': weight_updates,
                'learning_insights': insights,
                'ml_performance': self.ml_model_performance
            }
            
            logger.info(f"ML feedback loop completed: accuracy={accuracy_result['accuracy']:.3f}")
            return result
            
        except Exception as e:
            logger.error(f"Error in feedback loop: {e}")
            return {'error': str(e)}
    
    def _generate_learning_insights(self, accuracy_data: Dict[str, Any], weight_updates: Dict[str, Any]) -> List[str]:
        """Generate learning insights from feedback loop"""
        insights = []
        
        accuracy = accuracy_data.get('accuracy', 0)
        
        # Overall performance insight
        if accuracy > 0.7:
            insights.append(f"ML model performing well with {accuracy:.1%} accuracy")
        elif accuracy < 0.4:
            insights.append(f"ML model needs improvement with {accuracy:.1%} accuracy")
        else:
            insights.append(f"ML model performance is average with {accuracy:.1%} accuracy")
        
        # Strategy weight insights
        if weight_updates:
            increased_weights = [s for s, w in weight_updates.items() if w['adjustment'] > 0]
            decreased_weights = [s for s, w in weight_updates.items() if w['adjustment'] < 0]
            
            if increased_weights:
                insights.append(f"Increased weight for {len(increased_weights)} strategies: {', '.join(increased_weights[:3])}")
            
            if decreased_weights:
                insights.append(f"Decreased weight for {len(decreased_weights)} strategies: {', '.join(decrecreased_weights[:3])}")
        
        # Confidence range insights
        accuracy_by_conf = accuracy_data.get('accuracy_by_confidence', {})
        if accuracy_by_conf:
            high_conf_accuracy = accuracy_by_conf.get(0.9, 0)  # 90-100% confidence
            low_conf_accuracy = accuracy_by_conf.get(0.1, 0)   # 0-10% confidence
            
            if high_conf_accuracy > 0.8:
                insights.append("High confidence predictions are very reliable")
            elif low_conf_accuracy < 0.3:
                insights.append("Low confidence predictions need improvement")
        
        return insights
    
    async def should_trigger_retraining(self) -> Tuple[bool, str]:
        """Determine if model retraining should be triggered"""
        try:
            # Check if enough time has passed since last feedback
            if datetime.now() - self.last_feedback_time < self.feedback_interval:
                return False, "Too soon since last feedback loop"
            
            # Check accuracy threshold
            accuracy = self.ml_model_performance.get('accuracy', 0)
            if accuracy < 0.5 and self.ml_model_performance['total_predictions'] >= 100:
                return True, f"Low accuracy ({accuracy:.2%}) with sufficient predictions"
            
            # Check prediction volume
            if self.ml_model_performance['total_predictions'] >= 1000:
                return True, "High prediction volume reached, time for retraining"
            
            return False, "No retraining trigger conditions met"
            
        except Exception as e:
            logger.error(f"Error checking retraining trigger: {e}")
            return False, f"Error checking retraining: {e}"
