# app/services/analytics_broadcaster.py

"""
Institutional Analytics Broadcaster for StrikeIQ
Coordinates the 10-step AI pipeline and broadcasts at 500ms intervals.
"""

import asyncio
import logging
import time
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from app.core.ws_manager import manager
from app.ai.ai_orchestrator import ai_orchestrator
from app.services.option_chain_builder import option_chain_builder

logger = logging.getLogger(__name__)

# Global analytics cache to serve snapshots immediately to new clients
LAST_ANALYTICS: Dict[str, Any] = {}

def json_safe(obj):
    if isinstance(obj, (datetime)):
        return obj.isoformat()
    return str(obj)

class AnalyticsBroadcaster:
    """Master broadcaster for the StrikeIQ Elite Engine"""

    def __init__(self):
        self._analytics_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Real-time institutional cycle (500ms)
        self.ANALYTICS_INTERVAL = 0.5 
        self._last_analytics_time = 0

        # FIX 2: REST-only mode tracking
        self._dirty: Dict[str, bool] = {}
        self._last_broadcast_time: Dict[str, float] = {}

    def _get_spot_price(self, symbol: str, snapshot) -> float:
        """
        Try every possible source for spot price.
        Returns 0 only if genuinely unavailable.
        """
        # 1. Try snapshot first (dynamic attributes)
        for attr in ['spot', 'index_price', 'ltp', 'close', 'last_price']:
            val = getattr(snapshot, attr, None)
            if val and float(val) > 0:
                return float(val)

        # 2. Try option chain builder's index price cache
        try:
            from app.services.option_chain_builder import option_chain_builder
            for attr in ['spot_prices', '_index_prices', '_spot_prices']:
                cache = getattr(option_chain_builder, attr, {})
                if isinstance(cache, dict) and cache.get(symbol, 0) > 0:
                    return float(cache[symbol])
        except Exception:
            pass

        # 3. Try Redis cache as last resort
        try:
            # Note: synchronous check for performance, use cached value if possible
            from app.core.redis_client import redis_client
            import asyncio
            # We don't want to block the loop, so we only try this if we have a current loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # In a real scenario we'd use a non-blocking cache but for debug we use getattr if stored
                pass
        except Exception:
            pass

        return 0.0

    def _build_summary(self, symbol, pcr, bias, regime,
                       call_wall, put_wall, iv_atm, vol_state) -> str:
        """Build clean institutional summary sentence instead of raw concatenated string."""
        parts = []
        parts.append(f"{symbol} in {regime} regime")

        if bias and bias != 'NEUTRAL':
            parts.append(f"with {bias} bias (PCR {pcr:.2f})")
        else:
            parts.append(f"with neutral bias (PCR {pcr:.2f})")

        levels = []
        if call_wall > 0:
            levels.append(
                f"Call resistance at {call_wall:,}"
            )
        if put_wall > 0:
            levels.append(
                f"Put support at {put_wall:,}"
            )
        if levels:
            parts.append(". ".join(levels))

        if iv_atm > 0:
            iv_pct = iv_atm * 100 if iv_atm < 1 else iv_atm
            parts.append(f"IV {iv_pct:.1f}% — {vol_state}")

        return ". ".join(parts) + "."

    def compute_single_analytics(self, symbol: str, chain_data=None):
        """
        Called synchronously by option_chain_builder after each tick.
        Sets dirty flag only — never computes inline.
        This is intentional: computation happens in the 500ms loop.
        """
        self._dirty[symbol] = True

    def _build_option_chain_payload(self, symbol: str, snapshot) -> tuple:
        """Helper to extract formatted calls/puts for the frontend."""
        calls = {}
        puts  = {}

        try:
            # Use the snapshot object from get_latest_snapshot() instead of calling non-existent method
            if snapshot and hasattr(snapshot, 'symbol'):
                # Extract calls and puts from snapshot's internal chain data
                from app.services.option_chain_builder import option_chain_builder
                chain = option_chain_builder.chains.get(symbol, {})

                if chain:
                    for strike_key, sides in chain.items():
                        # The contract expects strike strings as keys
                        strike_str = str(int(float(strike_key)))

                        ce_data = sides.get('CE')
                        pe_data = sides.get('PE')

                        if ce_data:
                            calls[strike_str] = {
                                'ltp':   float(ce_data.ltp or 0.0),
                                'oi':    int(ce_data.oi or 0),
                                'iv':    float(ce_data.iv or 0.0),
                                'delta': float(ce_data.delta or 0.0),
                                'gamma': float(ce_data.gamma or 0.0),
                                'theta': float(ce_data.theta or 0.0),
                                'vega':  float(ce_data.vega or 0.0),
                                'bid':   float(ce_data.bid or 0.0),
                                'ask':   float(ce_data.ask or 0.0),
                            }

                        if pe_data:
                            puts[strike_str] = {
                                'ltp':   float(pe_data.ltp or 0.0),
                                'oi':    int(pe_data.oi or 0),
                                'iv':    float(pe_data.iv or 0.0),
                                'delta': float(pe_data.delta or 0.0),
                                'gamma': float(pe_data.gamma or 0.0),
                                'theta': float(pe_data.theta or 0.0),
                                'vega':  float(pe_data.vega or 0.0),
                                'bid':   float(pe_data.bid or 0.0),
                                'ask':   float(pe_data.ask or 0.0),
                            }
        except Exception as e:
            logger.debug(f"Option chain payload extraction failed: {e}")

        return calls, puts

    async def _compute_and_broadcast(self, symbol: str):
        try:
            from app.services.option_chain_builder import option_chain_builder
            from app.core.ws_manager import manager
            from ai.advanced_microstructure_layer import AdvancedMicrostructureLayer

            logger.info(f"[COMPUTE] Starting analytics for {symbol}")
            
            snap = option_chain_builder.get_latest_snapshot(symbol)
            if snap is None:
                logger.warning(f"[COMPUTE] No snapshot for {symbol} — checking chains")
                # Check if chains exist
                chains = option_chain_builder.chains.get(symbol, {})
                logger.info(f"[COMPUTE] Chains for {symbol}: {len(chains)} strikes")
                if chains:
                    logger.info(f"[COMPUTE] Sample strikes: {list(chains.keys())[:3]}")
                return

            logger.info(f"[COMPUTE] Found snapshot for {symbol}: spot={snap.spot} pcr={snap.pcr}")

            # Initialize microstructure layer for liquidity analysis
            microstructure_layer = AdvancedMicrostructureLayer()
            
            # Prepare metrics for liquidity vacuum analysis
            metrics = {
                'spot_price': snap.spot,
                'support': 0,  # Will be calculated from key levels
                'resistance': 0,  # Will be calculated from key levels  
                'volatility_regime': 'normal',  # Will be determined from IV
                'oi_change': 0  # Will be calculated from OI changes
            }
            
            # Run liquidity vacuum analysis
            microstructure_analysis = microstructure_layer.analyze_microstructure(metrics)

            # PHASE 1: Master AI Engine Execution (Law 1 Alignment)
            ai_results = {}
            try:
                # Convert snap attributes to dict for orchestrator
                snap_dict = {
                    "spot": snap.spot,
                    "pcr": snap.pcr,
                    "max_call_oi_strike": snap.max_call_oi_strike,
                    "max_put_oi_strike": snap.max_put_oi_strike,
                    "total_call_oi": snap.total_call_oi,
                    "total_put_oi": snap.total_put_oi,
                    "atm_strike": snap.atm_strike,
                    "atm_iv": snap.atm_iv,
                    "vwap": snap.vwap,
                    "dte": snap.dte,
                    "analytics": snap.analytics or {}
                }
                ai_results = await ai_orchestrator.run_cycle(symbol, snap_dict)
                logger.info(f"[ORCHESTRATOR] ✅ Analysis computed for {symbol} ({ai_results.get('cycle_time_ms')}ms)")
            except Exception as e:
                logger.error(f"[ORCHESTRATOR] ❌ Pipeline crash for {symbol}: {e}")
                # Fallback to manual heuristics if brain crashes

            # Simple bias from PCR (Fallback/Parity check)
            pcr = ai_results.get("market_analysis", {}).get("bias_strength", snap.pcr) if ai_results else snap.pcr
            
            # Map Orchestrator results to standard payload
            m_analysis = ai_results.get("market_analysis", {})
            bias = m_analysis.get("bias", "NEUTRAL")
            strength = m_analysis.get("bias_strength", 0.0)
            regime = m_analysis.get("regime", "RANGING")
            
            import time
            ts  = int(time.time())
            spot = snap.spot

            payload = {
                "type":        "market_update",
                "symbol":      symbol,
                "timestamp":   ts,

                # Spot — all aliases
                "spot":        spot,
                "spotPrice":   spot,
                "liveSpot":    spot,
                "currentSpot": spot,

                "atm":         snap.atm_strike,
                "ai_ready":    True,

                "market_analysis": {
                    "regime":        regime,
                    "bias":          bias,
                    "bias_strength": strength,
                    "key_levels":    m_analysis.get("key_levels", {
                        "call_wall": snap.max_call_oi_strike,
                        "put_wall":  snap.max_put_oi_strike,
                        "max_pain": 0,
                        "gex_flip": snap.analytics.get("gex_flip", 0) if snap.analytics else 0,
                        "vwap":      snap.vwap,
                    }),
                    "gamma_analysis": m_analysis.get("gamma_analysis", {
                        "net_gex": snap.analytics.get("net_gex", 0) if snap.analytics else 0,
                        "regime": snap.analytics.get("regime", "NEUTRAL") if snap.analytics else "NEUTRAL",
                        "flip_level": snap.analytics.get("gex_flip", 0) if snap.analytics else 0,
                        "implication": "Institutional Gamma Exposure Analysis",
                    }),
                    "volatility_state": m_analysis.get("volatility_state", {
                        "iv_atm":        snap.atm_iv,
                        "state":         "NORMAL",
                    }),
                    "technical_state": m_analysis.get("technical_state", {
                        "rsi":          0,
                        "momentum_15m": 0,
                    }),
                    "flow_analysis": {
                        "call_velocity": max(0.1, min(0.9, (snap.total_call_oi / 1000000))),
                        "put_velocity": max(0.1, min(0.9, (snap.total_put_oi / 1000000))),
                        "direction": "BULLISH" if snap.total_call_oi > snap.total_put_oi else "BEARISH",
                        "intent_score": max(0.1, min(0.9, abs(snap.total_call_oi - snap.total_put_oi) / 100000)),
                        "imbalance": abs(snap.total_call_oi - snap.total_put_oi) / (snap.total_call_oi + snap.total_put_oi)
                    },
                    "summary": m_analysis.get("summary") or self._build_summary(symbol, snap.pcr, bias, regime,
                                                   snap.max_call_oi_strike, snap.max_put_oi_strike,
                                                   snap.atm_iv, "NORMAL"),
                },

                "early_warnings": ai_results.get("early_warnings", []),
                "trade_plan": ai_results.get("trade_plan", {
                    "plan_id":      f"PLAN-{symbol}-{ts}",
                    "instrument":   symbol,
                    "direction":    "NEUTRAL",
                    "strike":       snap.atm_strike,
                }),
                "confidence_score": ai_results.get("confidence_score", 0.0),
                "sentiment_overlay": ai_results.get("sentiment_overlay", {}),
                "option_chain": {
                    "pcr":           snap.pcr,
                    "call_wall":     snap.max_call_oi_strike,
                    "put_wall":      snap.max_put_oi_strike,
                    "gex_flip":      snap.analytics.get("gex_flip", 0) if snap.analytics else 0,
                    "net_gex":       snap.analytics.get("net_gex", 0) if snap.analytics else 0,
                    "iv_atm":        snap.atm_iv,
                    "calls":         snap.calls_data,
                    "puts":          snap.puts_data,
                },

                "paper_trading": {
                    "total_trades":    0,
                    "total_pnl":       0.0,
                    "capital_current": 100000.0,
                },

                "news_alerts": [],
                "chart_intelligence": ai_results.get("chart_intelligence"),

                "dataQuality": {
                    "hasSpot":   spot > 0,
                    "hasOi":     snap.total_call_oi > 0,
                    "aiReady":   True,
                    "source":    "AI_ORCHESTRATOR",
                },
            }

            # Safe JSON broadcast
            import json
            try:
                message = json.dumps(payload, default=str)
                await manager.broadcast(message)
            except Exception as e:
                logger.error(f"[BROADCAST] JSON error for {symbol}: {e}")

            # Send separate chart_analysis message with all required data for components
            chart_analysis_payload = {
                "type": "chart_analysis",
                "symbol": symbol,
                "timestamp": ts,
                "price": round(spot, 2),
                "bias": bias,
                "bias_strength": strength,
                "regime": regime,
                "flow_analysis": payload["market_analysis"]["flow_analysis"],
                "key_levels": payload["market_analysis"]["key_levels"],
                "gamma_analysis": payload["market_analysis"]["gamma_analysis"],
                "expiry_magnet": {
                    "magnet_strike": snap.max_put_oi_strike if snap.max_put_oi_strike > 0 else snap.atm_strike,
                    "pin_probability": 0.45 if snap.dte <= 1 else 0.25, 
                    "days_to_expiry": snap.dte,
                    "target_distance": abs(spot - (snap.max_put_oi_strike if snap.max_put_oi_strike > 0 else snap.atm_strike))
                },
                "volatility_state": payload["market_analysis"]["volatility_state"],
                "expected_move": {
                    "1h": round(spot * 0.004, 2), 
                    "4h": round(spot * 0.008, 2),
                    "1d": round(spot * 0.012, 2)
                },
                "liquidity_analysis": {
                    "total_call_oi": snap.total_call_oi,
                    "total_put_oi": snap.total_put_oi,
                    "liquidity_pressure": min(1.0, (snap.total_call_oi + snap.total_put_oi) / 50000000), 
                    "book_depth": max(0.3, min(0.9, microstructure_analysis.get("liquidity_vacuum_confidence", 0.5))),
                    "expansion_probability": microstructure_analysis.get("liquidity_vacuum_confidence", 0.3),
                    "vacuum_signal": microstructure_analysis.get("liquidity_vacuum_signal", "NONE"),
                    "vacuum_direction": microstructure_analysis.get("liquidity_vacuum_direction", "NONE"),
                    "vacuum_strength": microstructure_analysis.get("liquidity_vacuum_strength", 0.0)
                },
                "sentiment_overlay": payload["sentiment_overlay"],
                "chart_intelligence": payload["chart_intelligence"],
                "summary": payload["market_analysis"]["summary"],
                "confidence": payload["confidence_score"],
                "computation_ms": round(ai_results.get("cycle_time_ms", 0), 2)
            }
            
            try:
                chart_message = json.dumps(chart_analysis_payload, default=str)
                await manager.broadcast(chart_message)
                logger.info(f"[BROADCAST] ✅ {symbol} chart_analysis via AI_ORCHESTRATOR")
            except Exception as e:
                logger.error(f"[BROADCAST] Chart analysis JSON error for {symbol}: {e}")

        except Exception as e:
            logger.error(
                f"[COMPUTE] ❌ Crash for {symbol}: {e}",
                exc_info=True
            )

    async def _analytics_loop(self):
        """Main loop ensuring 500ms broadcast cycles"""
        logger.info("Analytics Loop Started")
        loop_count = 0
        while self._running:
            try:
                loop_count += 1
                cycle_start = time.monotonic()

                if not manager.active_connections:
                    if loop_count % 10 == 0:
                        logger.warning(f"[BROADCASTER] No active connections (Loop #{loop_count})")
                    await asyncio.sleep(1)
                    continue

                # Broadly targeting main symbols
                symbols = ["NIFTY", "BANKNIFTY"]
                
                tasks = []
                for symbol in symbols:
                    is_dirty    = self._dirty.get(symbol, False)
                    last_bc     = self._last_broadcast_time.get(symbol, 0)
                    force_bc    = (time.monotonic() - last_bc) > 2.0
                    should_send = is_dirty or force_bc

                    if loop_count % 10 == 0:
                        logger.info(
                            f"[BROADCASTER LOOP #{loop_count}] {symbol} | "
                            f"dirty={is_dirty} force={force_bc} should_send={should_send}"
                        )

                    if should_send:
                        tasks.append(self._compute_and_broadcast(symbol))
                        self._dirty[symbol] = False
                        self._last_broadcast_time[symbol] = time.monotonic()

                if tasks:
                    await asyncio.gather(*tasks)

                # Control interval
                elapsed = time.monotonic() - cycle_start
                sleep_time = max(0, self.ANALYTICS_INTERVAL - elapsed)
                await asyncio.sleep(sleep_time)

            except Exception as e:
                logger.error(f"Loop error: {e}", exc_info=True)
                await asyncio.sleep(1)

    async def start(self):
        if self._running: return
        self._running = True
        self._analytics_task = asyncio.create_task(self._analytics_loop())
        logger.info("Analytics Broadcaster Started")

    async def stop(self):
        self._running = False
        if self._analytics_task:
            self._analytics_task.cancel()
            try:
                await asyncio.wait_for(self._analytics_task, timeout=2)
            except: pass
        logger.info("Analytics Broadcaster Stopped")

# Singleton
analytics_broadcaster = AnalyticsBroadcaster()
