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

# Global analytics cache to serve snapshots immediately to new clients
LAST_ANALYTICS: Dict[str, Any] = {}


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
        
        # hash cache for deduplication
        self._last_analytics_hash: Dict[str, str] = {}
        self._last_broadcast_times: Dict[str, float] = {}

    # --------------------------------------------------------
    # ANALYTICS COMPUTATION
    # --------------------------------------------------------

    async def _compute_analytics(
        self, symbol: str, chain_data
    ) -> Optional[Dict[str, Any]]:

        try:

            logger.info(f"ANALYTICS ENGINE RUNNING → {symbol}")
            logger.info(f"CHAIN DEBUG → chain_data type: {type(chain_data)}")

            # Handle both ChainSnapshot object and dict
            if hasattr(chain_data, '__dict__'):
                # ChainSnapshot object - convert to dict
                chain_dict = {
                    "symbol": getattr(chain_data, "symbol", None),
                    "spot": getattr(chain_data, "spot", None),
                    "atm_strike": getattr(chain_data, "atm_strike", None),
                    "strikes": getattr(chain_data, "strikes", []),
                    "pcr": getattr(chain_data, "pcr", 0),
                    "total_oi_calls": getattr(chain_data, "total_oi_calls", 0),
                    "total_oi_puts": getattr(chain_data, "total_oi_puts", 0)
                }
            else:
                # Already a dict
                chain_dict = chain_data

            strikes = chain_dict.get("strikes", [])
            
            logger.info(f"COMPUTING ANALYTICS FOR {symbol} - Chain data with {len(strikes)} strikes")
            logger.info(f"CHAIN DEBUG strikes sample {strikes[:3] if strikes else 'EMPTY'}")

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

            # Calculate PCR and total OI from ChainSnapshot if available
            pcr = chain_dict.get("pcr", 0)
            total_call_oi = chain_dict.get("total_oi_calls", 0)
            total_put_oi = chain_dict.get("total_oi_puts", 0)
            
            if pcr == 0 and strikes:
                # Fallback PCR calculation
                total_call_oi = sum(strike.get("call_oi", 0) for strike in strikes)
                total_put_oi = sum(strike.get("put_oi", 0) for strike in strikes)
                pcr = total_put_oi / total_call_oi if total_call_oi > 0 else 0.0
            
            logger.info(f"SNAPSHOT CREATED → PCR={pcr} CALL_OI={total_call_oi} PUT_OI={total_put_oi}")

            analytics_results = {
                "pcr": pcr,
                "total_call_oi": total_call_oi,
                "total_put_oi": total_put_oi,
                "total_oi": total_call_oi + total_put_oi
            }

            # -----------------------
            # MARKET BIAS
            # -----------------------

            bias_engine = self._get_bias_engine()

            if bias_engine and engine_data["calls"] and engine_data["puts"]:

                try:

                    logger.debug(f"COMPUTING MARKET BIAS FOR {symbol}")

                    bias = bias_engine.compute(engine_data)
                    
                    # CRITICAL FIX: Extract bias_value correctly from bias object
                    bias_value = getattr(bias, "bias_strength", 0) if hasattr(bias, 'bias_strength') else bias.get("bias_strength", 0)

                    analytics_results["bias"] = {
                        "pcr_value": float(getattr(bias, "pcr_value", 1.0)),
                        "bias_strength": bias_value,
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

            # ── Trade Setup Engine (Rule Based Fallback) ──────────────────────────────────────
            try:
                from app.services.trade_setup_engine import trade_setup_engine
                trade_setup = trade_setup_engine.compute(
                    symbol=symbol,
                    spot=engine_data["spot"],
                    chain_data=chain_data,
                    analytics=analytics_results,
                )
                if trade_setup:
                    analytics_results["trade_setup"] = trade_setup
            except Exception as e:
                logger.debug(f"Trade setup skipped: {e}")

            # ── AI Signal Integration (Primary) ──────────────────────────────────────
            try:
                from app.services.ai_signal_engine import ai_signal_engine
                ai_signal = await ai_signal_engine.get_latest_signal(symbol)
                if ai_signal:
                    analytics_results["ai_signal"] = ai_signal
                    # Map to trade_suggestion for frontend compatibility
                    analytics_results["trade_suggestion"] = {
                        "signal": "BULLISH" if ai_signal["direction"] == "CALL" else "BEARISH",
                        "direction": ai_signal["direction"],
                        "strike": ai_signal["strike"],
                        "entry": ai_signal["entry"],
                        "target": ai_signal["target"],
                        "stop_loss": ai_signal["stop_loss"],
                        "confidence": ai_signal["confidence"],
                        "reason": ai_signal.get("signal_reason")
                    }
            except Exception as e:
                logger.debug(f"AI signal fetch failed: {e}")

            analytics_payload = {
                "type": "analytics_update",
                "version": "2.0",
                "symbol": symbol,
                "timestamp": int(time.time()),
                "data": {
                    **analytics_results,
                    "bias": analytics_results.get("bias", {}),
                    "expected_move": analytics_results.get("expected_move", {}),
                    "structural": analytics_results.get("structural", {})
                }
            }
            
            logger.info(f"ANALYTICS PAYLOAD → {analytics_payload}")

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

        import json
        import hashlib
        
        symbol = analytics_payload.get("symbol")
        
        # Phase 5: Rate Limit (2 seconds)
        now = time.time()
        if symbol in self._last_broadcast_times:
            if now - self._last_broadcast_times[symbol] < 2.0:
                return # Skip broadcast if too frequent
        
        # Hash check to prevent flood
        payload_str = json.dumps(analytics_payload.get("data", {}), sort_keys=True)
        payload_hash = hashlib.md5(payload_str.encode()).hexdigest()
        
        if self._last_analytics_hash.get(symbol) == payload_hash:
            return  # Skip identical broadcasts
            
        self._last_analytics_hash[symbol] = payload_hash
        self._last_broadcast_times[symbol] = now

        try:

            from app.core.ws_manager import manager

            # STEP 13 MONITORING: Analytics broadcast latency tracker
            broadcast_start = time.time()

            try:
                # Create correct frontend-compatible payload
                analytics_message = {
                    "type": "analytics_update",
                    "symbol": analytics_payload.get("symbol"),
                    "timestamp": analytics_payload.get("timestamp", int(time.time())),
                    "data": {
                        "analytics": analytics_payload.get("data", analytics_payload)
                    }
                }
                
                logger.info(f"ANALYTICS BROADCAST SUCCESS → {analytics_payload.get('symbol','?')}")
                logger.info(f"FINAL PAYLOAD → {analytics_message}")
                
                # Cache analytics snapshot for new connections
                global LAST_ANALYTICS
                if symbol:
                    LAST_ANALYTICS[symbol] = analytics_message
                
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

        analytics_payload = await self._compute_analytics(symbol, chain_data)
        
        if analytics_payload:
            logger.info(f"ANALYTICS ENGINE → computed metrics {symbol}")
            await self._broadcast_analytics(analytics_payload)
            logger.info(f"ANALYTICS BROADCAST → {symbol}")
            
            # Return pure analytics data (not wrapped)
            return analytics_payload.get("data", {})
        else:
            logger.warning(f"ANALYTICS ENGINE → failed to compute metrics {symbol}")
            return None

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
                                        if chart_payload:
                                            broadcast_tasks.append(manager.broadcast(chart_payload))
                                            await signal_outcome_tracker.record_signal(
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

                                # ── Candle broadcasting ───────────────────────
                                try:
                                    from app.services.candle_builder import candle_builder
                                    for tf in ["1m", "5m"]:
                                        past_candles = candle_builder.get_candles_as_dicts(symbol, tf, 300)
                                        current = candle_builder.get_current_candle(symbol, tf)
                                        combo = list(past_candles)
                                        if current:
                                            combo.append(current)
                                            
                                        if combo:
                                            broadcast_tasks.append(manager.broadcast({
                                                "type": "candle_update",
                                                "symbol": symbol,
                                                "timeframe": tf,
                                                "candles": combo
                                            }))
                                except Exception as e:
                                    logger.debug(f"Candle broadcast skipped: {e}")

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