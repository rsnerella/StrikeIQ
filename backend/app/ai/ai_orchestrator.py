"""
AI Orchestrator - Institutional-Grade Engine Coordinator
Implements the 10-step AI pipeline for the Elite Engine architecture.
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from dataclasses import asdict

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

# Import Chart Intelligence Engine
from ..chart_intelligence.engine import chart_intelligence_engine

# Institutional Layer Integrations (backend/ai/)
# New AI modules - use try/except for graceful fallback
try:
    from ai.feature_engine import FeatureEngine
    from ai.bias_model import BiasModel
    from ai.strategy_decision_engine import StrategyDecisionEngine
    from ai.options_trade_engine import OptionsTradeEngine
    NEW_AI_MODULES_AVAILABLE = True
except ImportError:
    NEW_AI_MODULES_AVAILABLE = False

# Legacy AI modules - optional
try:
    from ai.dealer_gamma_engine import DealerGammaEngine
    from ai.liquidity_engine import LiquidityEngine
    from ai.gamma_squeeze_engine import GammaSqueezeEngine
    from ai.options_trade_engine import generate_option_trade
    from ai.entry_exit_engine import EntryExitEngine
except ImportError:
    # Fallback for different import paths
    try:
        from ..ai.dealer_gamma_engine import DealerGammaEngine
        from ..ai.liquidity_engine import LiquidityEngine
        from ..ai.gamma_squeeze_engine import GammaSqueezeEngine
        from ..ai.options_trade_engine import generate_option_trade
        from ..ai.entry_exit_engine import EntryExitEngine
    except ImportError:
        # Set to None if none available
        DealerGammaEngine = None
        LiquidityEngine = None
        GammaSqueezeEngine = None
        generate_option_trade = None
        EntryExitEngine = None

logger = logging.getLogger(__name__)

class AIOrchestrator:
    """
    Master coordinator for the AI pipeline.
    Ensures absolute performance (<100ms) and follows the 10-step cycle.
    """
    
    def __init__(self, db_session=None):
        self.db_session = db_session
        self._last_cycle_time = 0
        
        # Initialize Institutional Engines (with None checks)
        self.dealer_gamma = DealerGammaEngine() if DealerGammaEngine else None
        self.liquidity_engine = LiquidityEngine() if LiquidityEngine else None
        self.gamma_squeeze = GammaSqueezeEngine() if GammaSqueezeEngine else None
        self.entry_exit = EntryExitEngine() if EntryExitEngine else None
        
        logger.info("Institutional AI Orchestrator initialized with available engines")

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
            
            # 4.1 Institutional Gamma Analysis (Law 1 Alignment)
            gamma_metrics = {
                "net_gamma": fv.net_gamma,
                "gamma_flip_level": analysis.key_levels.get("gex_flip", 0),
                "spot_price": snapshot.spot
            }
            inst_gamma = self.dealer_gamma.analyze(gamma_metrics)
            
            # 4.2 Squeeze & Liquidity Scanning
            inst_metrics = {
                "spot": snapshot.spot,
                "net_gamma": fv.net_gamma,
                "gamma_flip_level": analysis.key_levels.get("gex_flip", 0),
                "distance_from_flip": abs(snapshot.spot - analysis.key_levels.get("gex_flip", 0)),
                "flow_direction": "call" if fv.pcr_ratio < 0.8 else "put" if fv.pcr_ratio > 1.2 else "neutral",
                "flow_imbalance": abs(1.0 - fv.pcr_ratio),
                "oi_velocity": fv.oi_velocity if hasattr(fv, 'oi_velocity') else 0,
                "volatility_regime": analysis.volatility_state.get("state", "normal"),
                "support_level": analysis.key_levels.get("put_wall", 0),
                "resistance_level": analysis.key_levels.get("call_wall", 0),
                "expected_move": analysis.volatility_state.get("iv_atm", 0) * snapshot.spot * 0.02 # Proxy
            }
            squeeze_data = self.gamma_squeeze.analyze(inst_metrics)
            liquidity_data = self.liquidity_engine.analyze(inst_metrics)

            # 5. Early Warning Scan (Merge with institutional squeeze alerts)
            alerts = early_warning_engine.scan(fv, snapshot, analysis)
            if squeeze_data.get("signal") != "NONE":
                from .early_warning_engine import EarlyWarningSignal
                alerts.append(EarlyWarningSignal(
                    alert_type="GAMMA_SQUEEZE",
                    severity="HIGH" if squeeze_data.get("confidence", 0) > 0.7 else "MEDIUM",
                    probability_move=squeeze_data.get("confidence", 0),
                    direction_bias=squeeze_data.get("direction", "NEUTRAL"),
                    description=squeeze_data.get("reason", ""),
                    suggested_action="Prepare for rapid directional expansion",
                    timestamp=int(time.time())
                ))

            # 6. Confidence Scoring (Weighting conviction)
            confidence = confidence_scoring_engine.score(fv, view_5m, view_15m, analysis, alerts)
            
            # 7. Model Drift Monitoring
            drift = model_drift_monitor.observe(fv)
            # Adjust confidence based on drift
            confidence = max(0.0, confidence * (1.0 - drift))
            
            # 8. Trade Planning (Execution strategy - Law 1 Alignment)
            # Use institutional option trade engine for real strikes
            opt_trade = generate_option_trade(snapshot, snapshot)
            plan = trade_planner.plan(symbol, analysis, confidence)
            
            # Merge opt_trade into plan if available
            if opt_trade and plan:
                plan_dict = plan.to_dict() if hasattr(plan, 'to_dict') else asdict(plan) if not isinstance(plan, dict) else plan
                plan_dict.update({
                    "strike": opt_trade["strike"],
                    "direction": opt_trade["option_type"],
                    "entry": opt_trade["entry"],
                    "stop_loss": opt_trade["stop_loss"],
                    "target": opt_trade["target"],
                    "reason": plan_dict.get("reason", []) + [opt_trade["signal_text"]]
                })
                plan = plan_dict
            elif plan:
                plan = plan.to_dict() if hasattr(plan, 'to_dict') else asdict(plan) if not isinstance(plan, dict) else plan

            # 9. News Event Engine (Institutional Sentiment Overlay)
            news_analysis = await news_event_engine.analyze(symbol)
            sentiment_overlay = {
                "sentiment": news_analysis.get("sentiment_overlay"),
                "news_impact": news_analysis.get("news_impact_bias"),
                "status": news_analysis.get("status")
            }
            
            # 9.5. Chart Intelligence Engine (Pattern Detection & Overlay Objects)
            chart_intelligence = None
            try:
                # Get candle data for chart intelligence (from history store)
                candle_data = []
                for hist_snapshot in snapshots[-200:]:  # Last 200 snapshots
                    if 'candle' in hist_snapshot:
                        candle_data.append(hist_snapshot['candle'])
                
                # Get options data for integration
                options_data = {
                    'call_wall': analysis.key_levels.get("call_wall", 0),
                    'put_wall': analysis.key_levels.get("put_wall", 0),
                    'pcr_ratio': fv.pcr_ratio if hasattr(fv, 'pcr_ratio') else 1.0,
                    'gex_flip_level': analysis.key_levels.get("gex_flip", 0),
                    'net_gamma': fv.net_gamma if hasattr(fv, 'net_gamma') else 0,
                    'total_call_oi': fv.total_call_oi if hasattr(fv, 'total_call_oi') else 0,
                    'total_put_oi': fv.total_put_oi if hasattr(fv, 'total_put_oi') else 0,
                    'max_pain': analysis.key_levels.get("max_pain", snapshot.spot),
                    'iv_atm': analysis.volatility_state.get("iv_atm", 0.20)
                }
                
                if candle_data:
                    chart_result = chart_intelligence_engine.analyze(candle_data, options_data)
                    chart_intelligence = {
                        "market_structure": chart_result.market_structure,
                        "pattern_detected": chart_result.pattern_detected,
                        "confidence": chart_result.confidence,
                        "overlay_objects": [asdict(obj) for obj in chart_result.overlay_objects],
                        "analysis_summary": chart_result.analysis_summary,
                        "options_context": chart_result.options_context,
                        "processing_time_ms": chart_result.processing_time_ms
                    }
            except Exception as e:
                logger.warning(f"Chart Intelligence analysis failed for {symbol}: {e}")
                chart_intelligence = {"error": str(e), "status": "CHART_INTELLIGENCE_ERROR"}
            
            # 10. Final Payload Assembly (Aligned with v5.0 Contract)
            elapsed_ms = (time.monotonic() - t0) * 1000
            self._last_cycle_time = elapsed_ms
            
            payload = {
                "symbol": symbol,
                "timestamp": int(time.time()),
                "status": "AI_READY",
                "ai_ready": True,
                "cycle_time_ms": round(elapsed_ms, 2),
                
                # 🔥 ADD PERFORMANCE DATA
                "performance": self.execution_engine.get_performance(),
                "analytics_full": self.execution_engine.get_full_analytics(),
                "strategy_weights": self.execution_engine.strategy_weights,
                
                "market_analysis": {
                    "regime": analysis.regime,
                    "bias": analysis.bias,
                    "bias_strength": analysis.bias_strength,
                    "key_levels": analysis.key_levels,
                    "gamma_analysis": {
                        "net_gex": inst_gamma.get("strength") * (1 if inst_gamma.get("direction") == "UP" else -1) if inst_gamma.get("direction") != "NONE" else fv.net_gamma,
                        "regime": inst_gamma.get("signal", "GAMMA_NEUTRAL"),
                        "flip_level": analysis.key_levels.get("gex_flip"),
                        "implication": inst_gamma.get("reason", "Stable positioning")
                    },
                    "volatility_state": analysis.volatility_state,
                    "technical_state": {
                        "rsi": fv.rsi if hasattr(fv, 'rsi') else 50.0,
                        "momentum_15m": fv.momentum,
                        "liquidity_signal": liquidity_data.get("signal", "NONE"),
                        "pattern": analysis.regime
                    },
                    "summary": analysis.summary
                },
                
                "early_warnings": [a.to_dict() if hasattr(a, 'to_dict') else a for a in alerts],
                "trade_plan": plan if isinstance(plan, dict) else plan.to_dict(),
                "confidence_score": round(confidence, 3),
                "sentiment_overlay": sentiment_overlay,
                "chart_intelligence": chart_intelligence
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

