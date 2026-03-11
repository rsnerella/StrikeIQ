# app/services/analytics_broadcaster.py

"""
Analytics Broadcaster for StrikeIQ
Stable production version
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class AnalyticsBroadcaster:
    """Broadcasts analytics results to websocket clients"""

    def __init__(self):

        self._analytics_task: Optional[asyncio.Task] = None
        self._running = False

        # analytics cache
        self.analytics_cache: Dict[str, Dict[str, Any]] = {}

        # update interval
        self.update_interval = 3.0
        
        # analytics broadcast interval control
        self.ANALYTICS_INTERVAL = 3  # seconds
        self._last_analytics_time = 0

        # engines (lazy loaded)
        self._bias_engine = None
        self._expected_move_engine = None
        self._structural_engine = None
        self._adv_strategies_enabled = True  # Step 14
        self._signal_scoring_enabled = True  # Step 15

    # --------------------------------------------------------
    # ANALYTICS COMPUTATION
    # --------------------------------------------------------

    async def _compute_analytics(
        self, symbol: str, chain_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:

        try:

            # Convert ChainSnapshot to dict if needed
            if not isinstance(chain_data, dict):
                chain_data = {
                    "symbol": getattr(chain_data, "symbol", None),
                    "spot": getattr(chain_data, "spot", None),
                    "atm_strike": getattr(chain_data, "atm_strike", None),
                    "strikes": getattr(chain_data, "strikes", [])
                }

            strikes = chain_data.get("strikes", [])

            logger.info(
                f"COMPUTING ANALYTICS FOR {symbol} - Chain data with {len(strikes)} strikes"
            )

            engine_data = {
                "symbol": symbol,
                "spot": chain_data.get("spot", 0),
                "calls": [],
                "puts": [],
            }

            # Convert strikes
            for strike in strikes:

                if strike.get("call_ltp", 0) > 0:
                    engine_data["calls"].append(
                        {
                            "strike": strike["strike"],
                            "ltp": strike["call_ltp"],
                            "oi": strike.get("call_oi", 0),
                            "volume": strike.get("call_volume", 0),
                        }
                    )

                if strike.get("put_ltp", 0) > 0:
                    engine_data["puts"].append(
                        {
                            "strike": strike["strike"],
                            "ltp": strike["put_ltp"],
                            "oi": strike.get("put_oi", 0),
                            "volume": strike.get("put_volume", 0),
                        }
                    )

            analytics_results = {}

            # -----------------------
            # MARKET BIAS
            # -----------------------

            bias_engine = self._get_bias_engine()

            if bias_engine and engine_data["calls"] and engine_data["puts"]:

                try:

                    logger.debug(f"COMPUTING MARKET BIAS FOR {symbol}")

                    bias = bias_engine.compute(engine_data)

                    analytics_results["bias"] = {
                        "pcr": getattr(bias, "pcr", 0),
                        "bias_strength": getattr(bias, "bias_strength", 0),
                        "price_vs_vwap": getattr(bias, "price_vs_vwap", 0),
                        "divergence_detected": getattr(bias, "divergence_detected", False),
                        "divergence_type": getattr(bias, "divergence_type", "none"),
                    }

                except Exception as e:
                    logger.error(f"Error computing market bias: {e}")

            # -----------------------
            # EXPECTED MOVE
            # -----------------------

            move_engine = self._get_expected_move_engine()

            if move_engine and engine_data["calls"] and engine_data["puts"]:

                try:

                    logger.debug(f"COMPUTING EXPECTED MOVE FOR {symbol}")

                    move = move_engine.compute(engine_data)

                    analytics_results["expected_move"] = {
                        "move_1sd": getattr(move, "expected_move_1sd", 0),
                        "move_2sd": getattr(move, "expected_move_2sd", 0),
                        "breakout_detected": getattr(move, "breakout_detected", False),
                        "breakout_direction": getattr(move, "breakout_direction", "none"),
                        "breakout_strength": getattr(move, "breakout_strength", 0),
                        "implied_volatility": getattr(move, "implied_volatility", 0),
                    }

                except Exception as e:
                    logger.error(f"Error computing expected move: {e}")

            # -----------------------
            # STRUCTURAL ANALYSIS
            # -----------------------

            structural_engine = self._get_structural_engine()

            if structural_engine and engine_data["calls"] and engine_data["puts"]:

                try:

                    logger.debug(f"COMPUTING STRUCTURAL ANALYSIS FOR {symbol}")

                    if self._structural_engine:
                        # Use await for the async method and handle return type
                        structural = await self._structural_engine.compute_symbol_metrics(symbol)
                    else:
                        structural = None

                    if structural:
                        analytics_results["structural"] = {
                            "expected_move": getattr(structural, "expected_move", 0),
                            "upper_1sd": getattr(structural, "upper_1sd", 0),
                            "lower_1sd": getattr(structural, "lower_1sd", 0),
                            "upper_2sd": getattr(structural, "upper_2sd", 0),
                            "lower_2sd": getattr(structural, "lower_2sd", 0),
                            "breach_probability": getattr(structural, "breach_probability", 0),
                            "range_hold_probability": getattr(structural, "range_hold_probability", 0),
                            "gamma_regime": getattr(structural, "gamma_regime", "neutral"),
                            "volatility_regime": getattr(structural, "volatility_regime", "normal"),
                            "support_level": getattr(structural, "support_level", 0),
                            "resistance_level": getattr(structural, "resistance_level", 0),
                            "intent_score": getattr(structural, "intent_score", 0),
                            "oi_velocity": getattr(structural, "oi_velocity", 0),
                            "total_oi": getattr(structural, "total_oi", 0),
                            "net_gamma": getattr(structural, "net_gamma", 0),
                            "gamma_flip_level": getattr(structural, "gamma_flip_level", 0),
                            "distance_from_flip": getattr(structural, "distance_from_flip", 0),
                        }
                    else:
                        analytics_results["structural"] = {}

                except Exception as e:
                    logger.error(f"Error computing structural analysis: {e}")

            # ── STEP 14: Advanced Strategies ──────────────────────────────────
            advanced_payload = None
            signal_payload = None
            if self._adv_strategies_enabled:
                try:
                    from app.services.advanced_strategies_engine import run_advanced_strategies
                    advanced_payload = run_advanced_strategies(symbol, chain_data)
                    analytics_results["advanced_strategies"] = advanced_payload
                except Exception as e:
                    logger.debug(f"Advanced strategies skipped: {e}")

            # ── STEP 15: Signal Scoring ──────────────────────────────────────
            if self._signal_scoring_enabled and advanced_payload:
                try:
                    from app.services.signal_scoring_engine import signal_scoring_engine
                    signal_payload = signal_scoring_engine.score(
                        symbol=symbol,
                        chain_data=chain_data,
                        analytics=analytics_results,
                        advanced=advanced_payload,
                    )
                    analytics_results["signal_score"] = signal_payload
                except Exception as e:
                    logger.debug(f"Signal scoring skipped: {e}")

            analytics_payload = {
                "type": "analytics",
                "version": "2.0",
                "symbol": symbol,
                "timestamp": datetime.utcnow().isoformat(),
                **analytics_results
            }

            # cache store
            self.analytics_cache[symbol] = analytics_payload

            logger.debug(
                f"ANALYTICS COMPUTED FOR {symbol} → {list(analytics_results.keys())}"
            )

            return analytics_payload

        except Exception as e:

            logger.error(f"Error computing analytics for {symbol}: {e}")
            return None

    # --------------------------------------------------------
    # BROADCAST
    # --------------------------------------------------------

    async def _broadcast_analytics(self, analytics_payload: Dict[str, Any]):

        # Ensure payload exists before logging
        if not analytics_payload:
            logger.warning("Analytics payload empty — skipping broadcast")
            return

        try:

            from app.core.ws_manager import manager

            # STEP 13 MONITORING: Analytics broadcast latency tracker
            broadcast_start = time.time()

            try:
                # Ensure correct message type for frontend
                analytics_message = dict(analytics_payload)
                analytics_message["type"] = "analytics_update"
                
                await manager.broadcast(analytics_message)
                broadcast_ms = (time.time() - broadcast_start) * 1000
                logger.info(
                    f"ANALYTICS BROADCAST → {analytics_payload.get('symbol','?')} "
                    f"clients={len(manager.active_connections)} latency={broadcast_ms:.1f}ms"
                )
            except Exception as e:
                logger.error(f"Analytics broadcast failed: {e}")

        except Exception as e:
            logger.error(f"Error broadcasting analytics: {e}")

    # --------------------------------------------------------
    # PUBLIC ACCESS
    # --------------------------------------------------------

    def get_cached_analytics(self, symbol: str):

        return self.analytics_cache.get(symbol)

    async def compute_single_analytics(self, symbol, chain_data):

        return await self._compute_analytics(symbol, chain_data)

    # --------------------------------------------------------
    # BACKGROUND LOOP
    # --------------------------------------------------------

    async def _analytics_loop(self):

        from app.services.option_chain_builder import option_chain_builder
        from app.core.ws_manager import manager
        from app.services.market_status_service import get_market_status

        try:
            while self._running:

                # skip analytics if no websocket clients
                if not manager.active_connections:
                    await asyncio.sleep(1)
                    continue

                # reduce analytics spam when market closed
                status = await get_market_status()
                if status not in ("OPEN", "PREOPEN"):
                    await asyncio.sleep(5)
                    continue

                # rate limit analytics computation
                if time.time() - self._last_analytics_time < self.ANALYTICS_INTERVAL:
                    await asyncio.sleep(0.2)
                    continue

                try:
                    # STEP 13 MONITORING: track analytics tick rate
                    loop_start = time.time()
                    
                    for symbol in ["NIFTY", "BANKNIFTY"]:
                        chain_data = option_chain_builder.get_chain(symbol)
                        
                        if chain_data:
                            analytics = await self._compute_analytics(symbol, chain_data)
                            
                            if analytics:
                                await self._broadcast_analytics(analytics)

                                # ── Step 14/15: broadcast advanced + score separately ──
                                adv = analytics.get("advanced_strategies")
                                score = analytics.get("signal_score")

                                # Parallel broadcast all analytics components
                                broadcast_tasks = []
                                
                                if adv:
                                    broadcast_tasks.append(manager.broadcast(adv))
                                
                                if score:
                                    broadcast_tasks.append(manager.broadcast(score))

                                # ── Chart Intelligence (Steps 2–9) ────────────────
                                try:
                                    from app.services.chart_signal_engine import chart_signal_engine
                                    from app.services.signal_outcome_tracker import signal_outcome_tracker
                                    spot = chain_data.get("spot", 0)
                                    if spot > 0:
                                        chart_payload = chart_signal_engine.analyze(
                                            symbol=symbol,
                                            current_price=spot,
                                            chain_data=chain_data,
                                            options_analytics=analytics,
                                        )
                                        if chart_payload and chart_payload.get("signal") != "WAIT":
                                            broadcast_tasks.append(manager.broadcast(chart_payload))
                                            signal_outcome_tracker.record_signal(
                                                chart_payload,
                                                extra={
                                                    "pcr": chain_data.get("pcr", 0),
                                                    "signal_score": (score or {}).get("score", 0),
                                                }
                                            )
                                            
                                            # AI ML Prediction Integration
                                            try:
                                                from app.services.feature_builder import feature_builder
                                                from app.services.probability_engine import probability_engine
                                                features = feature_builder.build_features({**chart_payload, "pcr": chain_data.get("pcr", 0)})
                                                if features:
                                                    ai_prediction = probability_engine.predict(symbol, features)
                                                    if ai_prediction:
                                                        broadcast_tasks.append(manager.broadcast(ai_prediction))
                                            except Exception as ai_e:
                                                logger.debug(f"AI ML Pipeline error: {ai_e}", exc_info=True)

                                        await signal_outcome_tracker.evaluate_pending(symbol, spot)
                                except Exception as e:
                                    logger.debug(f"Chart signal engine skipped: {e}")

                                # Execute all broadcasts in parallel
                                if broadcast_tasks:
                                    try:
                                        await asyncio.gather(*broadcast_tasks, return_exceptions=True)
                                    except Exception as e:
                                        logger.debug(f"Parallel broadcast failed: {e}")

                        else:
                            logger.debug(f"No chain data yet for {symbol} — skipping analytics")
                    
                    self._last_analytics_time = time.time()
                    elapsed = (time.time() - loop_start) * 1000
                    logger.debug(f"ANALYTICS LOOP → elapsed={elapsed:.1f}ms clients={len(manager.active_connections)}")
                    
                except Exception as e:
                    logger.error(f"Analytics build failed: {e}")
                    await asyncio.sleep(1)
                    continue

        except asyncio.CancelledError:
            logger.info("Analytics broadcaster stopped gracefully")
            raise

    # --------------------------------------------------------
    # START / STOP
    # --------------------------------------------------------

    async def start(self):

        if self._running:
            return

        self._running = True
        self._analytics_task = asyncio.create_task(self._analytics_loop())

        logger.info("Analytics broadcaster started")

    async def stop(self):

        self._running = False

        if self._analytics_task:

            self._analytics_task.cancel()

            try:
                await self._analytics_task
            except asyncio.CancelledError:
                pass

        logger.info("Analytics broadcaster stopped")

    # --------------------------------------------------------
    # ENGINE LOADERS
    # --------------------------------------------------------

    def _get_bias_engine(self):

        if self._bias_engine is None:

            try:
                from app.services.market_bias_engine import MarketBiasEngine

                self._bias_engine = MarketBiasEngine()

            except ImportError as e:
                logger.error(f"Could not import MarketBiasEngine: {e}")

        return self._bias_engine

    def _get_expected_move_engine(self):

        if self._expected_move_engine is None:

            try:
                from app.services.expected_move_engine import ExpectedMoveEngine

                self._expected_move_engine = ExpectedMoveEngine()

            except ImportError as e:
                logger.error(f"Could not import ExpectedMoveEngine: {e}")

        return self._expected_move_engine

    def _get_structural_engine(self):

        if self._structural_engine is None:

            try:
                from app.services.live_structural_engine import LiveStructuralEngine
                from app.core.live_market_state import get_market_state_manager
                market_state_mgr = get_market_state_manager()
                structural_engine = LiveStructuralEngine(market_state_mgr)
            except Exception as e:
                logger.warning("Structural engine unavailable: %s", e)
                structural_engine = None
            
            self._structural_engine = structural_engine

        return self._structural_engine


# --------------------------------------------------------
# GLOBAL INSTANCE (IMPORTANT)
# --------------------------------------------------------

analytics_broadcaster = AnalyticsBroadcaster()