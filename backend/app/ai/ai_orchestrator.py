"""
AI Orchestrator - Institutional-Grade Engine Coordinator
Implements the 10-step AI pipeline for the Elite Engine architecture.
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

# Import core processing and storage
from .history_store import history_store
from app.data.processing.feature_engineer import feature_engineering_engine
from app.data.processing.timeframe_aggregator import timeframe_aggregator

# Import AI analysis engines
from .market_analysis_engine import market_analysis_engine
from .early_warning_engine import early_warning_engine
from .confidence_scorer import confidence_scoring_engine
from .drift_monitor import model_drift_monitor
from .trade_planner import trade_planner
from .news_event_engine import news_event_engine

logger = logging.getLogger(__name__)

class AIOrchestrator:
    """
    Master coordinator for the AI pipeline.
    Ensures absolute performance (<100ms) and follows the 10-step cycle.
    """
    
    def __init__(self, db_session=None):
        self.db_session = db_session
        self._last_cycle_time = 0
        logger.info("Institutional AI Orchestrator initialized")

    async def run_cycle(self, symbol: str, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the full 10-step AI pipeline for a single market snapshot.
        
        Args:
            symbol: Target instrument (NIFTY, BANKNIFTY, etc.)
            snapshot: Current normalized market snapshot (1s or tick)
            
        Returns:
            Complete AI response payload
        """
        t0 = time.monotonic()
        
        try:
            # 1. Store snapshot in bounded history
            history_store.append(symbol, snapshot)
            snapshots = history_store.get_history(symbol)
            
            # 2. Compute MarketFeatureVector
            fv = feature_engineering_engine.compute(symbol, snapshots)
            if not fv:
                return self._idle_response(symbol, "Insufficient history for features")
            
            # 3. Timeframe Aggregation
            view_5m = timeframe_aggregator.get_5m_view(snapshots)
            view_15m = timeframe_aggregator.get_15m_view(snapshots)
            
            # 4. Market Analysis (Regime + Bias + Levels)
            analysis = market_analysis_engine.analyze(fv, snapshot)
            
            # 5. Early Warning Scan (Severity alerts)
            alerts = early_warning_engine.scan(fv, snapshot, analysis)
            
            # 6. Confidence Scoring (Weighting conviction)
            confidence = confidence_scoring_engine.score(fv, view_5m, view_15m, analysis, alerts)
            
            # 7. Model Drift Monitoring
            drift = model_drift_monitor.observe(fv)
            # Adjust confidence based on drift
            confidence = max(0.0, confidence * (1.0 - drift))
            
            # 8. Trade Planning (Execution strategy)
            plan = trade_planner.plan(symbol, analysis, confidence)
            
            # 9. News Event Engine (Institutional Sentiment Overlay)
            news_analysis = await news_event_engine.analyze(symbol)
            sentiment_overlay = {
                "sentiment": news_analysis.get("sentiment_overlay"),
                "news_impact": news_analysis.get("news_impact_bias"),
                "status": news_analysis.get("status")
            }
            
            # 10. Final Payload Assembly
            elapsed_ms = (time.monotonic() - t0) * 1000
            self._last_cycle_time = elapsed_ms
            
            payload = {
                "symbol": symbol,
                "timestamp": int(time.time()),
                "status": "AI_READY",
                "cycle_time_ms": round(elapsed_ms, 2),
                "regime": analysis.regime,
                "bias": analysis.bias,
                "bias_strength": analysis.bias_strength,
                "confidence_score": round(confidence, 3),
                "drift_score": round(drift, 3),
                "key_levels": analysis.key_levels,
                "early_warnings": [a.to_dict() for a in alerts],
                "trade_plan": plan.to_dict() if hasattr(plan, 'to_dict') else plan,
                "market_summary": f"{analysis.regime} market with {analysis.bias} bias",
                "volatility_state": analysis.vol_state,
                "sentiment_overlay": sentiment_overlay
            }
            
            if elapsed_ms > 100:
                logger.warning(f"AI Cycle Budget Exceeded: {elapsed_ms:.2f}ms for {symbol}")
            
            return payload
            
        except Exception as e:
            logger.error(f"AI Pipeline Crash for {symbol}: {e}", exc_info=True)
            return self._error_response(symbol, str(e))

    def _idle_response(self, symbol: str, reason: str) -> Dict[str, Any]:
        return {
            "symbol": symbol,
            "status": "AI_WAITING",
            "reason": reason,
            "timestamp": int(time.time())
        }

    def _error_response(self, symbol: str, error: str) -> Dict[str, Any]:
        return {
            "symbol": symbol,
            "status": "AI_ERROR",
            "error": error,
            "timestamp": int(time.time())
        }

# Global singleton
ai_orchestrator = AIOrchestrator()

