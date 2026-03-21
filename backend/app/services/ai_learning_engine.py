import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from ai.ai_db import ai_db
from app.core.logging_config import AI_DEBUG

logger = logging.getLogger(__name__)

class AILearningEngine:
    def __init__(self):
        self.db = ai_db
        self.learning_window_days = 30
        self.min_predictions_for_learning = 5
        
    async def get_formula_performance(self, formula_id: str, days: int = 30) -> Dict:
        """Get performance statistics for a specific formula (Async)"""
        try:
            query = """
                SELECT 
                    COUNT(*) as total_predictions,
                    SUM(CASE WHEN o.outcome = 'WIN' THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN o.outcome = 'LOSS' THEN 1 ELSE 0 END) as losses,
                    SUM(CASE WHEN o.outcome = 'HOLD' THEN 1 ELSE 0 END) as holds,
                    AVG(p.confidence) as avg_confidence,
                    MAX(o.evaluation_time) as last_evaluation
                FROM ai_signal_logs p
                LEFT JOIN outcome_log o ON p.id::text = o.prediction_id::text
                WHERE p.formula_id = %s
                AND p.timestamp >= NOW() - (%s)::interval
            """
            
            params = (int(formula_id), f"{days} days")
            result = await self.db.fetch_one(query, params)
            
            if result:
                total_predictions = result[0] or 0
                wins = result[1] or 0
                losses = result[2] or 0
                holds = result[3] or 0
                avg_confidence = result[4] or 0.0
                last_evaluation = result[5]
                
                considered = wins + losses
                success_rate = (wins / considered * 100) if considered > 0 else 0.0
                
                return {
                    'formula_id': formula_id,
                    'total_predictions': total_predictions,
                    'wins': wins,
                    'losses': losses,
                    'holds': holds,
                    'success_rate': round(success_rate, 2),
                    'avg_confidence': round(avg_confidence, 2),
                    'last_evaluation': last_evaluation,
                    'period_days': days
                }
            return {'formula_id': formula_id, 'total_predictions': 0, 'wins': 0, 'losses': 0, 'holds': 0, 'success_rate': 0.0, 'avg_confidence': 0.0, 'last_evaluation': None, 'period_days': days}
        except Exception as e:
            logger.error(f"Error getting performance for {formula_id}: {e}")
            return {'formula_id': formula_id, 'total_predictions': 0, 'wins': 0, 'losses': 0, 'holds': 0, 'success_rate': 0.0, 'avg_confidence': 0.0, 'last_evaluation': None, 'period_days': days}

    async def get_current_formula_experience(self, formula_id: str) -> Optional[Dict]:
        """Get current formula experience from DB (Async)"""
        try:
            query = """
                SELECT total_tests, wins, losses, success_rate, experience_adjusted_confidence, last_updated
                FROM formula_experience
                WHERE formula_id = %s
            """
            result = await self.db.fetch_one(query, (str(formula_id),))
            if result:
                return {
                    'formula_id': formula_id,
                    'total_tests': result[0] or 0,
                    'wins': result[1] or 0,
                    'losses': result[2] or 0,
                    'success_rate': result[3] or 0.0,
                    'experience_adjusted_confidence': result[4] or 0.0,
                    'last_updated': result[5]
                }
            return None
        except Exception as e:
            logger.error(f"Error getting experience for {formula_id}: {e}")
            return None

    def calculate_experience_adjusted_confidence(self, base_confidence: float, success_rate: float, total_tests: int) -> float:
        """Calculate experience-adjusted confidence"""
        experience_weight = min(0.4, total_tests / 100.0)
        base_weight = 1.0 - experience_weight
        
        if success_rate >= 60: multiplier = 1.2
        elif success_rate >= 50: multiplier = 1.0
        elif success_rate >= 40: multiplier = 0.8
        else: multiplier = 0.6
        
        adjusted = (base_confidence * base_weight * multiplier + success_rate / 100.0 * experience_weight)
        return round(max(0.1, min(0.95, adjusted)), 3)

    async def update_formula_experience(self, formula_id: str) -> bool:
        """Update formula experience (Async)"""
        try:
            performance = await self.get_formula_performance(formula_id, self.learning_window_days)
            if performance['total_predictions'] < self.min_predictions_for_learning:
                return True
            
            current_exp = await self.get_current_formula_experience(formula_id)
            base_confidence = await self.get_formula_base_confidence(formula_id)
            
            exp_adjusted_confidence = self.calculate_experience_adjusted_confidence(
                base_confidence, performance['success_rate'], performance['total_predictions']
            )
            
            if current_exp:
                query = """
                    UPDATE formula_experience
                    SET total_tests = %s, wins = %s, losses = %s, success_rate = %s,
                        experience_adjusted_confidence = %s, last_updated = %s
                    WHERE formula_id = %s
                """
                params = (performance['total_predictions'], performance['wins'], performance['losses'], 
                          performance['success_rate'], exp_adjusted_confidence, datetime.now(), str(formula_id))
            else:
                query = """
                    INSERT INTO formula_experience 
                    (formula_id, total_tests, wins, losses, success_rate, experience_adjusted_confidence, last_updated)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                params = (str(formula_id), performance['total_predictions'], performance['wins'], 
                          performance['losses'], performance['success_rate'], exp_adjusted_confidence, datetime.now())
                
            return await self.db.execute_query(query, params)
        except Exception as e:
            logger.error(f"Error updating experience for {formula_id}: {e}")
            return False

    async def get_formula_base_confidence(self, formula_id: str) -> float:
        """Get base confidence from formula_master (Async)"""
        try:
            query = "SELECT confidence_threshold FROM formula_master WHERE id::text = %s"
            result = await self.db.fetch_one(query, (str(formula_id),))
            return result[0] if result else 0.5
        except Exception as e:
            logger.error(f"Error getting base confidence: {e}")
            return 0.5

    async def get_all_active_formulas(self) -> List[str]:
        """Get all active formula IDs (Async)"""
        try:
            query = "SELECT id FROM formula_master WHERE is_active = TRUE"
            results = await self.db.fetch_query(query)
            return [str(row[0]) for row in results]
        except Exception as e:
            logger.error(f"Error getting active formulas: {e}")
            return []

    async def update_all_formula_learning(self) -> int:
        """Update learning for all active formulas (Async)"""
        try:
            formula_ids = await self.get_all_active_formulas()
            updated = 0
            for fid in formula_ids:
                if await self.update_formula_experience(fid):
                    updated += 1
            logger.info(f"Learning updated for {updated}/{len(formula_ids)} formulas")
            return updated
        except Exception as e:
            logger.error(f"Error in learning cycle: {e}")
            return 0

    async def log_ai_event(self, event_type: str, description: str):
        """Log AI events (Async)"""
        try:
            query = "INSERT INTO ai_event_log (event_type, description) VALUES (%s, %s)"
            await self.db.execute_query(query, (event_type, description))
        except Exception as e:
            logger.error(f"Error logging AI event: {e}")

# Global instance
ai_learning_engine = AILearningEngine()
