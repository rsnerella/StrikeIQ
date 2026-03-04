"""
AI Outcome Engine for StrikeIQ

Responsibilities:
- Find predictions where outcome_checked = FALSE
- Determine result using price movement and paper trade results
- Insert result into outcome_log
- Update prediction_log with outcome
"""
import logging
import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from ai.ai_db import ai_db
from ai.prediction_service import prediction_service

logger = logging.getLogger(__name__)

prediction_lock = asyncio.Lock()
resolved_predictions = set()
last_ai_run = 0

class AIOutcomeEngine:
    def __init__(self):
        self.db = ai_db
        self.prediction_service = prediction_service
        self.outcome_threshold_minutes = 30  # Time to wait before evaluating outcome
        
    def get_pending_outcome_predictions(self) -> List[Dict]:
        """Get predictions that need outcome evaluation"""
        try:
            query = """
                SELECT p.id, p.formula_id, p.signal, p.confidence, p.nifty_spot, 
                       p.prediction_time, pt.pnl, pt.exit_time
                FROM prediction_log p
                LEFT JOIN paper_trade_log pt ON p.id = pt.prediction_id
                WHERE p.outcome_checked = FALSE
                AND p.prediction_time <= NOW() - INTERVAL %s
                AND p.signal IN ('BUY', 'SELL')
                ORDER BY p.prediction_time ASC
                LIMIT 100
            """
            
            params = (f"{self.outcome_threshold_minutes} minutes",)
            results = self.db.fetch_query(query, params)
            
            predictions = []
            for row in results:
                predictions.append({
                    'id': row[0],
                    'formula_id': row[1],
                    'signal': row[2],
                    'confidence': row[3],
                    'nifty_spot': row[4],
                    'prediction_time': row[5],
                    'pnl': row[6],
                    'exit_time': row[7]
                })
                
            logger.info(f"Found {len(predictions)} predictions pending outcome evaluation")
            return predictions
            
        except Exception as e:
            logger.error(f"Error fetching pending outcome predictions: {e}")
            return []
    
    def get_market_price_movement(self, prediction_time: datetime, initial_spot: float) -> float:
        """
        Calculate market price movement from prediction time to evaluation time
        
        Returns:
            Price movement percentage (positive for upward movement)
        """
        try:
            # In production, fetch actual market data from market_snapshot table
            # For now, simulate with a simple model
            
            query = """
                SELECT spot_price
                FROM market_snapshot
                WHERE timestamp >= %s
                ORDER BY timestamp ASC
                LIMIT 1
            """
            
            # Look for market snapshot shortly after prediction time
            search_time = prediction_time + timedelta(minutes=5)
            result = self.db.fetch_one(query, (search_time,))
            
            if result:
                final_spot = result[0]
                price_movement = ((final_spot - initial_spot) / initial_spot) * 100
                return price_movement
            else:
                # Fallback: simulate price movement
                import random
                movement = random.uniform(-2.0, 2.0)  # Random movement between -2% and +2%
                logger.warning(f"No market data found, using simulated movement: {movement:.2f}%")
                return movement
                
        except Exception as e:
            logger.error(f"Error calculating market price movement: {e}")
            return 0.0  # No movement as fallback
    
    def determine_outcome_from_price_movement(self, signal: str, price_movement: float) -> str:
        """
        Determine outcome based on signal and price movement
        
        Args:
            signal: BUY or SELL
            price_movement: Percentage price movement (positive = up, negative = down)
            
        Returns:
            WIN, LOSS, or HOLD
        """
        try:
            # Define threshold for significant movement
            movement_threshold = 0.5  # 0.5% minimum movement
            
            if abs(price_movement) < movement_threshold:
                return "HOLD"
            
            if signal == "BUY":
                # BUY signal wins if price goes up
                return "WIN" if price_movement > 0 else "LOSS"
            else:  # SELL
                # SELL signal wins if price goes down
                return "WIN" if price_movement < 0 else "LOSS"
                
        except Exception as e:
            logger.error(f"Error determining outcome from price movement: {e}")
            return "HOLD"
    
    def determine_outcome_from_pnl(self, pnl: Optional[float]) -> str:
        """
        Determine outcome based on paper trade PnL
        
        Args:
            pnl: Profit and Loss from paper trade
            
        Returns:
            WIN, LOSS, or HOLD
        """
        try:
            if pnl is None:
                return "HOLD"
            
            if pnl > 0:
                return "WIN"
            elif pnl < 0:
                return "LOSS"
            else:
                return "HOLD"
                
        except Exception as e:
            logger.error(f"Error determining outcome from PnL: {e}")
            return "HOLD"
    
    def evaluate_prediction_outcome(self, prediction: Dict) -> Tuple[str, float, str]:
        """
        Evaluate the outcome of a prediction
        
        Returns:
            Tuple of (outcome, confidence, method_used)
        """
        try:
            # Method 1: Use paper trade PnL if available
            if prediction['pnl'] is not None:
                outcome = self.determine_outcome_from_pnl(prediction['pnl'])
                method = "PAPER_TRADE_PNL"
                confidence = 0.9  # High confidence with actual trade results
                logger.debug(f"Outcome determined by PnL: {outcome} (PnL: {prediction['pnl']:.2f})")
                return outcome, confidence, method
            
            # Method 2: Use market price movement
            prediction_time = prediction['prediction_time']
            if isinstance(prediction_time, str):
                prediction_time = datetime.fromisoformat(prediction_time.replace('Z', '+00:00'))
            
            price_movement = self.get_market_price_movement(prediction_time, prediction['nifty_spot'])
            outcome = self.determine_outcome_from_price_movement(prediction['signal'], price_movement)
            method = "PRICE_MOVEMENT"
            confidence = 0.7  # Lower confidence without actual trades
            
            logger.debug(f"Outcome determined by price movement: {outcome} (movement: {price_movement:.2f}%)")
            return outcome, confidence, method
            
        except Exception as e:
            logger.error(f"Error evaluating prediction outcome: {e}")
            return "HOLD", 0.0, "ERROR"
    
    def store_outcome(self, prediction: Dict, outcome: str, confidence: float, method: str) -> bool:
        """
        Store outcome in outcome_log table
        
        Returns:
            True if successful, False otherwise
        """
        try:
            query = """
                INSERT INTO outcome_log 
                (prediction_id, formula_id, outcome, confidence, evaluation_method, evaluation_time)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            
            params = (
                prediction['id'],
                prediction['formula_id'],
                outcome,
                confidence,
                method,
                datetime.now()
            )
            
            result = self.db.execute_query(query, params)
            
            if result:
                logger.info(f"Outcome stored: Prediction {prediction['id']} -> {outcome}")
                return True
            else:
                logger.error(f"Failed to store outcome for prediction {prediction['id']}")
                return False
                
        except Exception as e:
            logger.error(f"Error storing outcome: {e}")
            return False
    
    async def update_prediction_outcome(self, prediction_id: int, outcome: str):

        async with prediction_lock:

            try:

                query = """
                    UPDATE prediction_log 
                    SET outcome = %s, outcome_time = NOW(), outcome_checked = TRUE
                    WHERE id = %s AND outcome IS NULL
                """
                
                result = self.db.execute_query(query, (outcome, prediction_id))
                
                if result:
                    logger.info(f"Outcome stored: Prediction {prediction_id} → {outcome}")
                else:
                    logger.warning(f"Prediction {prediction_id} already resolved or not found")

            except Exception as e:

                logger.error(
                    f"Failed to update prediction {prediction_id}: {e}"
                )
    
    async def evaluate_pending_outcomes(self) -> int:
        """
        Evaluate all pending prediction outcomes
        
        Returns:
            Number of outcomes evaluated
        """
        global last_ai_run
        
        now = time.time()
        
        if now - last_ai_run < 5:
            return 0
            
        last_ai_run = now
        
        try:
            predictions = self.get_pending_outcome_predictions()
            outcomes_evaluated = 0
            
            for prediction in predictions:
                prediction_id = prediction['id']
                
                if prediction_id in resolved_predictions:
                    continue
                
                # Evaluate outcome
                outcome, confidence, method = self.evaluate_prediction_outcome(prediction)
                
                # Store outcome
                if self.store_outcome(prediction, outcome, confidence, method):
                    # Update prediction
                    await self.update_prediction_outcome(prediction_id, outcome)
                    outcomes_evaluated += 1
                    resolved_predictions.add(prediction_id)
                    
                    # Log AI event
                    self.log_ai_event(
                        event_type="OUTCOME_EVALUATED",
                        description=f"Prediction {prediction_id} outcome: {outcome} (method: {method}, confidence: {confidence:.2f})"
                    )
                else:
                    logger.error(f"Failed to update prediction {prediction_id} with outcome")
            
            logger.info(f"Outcome evaluation completed. Evaluated {outcomes_evaluated} outcomes")
            return outcomes_evaluated
            
        except Exception as e:
            logger.error(f"Error in outcome evaluation: {e}")
            return 0
    
    def get_outcome_statistics(self, days: int = 7) -> Dict:
        """Get outcome statistics for the last N days"""
        try:
            query = """
                SELECT outcome, COUNT(*) as count
                FROM outcome_log
                WHERE evaluation_time >= NOW() - INTERVAL %s
                GROUP BY outcome
                ORDER BY count DESC
            """
            
            results = self.db.fetch_query(query, (f"{days} days",))
            
            stats = {'WIN': 0, 'LOSS': 0, 'HOLD': 0}
            total_outcomes = 0
            
            for row in results:
                outcome = row[0]
                count = row[1]
                stats[outcome] = count
                total_outcomes += count
            
            # Calculate win rate
            win_rate = (stats['WIN'] / total_outcomes * 100) if total_outcomes > 0 else 0
            
            return {
                'total_outcomes': total_outcomes,
                'wins': stats['WIN'],
                'losses': stats['LOSS'],
                'holds': stats['HOLD'],
                'win_rate': round(win_rate, 2),
                'period_days': days
            }
            
        except Exception as e:
            logger.error(f"Error getting outcome statistics: {e}")
            return {
                'total_outcomes': 0,
                'wins': 0,
                'losses': 0,
                'holds': 0,
                'win_rate': 0.0,
                'period_days': days
            }
    
    def log_ai_event(self, event_type: str, description: str):
        """Log AI events to ai_event_log table"""
        try:
            query = """
                INSERT INTO ai_event_log (event_type, description)
                VALUES (%s, %s)
            """
            
            params = (event_type, description)
            self.db.execute_query(query, params)
            
        except Exception as e:
            logger.error(f"Error logging AI event: {e}")

# Global outcome engine instance
ai_outcome_engine = AIOutcomeEngine()
