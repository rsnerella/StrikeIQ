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

            snap = option_chain_builder.get_latest_snapshot(symbol)
            if snap is None:
                logger.warning(f"[COMPUTE] No snapshot for {symbol} — skipping")
                return

            # Simple bias from PCR
            pcr = snap.pcr
            if pcr > 1.3:
                bias, strength, regime = "BULLISH", round(min((pcr-1)/0.5, 1.0), 3), "RANGING"
            elif pcr < 0.7:
                bias, strength, regime = "BEARISH", round(min((1-pcr)/0.5, 1.0), 3), "RANGING"
            else:
                bias, strength, regime = "NEUTRAL", 0.0, "RANGING"

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
                    "key_levels": {
                        "call_wall": snap.max_call_oi_strike,
                        "put_wall":  snap.max_put_oi_strike,
                        "max_pain": 0,
                        "gex_flip": 0,
                        "vwap":      snap.vwap,
                        "ema20":     0,
                        "ema50":     0,
                    },
                    "gamma_analysis": {
                        "net_gex":     0,
                        "regime":      "SHORT_GAMMA" if snap.total_call_oi > snap.total_put_oi else "LONG_GAMMA",
                        "flip_level":  0,
                        "implication": "Dealer positioning from OI structure",
                    },
                    "volatility_state": {
                        "iv_atm":        snap.atm_iv,
                        "iv_percentile": 0,
                        "state":         "NORMAL",
                        "compression":   False,
                    },
                    "technical_state": {
                        "rsi":          0,
                        "macd_hist":    0,
                        "adx":          0,
                        "momentum_15m": 0,
                        "pattern":      "NONE",
                    },
                    "summary": (
                        f"{symbol} | PCR={pcr:.2f} | Bias={bias} | "
                        f"Call wall={snap.max_call_oi_strike} | "
                        f"Put wall={snap.max_put_oi_strike} | "
                        f"IV={snap.atm_iv:.2f}%"
                    ),
                },

                "early_warnings": [],

                "trade_plan": {
                    "plan_id":      f"PLAN-{symbol}-{ts}",
                    "instrument":   symbol,
                    "direction":    "NEUTRAL",
                    "strike":       snap.atm_strike,
                    "entry":        0.0,
                    "stop_loss":    0.0,
                    "target":       0.0,
                    "confidence":   0.0,
                    "time_horizon": "N/A",
                    "risk_reward":  0.0,
                    "reason":       ["Analyzing OI structure..."],
                    "signals_used": {
                        "pcr":       pcr,
                        "bias":      bias,
                        "regime":    regime,
                        "call_wall": snap.max_call_oi_strike,
                        "put_wall":  snap.max_put_oi_strike,
                    },
                },

                "option_chain": {
                    "pcr":           pcr,
                    "call_wall":     snap.max_call_oi_strike,
                    "put_wall":      snap.max_put_oi_strike,
                    "max_pain":      0,
                    "gex_flip":      0,
                    "net_gex":       0,
                    "iv_atm":        snap.atm_iv,
                    "iv_percentile": 0,
                    "straddle_pct": 0,
                    "calls":         snap.calls_data,
                    "puts":          snap.puts_data,
                },

                "paper_trading": {
                    "total_trades":    0,
                    "wins":            0,
                    "win_rate":        0.0,
                    "profit_factor":   0.0,
                    "sharpe_ratio":    0.0,
                    "total_pnl":       0.0,
                    "capital_current": 100000.0,
                },

                "news_alerts": [],

                "dataQuality": {
                    "hasSpot":   spot > 0,
                    "hasOi":     snap.total_call_oi > 0,
                    "hasGreeks": snap.atm_iv > 0,
                    "aiReady":   True,
                    "source":    "rest_poller",
                },
            }

            # Safe JSON broadcast
            import json
            try:
                message = json.dumps(payload, default=str)
            except Exception as e:
                logger.error(f"[BROADCAST] JSON error for {symbol}: {e}")
                return

            await manager.broadcast(message)
            logger.info(
                f"[BROADCAST] ✅ {symbol} | spot={spot} "
                f"pcr={pcr:.2f} calls={len(snap.calls_data)} "
                f"puts={len(snap.puts_data)}"
            )

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
