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
from app.core.logging_config import AI_DEBUG

logger = logging.getLogger(__name__)

prediction_lock = asyncio.Lock()
last_ai_run = 0

class AIOutcomeEngine:
    def __init__(self):
        self.db = ai_db
        self.prediction_service = prediction_service
        self.outcome_threshold_minutes = 2  # Time to wait before evaluating outcome (Phase 5)
        
    async def get_pending_outcome_predictions(self) -> List[Dict]:
        """Get predictions that need outcome evaluation from ai_signal_logs"""
        try:
            cutoff = datetime.now() - timedelta(minutes=self.outcome_threshold_minutes)
            # Query the new ai_signal_logs table
            query = """
                SELECT id, formula_id, signal, confidence, spot_price, 
                       timestamp, strike, direction, entry, stop_loss, target, entry_premium, metadata
                FROM ai_signal_logs
                WHERE outcome_checked = FALSE
                AND timestamp <= %s
                ORDER BY timestamp ASC
                LIMIT 100
            """
            
            results = await self.db.fetch_query(query, (cutoff,))
            
            predictions = []
            for row in results:
                predictions.append({
                    'id': row[0],
                    'formula_id': row[1],
                    'signal': row[2],
                    'confidence': row[3],
                    'spot_price': row[4],
                    'prediction_time': row[5],
                    'strike': row[6],
                    'direction': row[7],
                    'entry': row[8],
                    'stop_loss': row[9],
                    'target': row[10],
                    'entry_premium': row[11],
                    'metadata': row[12]
                })
                
            return predictions
        except Exception as e:
            logger.error(f"Error fetching pending predictions from ai_signal_logs: {e}")
            return []

    async def evaluate_prediction_outcome(self, prediction: Dict) -> Tuple[str, float, str, float]:
        """
        Evaluate prediction outcome using Option Premium movement (Phase 4)
        Returns: (outcome, score, method, current_premium)
        """
        try:
            prediction_time = prediction['prediction_time']
            if isinstance(prediction_time, str):
                prediction_time = datetime.fromisoformat(prediction_time.replace('Z', '+00:00'))
            
            # Phase 4: TIMEOUT (4 hours)
            now = datetime.now(prediction_time.tzinfo)
            if now - prediction_time > timedelta(hours=4):
                return "TIMEOUT", 0.5, "TIME_THRESHOLD", 0.0

            strike = prediction.get('strike')
            direction = prediction.get('direction', 'CALL')
            entry_premium = float(prediction.get('entry_premium', 0) or 0)
            
            # Phase 4 Requirement: Use exact option contract price
            current_premium = 0.0
            try:
                from app.services.option_chain_builder import option_chain_builder
                right = "CE" if direction == "CALL" else "PE"
                current_premium = option_chain_builder.get_option_ltp("NIFTY", strike, right)
            except Exception as ex:
                logger.debug(f"Could not fetch current premium for evaluation: {ex}")

            # Option-based evaluation (Direct Contract evaluation)
            if current_premium > 0 and entry_premium > 0:
                # Phase 4: Volatility-aware premium target
                meta = prediction.get('metadata') or {}
                if isinstance(meta, str):
                    import json
                    try: meta = json.loads(meta)
                    except: meta = {}
                
                expected_move = float(meta.get('expected_move', 0) or 0)
                
                # target_premium = max(entry_premium * 1.5, entry_premium + expected_move * 0.3)
                target_premium = max(entry_premium * 1.5, entry_premium + (expected_move * 0.3))
                sl_premium = entry_premium * 0.7 # Keep 30% SL
                
                if current_premium >= target_premium: return "WIN", 1.0, "OPTION_TARGET_VOL_AWARE", current_premium
                if current_premium <= sl_premium: return "LOSS", 1.0, "OPTION_SL_30PCT", current_premium
                return "HOLD", 0.0, "OPTION_STILL_ACTIVE", current_premium

            # Fallback to Index Price evaluation
            query = "SELECT spot_price FROM market_snapshots ORDER BY timestamp DESC LIMIT 1"
            result = await self.db.fetch_one(query)
            current_spot = result[0] if result else None
            
            if not current_spot:
                return "HOLD", 0.0, "MISSING_DATA", 0.0

            entry_spot = prediction.get('entry') or prediction['spot_price']
            sl_spot = prediction.get('stop_loss')
            target_spot = prediction.get('target')

            if direction == "CALL":
                if target_spot and current_spot >= target_spot: return "WIN", 1.0, "INDEX_TARGET_HIT", 0.0
                if sl_spot and current_spot <= sl_spot: return "LOSS", 1.0, "INDEX_SL_HIT", 0.0
            else: # PUT
                if target_spot and current_spot <= target_spot: return "WIN", 1.0, "INDEX_TARGET_HIT", 0.0
                if sl_spot and current_spot >= sl_spot: return "LOSS", 1.0, "INDEX_SL_HIT", 0.0

            return "HOLD", 0.0, "STILL_ACTIVE", 0.0

        except Exception as e:
            logger.error(f"Error in outcome evaluation: {e}")
            return "HOLD", 0.0, "ERROR", 0.0

    async def store_outcome(self, prediction: Dict, outcome: str, confidence: float, method: str):
        """Store outcome in outcome_log table"""
        try:
            import json
            query = """
                INSERT INTO outcome_log (signal_id, predicted_outcome, actual_outcome, accuracy, metadata)
                VALUES (%s, %s, %s, %s, %s)
            """
            metadata = {'method': method, 'formula_id': prediction['formula_id']}
            params = (
                prediction['id'],
                prediction['signal'],
                outcome,
                confidence,
                json.dumps(metadata)
            )
            await self.db.execute_query(query, params)
        except Exception as e:
            logger.error(f"Failed to store outcome: {e}")

    async def update_prediction_outcome(self, prediction_id: int, outcome: str, exit_premium: float = 0, pnl: float = 0):
        async with prediction_lock:
            try:
                # Update both legacy and new logs for compatibility
                query = """
                    UPDATE ai_signal_logs 
                    SET outcome_checked = TRUE, exit_premium = %s, pnl = %s 
                    WHERE id = %s
                """
                await self.db.execute_query(query, (exit_premium, pnl, prediction_id))
                await self.prediction_service.mark_prediction_checked(prediction_id, outcome)
            except Exception as e:
                logger.error(f"Failed to update outcome for {prediction_id}: {e}")

    async def evaluate_pending_outcomes(self) -> int:
        """Evaluate pending outcomes and update experience"""
        try:
            predictions = await self.get_pending_outcome_predictions()
            if not predictions: return 0
            
            count = 0
            from ai.experience_updater import experience_updater
            
            for p in predictions:
                outcome, score, method, exit_premium = await self.evaluate_prediction_outcome(p)
                
                if outcome in ["WIN", "LOSS", "TIMEOUT"]:
                    # Calculate PnL (in points)
                    entry_premium = p.get('entry_premium', 0) or 0
                    pnl = exit_premium - entry_premium if exit_premium > 0 and entry_premium > 0 else 0
                    
                    # Store in outcome_log
                    await self.store_outcome(p, outcome, score, method)
                    # Update prediction log with premium data
                    await self.update_prediction_outcome(p['id'], outcome, exit_premium, pnl)
                    # Update experience
                    await experience_updater.update_experience(p['formula_id'], outcome, p.get('confidence', 0), pnl)
                    count += 1
            
            return count
        except Exception as e:
            logger.error(f"Error in outcome loop: {e}")
            return 0
    
    async def get_outcome_statistics(self, days: int = 7) -> Dict:
        """Get outcome statistics for the last N days (Async)"""
        try:
            query = """
                SELECT outcome, COUNT(*) as count
                FROM outcome_log
                WHERE evaluation_time >= NOW() - (%s)::interval
                GROUP BY outcome
                ORDER BY count DESC
            """
            
            results = await self.db.fetch_query(query, (f"{days} days",))
            
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
    
    async def log_ai_event(self, event_type: str, description: str):
        """Log AI events to ai_event_log table (Async)"""
        try:
            query = """
                INSERT INTO ai_event_log (event_type, description)
                VALUES (%s, %s)
            """
            
            params = (event_type, description)
            await self.db.execute_query(query, params)
            
        except Exception as e:
            logger.error(f"Error logging AI event: {e}")

# Global outcome engine instance
ai_outcome_engine = AIOutcomeEngine()
