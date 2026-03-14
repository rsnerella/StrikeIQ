# app/services/analytics_broadcaster.py

"""
Analytics Broadcaster for StrikeIQ
Stable production version
"""

import asyncio
import logging
import time
import json
from datetime import datetime, date
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Global analytics cache to serve snapshots immediately to new clients
LAST_ANALYTICS: Dict[str, Any] = {}

def json_safe(obj):
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    return str(obj)


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
        self.ANALYTICS_INTERVAL = 0.5  # Real-time institutional cycle (500ms)
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
            # PATCH 2: FIX ANALYTICS ENGINE INPUT
            if not isinstance(chain_data, dict):
                if hasattr(chain_data, "to_dict"):
                    chain_data = chain_data.to_dict()
                elif hasattr(chain_data, "__dict__"):
                    chain_data = chain_data.__dict__

            logger.info(f"ANALYTICS ENGINE RUNNING → {symbol}")
            
            # Use chain_data as dict from here on
            chain_dict = chain_data
            
            # Fallback extraction if missing fields
            if "strikes" not in chain_dict and hasattr(chain_dict, "strikes"):
                 chain_dict["strikes"] = chain_dict.strikes

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
                            "spot": getattr(structural, "spot", 0),
                            "open": getattr(structural, "open", 0),
                            "prev_close": getattr(structural, "prev_close", 0),
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
                            "dealer_positioning": getattr(structural, "dealer_positioning", "neutral"),
                            "options_trap": getattr(structural, "options_trap", {}),
                            "liquidity_vacuum": getattr(structural, "liquidity_vacuum", {}),
                            "expiry_magnet_analysis": getattr(structural, "expiry_magnet_analysis", {}),
                            "gamma_pressure_map": getattr(structural, "gamma_pressure_map", {}),
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

            # ── Option Trade Engine (AI Real Options) ──────────────────────────────────
            try:
                from ai.options_trade_engine import generate_option_trade
                snapshot = {
                    "symbol": symbol,
                    "spot_price": engine_data["spot"],
                    "pcr": pcr
                }
                option_trade = generate_option_trade(snapshot, chain_data)
                if option_trade:
                    analytics_results["trade_setup"] = option_trade
                    logger.info(f"AI OPTION TRADE GENERATED → {option_trade['symbol']} {option_trade['strike']} {option_trade['type']}")
            except Exception as e:
                logger.debug(f"AI option trade engine skipped: {e}")

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

            # PHASE 8: Bundle full professional payload
            from app.services.option_chain_builder import option_chain_builder
            from app.services.candle_builder import candle_builder
            
            # Fetch additional components for bundling
            chain_snapshot = option_chain_builder.get_chain(symbol)
            candles_1m = candle_builder.get_candles_as_dicts(symbol, "1m", 100)
            
            analytics_payload = {
                "type": "analytics_update",
                "version": "3.0 PRO",
                "symbol": symbol,
                "timestamp": int(time.time()),
                "data": {
                    "snapshot": {
                        "spot": engine_data["spot"],
                        "pcr": pcr,
                        "total_call_oi": total_call_oi,
                        "total_put_oi": total_put_oi,
                        "gamma_exposure": analytics_results.get("structural", {}).get("net_gamma", 0),
                        "expected_move": analytics_results.get("expected_move", {}).get("move_1sd", 0)
                    },
                    "analytics": analytics_results,
                    "option_chain": chain_snapshot.__dict__ if hasattr(chain_snapshot, '__dict__') else chain_snapshot,
                    "trade_setup": analytics_results.get("trade_setup"),
                    "candles": candles_1m,
                    "ai_signals": analytics_results.get("ai_signal")
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

    async def compute_single_analytics(self, symbol: str, chain_data=None):
        """
        Triggered by option_chain_builder after chain update.
        Runs one analytics compute cycle for the given symbol immediately.
        This is the bridge between chain updates and broadcast output.
        """
        try:
            logger.debug(f"ANALYTICS TRIGGERED → {symbol}")
            
            # Compute analytics for the symbol
            analytics_payload = await self._compute_analytics(symbol, chain_data)
            
            if analytics_payload:
                # Broadcast the results
                await self._broadcast_analytics(analytics_payload)
                logger.debug(f"ANALYTICS COMPLETED → {symbol}")
            else:
                logger.warning(f"ANALYTICS FAILED → {symbol} (no payload)")

        except Exception as e:
            logger.error(f"compute_single_analytics failed for {symbol}: {e}")

    async def _broadcast_analytics(self, analytics_payload):
        """Broadcast analytics results to WebSocket clients"""
        try:
            symbol = analytics_payload.get("symbol")
            data = analytics_payload.get("data", {})
            
            # FIX 6: Ensure payload format matches frontend store expectations
            snapshot = data.get("snapshot", {})
            analytics = data.get("analytics", {})
            option_chain = data.get("option_chain", {})
            candles = data.get("candles", [])
            ai_signals = data.get("ai_signals", {})
            
            # Create unified analytics_update message as specified in requirements
            unified_message = {
                "type": "analytics_update",
                "symbol": symbol,
                "snapshot": snapshot,
                "analytics": analytics,
                "option_chain": option_chain,
                "candles": candles,
                "ai_signals": ai_signals,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Cache analytics snapshot for new connections
            global LAST_ANALYTICS
            if symbol:
                # Phase 8: Store full bundled payload
                LAST_ANALYTICS[symbol] = unified_message
            
            # PATCH 3: FIX DATETIME SERIALIZATION
            payload_json = json.dumps(unified_message, default=json_safe)
            await manager.broadcast(payload_json)
            
            broadcast_ms = (time.time() - broadcast_start) * 1000
            logger.info(
                f"ANALYTICS BROADCAST → {symbol} "
                f"clients={len(manager.active_connections)} latency={broadcast_ms:.1f}ms"
            )
        except Exception as e:
            logger.error(f"Error broadcasting analytics: {e}")

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

    async def start(self):
        """
        Start analytics loop safely.
        Prevent duplicate loops.
        """
        if getattr(self, "_running", False):
            return

        self._running = True
        logger.info("Analytics broadcaster started")

        async def _loop():
            while self._running:
                try:
                    await asyncio.sleep(0.5)
                except Exception as e:
                    logger.error(f"Analytics loop error: {e}")

        self._analytics_task = asyncio.create_task(_loop())

    async def stop(self):

        self._running = False

        if self._analytics_task:

            self._analytics_task.cancel()

        try:
            await asyncio.wait_for(self._analytics_task, timeout=5)
        except asyncio.TimeoutError:
            logger.warning("Analytics task did not stop within 5 seconds")

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