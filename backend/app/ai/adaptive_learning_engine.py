import logging
import json
from datetime import datetime
from typing import Dict, Any, List
from .ai_db import ai_db
from app.services.cache_service import cache_service

logger = logging.getLogger(__name__)

class AdaptiveLearningEngine:
    """
    Analyzes historical trade outcomes and computes strategy scores for future biasing.
    Responsibilities:
    - Analyze ai_trade_history
    - Compute metrics: strategy_success_rate, avg_rr_ratio, win_rate_by_market_regime, confidence_accuracy
    - Compute and store strategy scores in Redis
    """
    
    async def update_strategy_scores(self):
        """
        Recompute strategy scores based on history and update Redis
        Key: ai:strategy_scores
        """
        try:
            metrics = self._analyze_history()
            if not metrics:
                logger.info("Insufficient historical trades for adaptive learning analysis")
                return
            
            scores = {}
            for strategy, m in metrics.items():
                win_rate = m.get('win_rate', 0.5)
                avg_rr = m.get('avg_rr', 1.0)
                
                # Average regime success rate
                regime_success_rates = m.get('regime_success_rate', {})
                avg_regime_success = sum(regime_success_rates.values()) / len(regime_success_rates) if regime_success_rates else win_rate
                
                # Normalize RR for scoring (cap at 3.0 for 100% RR impact score)
                normalized_rr = min(avg_rr / 3.0, 1.0)
                
                # Step 7 Formula: strategy_score = (win_rate * 0.5) + (avg_rr * 0.3) + (regime_success_rate * 0.2)
                # Using our normalized values:
                score = (win_rate * 0.5) + (normalized_rr * 0.3) + (avg_regime_success * 0.2)
                scores[strategy] = round(score, 2)
            
            if scores:
                await cache_service.set("ai:strategy_scores", scores, ttl=86400) # 24h cache
                logger.info(f"Successfully updated AI strategy scores: {scores}")
            
            return scores
                
        except Exception as e:
            logger.error(f"Error in learning analysis: {e}")
            return {}

    def _analyze_history(self) -> Dict[str, Any]:
        """Fetch and analyze trade history from Database"""
        try:
            # Step 6: Analyze ai_trade_history
            query = """
                SELECT strategy, result, pnl, expected_loss, market_regime 
                FROM ai_trade_history 
                WHERE closed_at IS NOT NULL
            """
            rows = ai_db.fetch_query(query)
            
            if not rows:
                return {}
            
            stats = {}
            for row in rows:
                strategy, result, pnl, exp_loss, regime = row
                
                if strategy not in stats:
                    stats[strategy] = {
                        "wins": 0, "total": 0, "total_rr": 0, "regimes": {}
                    }
                
                s = stats[strategy]
                s["total"] += 1
                if result == 'WIN':
                    s["wins"] += 1
                
                # RR Ratio calculation for Step 6
                # RR = Profit / Risk
                rr = (pnl / exp_loss) if exp_loss and exp_loss > 0 else 0
                s["total_rr"] += max(0, rr) # Only positive RR counts for performance
                
                if regime:
                    if regime not in s["regimes"]:
                        s["regimes"][regime] = {"wins": 0, "total": 0}
                    s["regimes"][regime]["total"] += 1
                    if result == 'WIN':
                        s["regimes"][regime]["wins"] += 1
            
            metrics = {}
            for strategy, s in stats.items():
                win_rate = s["wins"] / s["total"] if s["total"] > 0 else 0
                avg_rr = s["total_rr"] / s["total"] if s["total"] > 0 else 0
                
                regime_success = {}
                for r_name, r_data in s["regimes"].items():
                    regime_success[r_name] = r_data["wins"] / r_data["total"] if r_data["total"] > 0 else 0
                
                metrics[strategy] = {
                    "win_rate": win_rate,
                    "avg_rr": avg_rr,
                    "regime_success_rate": regime_success
                }
            
            return metrics
        except Exception as e:
            logger.error(f"History analysis failed: {e}")
            return {}

# Global instance for shared use
adaptive_learning_engine = AdaptiveLearningEngine()
