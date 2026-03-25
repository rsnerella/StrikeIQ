"""
Option Chain Builder for StrikeIQ
Maintains in-memory option chain and produces snapshots
"""

import asyncio
import logging
import bisect
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import json

from app.analytics.oi_buildup_engine import OIBuildupEngine
from app.core.diagnostics import diag, increment_counter
from app.core.ai_health_state import mark_health
from app.services.option_chain_snapshot import option_chain_snapshot
from app.analytics.analytics_engine import analytics_engine
from app.ai.ai_signal_engine import ai_signal_engine

logger = logging.getLogger(__name__)

# ---------------------------------------------------------
# INDEX CONFIGURATION (Institutional Standard)
# ---------------------------------------------------------
INDEX_CONFIG = {
    "NIFTY": {"step": 50, "lot": 25},
    "BANKNIFTY": {"step": 100, "lot": 15},
    "FINNIFTY": {"step": 50, "lot": 40}
}

@dataclass
class OptionData:
    strike: float
    ltp: float = 0.0
    oi: int = 0
    oi_prev: int = 0
    bid: float = 0.0
    ask: float = 0.0
    bid_qty: int = 0
    ask_qty: int = 0
    iv: float = 0.0
    delta: float = 0.0
    theta: float = 0.0
    vega: float = 0.0
    gamma: float = 0.0
    volume: int = 0
    last_update: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ChainSnapshot:
    symbol: str
    spot: float
    atm_strike: float
    expiry: str
    strikes: List[Dict[str, Any]]
    timestamp: int
    pcr: float = 0.0
    total_oi_calls: int = 0
    total_oi_puts: int = 0
    open: float = 0.0
    prev_close: float = 0.0
    recent_prices: List[float] = field(default_factory=list)
    analytics: Dict[str, Any] = None
    is_fallback: bool = False
    is_valid: bool = True


class OptionChainBuilder:

    def __init__(self):

        self.chains: Dict[str, Dict[float, Dict[str, OptionData]]] = {}

        self.spot_prices: Dict[str, float] = {}

        self.last_snapshots: Dict[str, datetime] = {}
        
        self.stale_timeout = 300  # 5 minutes

        self._snapshot_task: Optional[asyncio.Task] = None
        self._running = False
        
        self.debug = False  # Debug flag for snapshot logging

        self.default_expiry = self._get_next_expiry()

        self.oi_buildup_engine = OIBuildupEngine()

        logger.info("Option Chain Builder initialized")

    def _fallback_snapshot(self, symbol: str) -> ChainSnapshot:
        """Create a fallback snapshot when real data is unavailable"""
        from ai.ai_logger import log
        
        # Log fallback mode once per symbol
        self.log_once(f"_fallback_{symbol}", f"[SAFE MODE] Using fallback snapshot for {symbol}")
        
        # Use last known good spot or default
        spot = self.spot_prices.get(symbol, 22500)  # Default NIFTY spot
        
        # Create minimal valid strikes
        default_strikes = [
            {"strike": spot - 100, "call_oi": 1000, "put_oi": 800},
            {"strike": spot, "call_oi": 1200, "put_oi": 1000},
            {"strike": spot + 100, "call_oi": 900, "put_oi": 1100}
        ]
        
        # Mark as fallback
        fallback_snapshot = ChainSnapshot(
            symbol=symbol,
            spot=0,  # Invalid spot
            open=0,
            prev_close=0,
            atm_strike=0,
            expiry=self.default_expiry,
            strikes=default_strikes,
            timestamp=int(time.time()),
            pcr=1.0,  # Neutral PCR
            total_oi_calls=0,  # Invalid OI
            total_oi_puts=0,   # Invalid OI
            recent_prices=[],
            analytics={
                "strategy": "NONE",
                "confidence": 0.0,
                "is_fallback": True
            },
            is_fallback=True,
            is_valid=False  # Critical: Mark as invalid
        )
        
        return fallback_snapshot

    def log_once(self, key: str, message: str):
        """Log message only once per key to prevent spam"""
        if not hasattr(self, key):
            from ai.ai_logger import log
            log(message)
            setattr(self, key, True)

    # --------------------------------------------------

    def _get_next_expiry(self) -> str:

        import pytz

        ist = pytz.timezone("Asia/Kolkata")
        now = datetime.now(ist)

        today = now.date()

        days_until_thursday = (3 - today.weekday()) % 7

        expiry = today + timedelta(days=days_until_thursday)

        return expiry.strftime("%Y-%m-%d")

    # --------------------------------------------------

    async def start(self):

        if self._running:
            return

        self._running = True

        self._snapshot_task = asyncio.create_task(self._snapshot_loop())

        logger.info("Option chain builder started")

    async def stop(self):

        self._running = False

        if self._snapshot_task:
            self._snapshot_task.cancel()

            try:
                await self._snapshot_task
            except asyncio.CancelledError:
                pass

    # --------------------------------------------------

    async def _snapshot_loop(self):

        while self._running:

            try:
                await asyncio.sleep(0.5)

                await self._generate_snapshots()

            except asyncio.CancelledError:
                break

            except Exception as e:
                logger.error("Snapshot loop error: %s", e)

    # --------------------------------------------------

    async def _generate_snapshots(self):

        now = datetime.utcnow()
        from app.core.market_context import MARKET_CONTEXT
        current_symbol = MARKET_CONTEXT.get("symbol", "NIFTY")

        if getattr(self, "active_symbol", None) != current_symbol:
            logger.info(f"CHAIN BUILDER → Symbol switched to {current_symbol}. Clearing stale caches.")
            self.chains.clear()
            self.spot_prices.clear()
            self.active_symbol = current_symbol

        for symbol in list(self.spot_prices.keys()):
            if symbol != current_symbol:
                continue

            spot = self.spot_prices.get(symbol)

            chain = self.chains.get(symbol)

            if not chain:
                continue

            self.purge_stale_strikes(symbol)

            # PHASE 1: Calculate ATM strike
            config = INDEX_CONFIG.get(symbol, {"step": 50, "lot": 25})
            step = config["step"]
            atm = round(spot / step) * step
            
            # PHASE 2: Select strikes dynamically (ATM ± 20 strikes)
            # This ensures we always have a professional depth of 41 strikes (ATM + 20 ITM + 20 OTM)
            lower_bound = atm - (20 * step)
            upper_bound = atm + (20 * step)
            
            # PHASE 3: EVICT strikes outside the dynamic active window - DISABLED
            # We now keep ALL strikes to ensure full chain PCR calculation
            # Commented out eviction to preserve full 136+ strike chain
            # far = [s for s in chain.keys() if s < lower_bound or s > upper_bound]
            # for s in far:
            #     chain.pop(s, None)
 
            last = self.last_snapshots.get(symbol, datetime.min)
            if (now - last).total_seconds() < 0.5:
                continue

            try:
                snapshot = self._create_snapshot(symbol)
            except Exception as e:
                logger.error("Snapshot build error", exc_info=True)
                continue

            if not snapshot:
                continue

            self.last_snapshots[symbol] = now

            diag("CHAIN_ENGINE", "snapshot update")
            increment_counter("chain_updates")

            await self._broadcast_snapshot(snapshot)

    def purge_stale_strikes(self, symbol: str):
        chain = self.chains.get(symbol)
        if not chain:
            return
            
        now = datetime.utcnow()
        for strike in list(chain.keys()):
            ce = chain[strike].get("CE")
            pe = chain[strike].get("PE")
            
            ce_age = (now - ce.last_update).total_seconds() if ce else float('inf')
            pe_age = (now - pe.last_update).total_seconds() if pe else float('inf')
            
            if ce_age > self.stale_timeout and pe_age > self.stale_timeout:
                del chain[strike]

    # --------------------------------------------------

    def _create_snapshot(self, symbol: str) -> Optional[ChainSnapshot]:
        try:
            if symbol not in self.spot_prices:
                return self._fallback_snapshot(symbol)

            spot = self.spot_prices[symbol]

            chain = self.chains.get(symbol, {})
            
            if not chain:
                self.log_once(f"_no_chain_{symbol}", f"[SAFE MODE] No chain data for {symbol}")
                return self._fallback_snapshot(symbol)

            strikes = []

            # FIX: avoid repeated expensive sorting
            strike_keys = list(chain.keys())
            strike_keys.sort()

            atm = self._find_atm_strike(spot, strike_keys)
            
            now = datetime.utcnow()

            for strike in strike_keys:
                data = chain[strike]
                ce = data.get("CE")
                pe = data.get("PE")
                
                # Use real values if present, else None (Standardized null for frontend '—')
                strikes.append(
                {
                    "strike": strike,
                    "call_oi": ce.oi if ce and ce.oi > 0 else None,
                    "call_oi_change": ce.oi - ce.oi_prev if ce and ce.oi_prev > 0 else None,
                    "call_ltp": ce.ltp if ce and ce.ltp > 0 else None,
                    "call_bid": ce.bid if ce and ce.bid > 0 else None,
                    "call_ask": ce.ask if ce and ce.ask > 0 else None,
                    "call_bid_qty": ce.bid_qty if ce and ce.bid_qty > 0 else None,
                    "call_ask_qty": ce.ask_qty if ce and ce.ask_qty > 0 else None,
                    "call_volume": ce.volume if ce and ce.volume > 0 else None,
                    "call_iv": ce.iv if ce and ce.iv > 0 else None,
                    "call_delta": ce.delta if ce and ce.delta != 0 else None,
                    "call_theta": ce.theta if ce and ce.theta != 0 else None,
                    "call_vega": ce.vega if ce and ce.vega != 0 else None,
                    "call_gamma": ce.gamma if ce and ce.gamma != 0 else None,
                    "put_oi": pe.oi if pe and pe.oi > 0 else None,
                    "put_oi_change": pe.oi - pe.oi_prev if pe and pe.oi_prev > 0 else None,
                    "put_ltp": pe.ltp if pe and pe.ltp > 0 else None,
                    "put_bid": pe.bid if pe and pe.bid > 0 else None,
                    "put_ask": pe.ask if pe and pe.ask > 0 else None,
                    "put_bid_qty": pe.bid_qty if pe and pe.bid_qty > 0 else None,
                    "put_ask_qty": pe.ask_qty if pe and pe.ask_qty > 0 else None,
                    "put_volume": pe.volume if pe and pe.volume > 0 else None,
                    "put_iv": pe.iv if pe and pe.iv > 0 else None,
                    "put_delta": pe.delta if pe and pe.delta != 0 else None,
                    "put_theta": pe.theta if pe and pe.theta != 0 else None,
                    "put_vega": pe.vega if pe and pe.vega != 0 else None,
                    "put_gamma": pe.gamma if pe and pe.gamma != 0 else None,
                }
                )

            # Calculate PCR and total OI - FIX: Use actual chain structure
            total_call_oi = sum([
                ce.oi for strike in chain.values()
                if (ce := strike.get("CE")) and hasattr(ce, "oi")
            ])
            
            total_put_oi = sum([
                pe.oi for strike in chain.values()
                if (pe := strike.get("PE")) and hasattr(pe, "oi")
            ])

            print("[OI CHECK]", total_call_oi, total_put_oi)
            pcr = total_put_oi / total_call_oi if total_call_oi > 0 else 0.0

            if total_call_oi == 0 and total_put_oi == 0:
                self.log_once("_oi_error", "[SAFE MODE] Invalid OI data - using fallback")
                return self._fallback_snapshot(symbol)

            logger.info(f"[CHAIN_OI_SUMMARY] strikes={len(strikes)} call_oi={total_call_oi} put_oi={total_put_oi}")
            
            logger.info(
                f"CHAIN_BUILDER_OUTPUT symbol={symbol} "
                f"strikes={len(strikes)} "
                f"call_oi={total_call_oi} "
                f"put_oi={total_put_oi}"
            )
            
            mark_health("option_chain")

            # Capture price metadata
            meta = getattr(self, "price_metadata", {}).get(symbol, {})

            # Create snapshot data dictionary for analytics with correct mapping for GEX engine
            snapshot_data = {
                "symbol": symbol,
                "spot": spot,
                "calls": {
                    str(s["strike"]): {
                        "gamma": s.get("call_gamma", 0) or 0,
                        "oi": s.get("call_oi", 0) or 0
                    } for s in strikes
                },
                "puts": {
                    str(s["strike"]): {
                        "gamma": s.get("put_gamma", 0) or 0,
                        "oi": s.get("put_oi", 0) or 0
                    } for s in strikes
                }
            }

            # Run analytics engine
            analytics = analytics_engine.analyze(snapshot_data)
            
            # VALIDATE ANALYTICS BEFORE AI SIGNAL
            if not analytics or analytics.get("pcr") == 0:
                self.log_once("_analytics_error", "[SAFE MODE] Invalid analytics - using fallback")
                return self._fallback_snapshot(symbol)
            
            # NORMALIZE ANALYTICS FOR UI (CRITICAL PATCH)
            analytics["gamma"] = analytics.get("net_gex", 0)
            analytics["oi"] = total_call_oi + total_put_oi
            analytics["liquidity"] = total_call_oi + total_put_oi
            analytics["volatility"] = analytics.get("iv", 0) or 0
            
            # Generate AI signal
            ai_signal = ai_signal_engine.generate(analytics)
            analytics["ai_signal"] = ai_signal

            mark_health("option_chain")

            # Capture price metadata
            meta = getattr(self, "price_metadata", {}).get(symbol, {})

            # ENSURE REAL DATA FLOW - Check spot price
            if spot == 0:
                self.log_once("_spot_error", "[SAFE MODE] Invalid spot price - using fallback")
                return self._fallback_snapshot(symbol)
            
            return ChainSnapshot(
                symbol=symbol,
                spot=spot,
                open=meta.get("open", spot),
                prev_close=meta.get("prev_close", spot),
                atm_strike=atm,
                expiry=self.default_expiry,
                strikes=strikes,
                timestamp=int(now.timestamp()),
                pcr=pcr,
                total_oi_calls=total_call_oi,
                total_oi_puts=total_put_oi,
                recent_prices=getattr(self, "_price_history", {}).get(symbol, []),
                analytics=analytics
            )
        
        except Exception as e:
            self.log_once("_snapshot_error", f"[SAFE MODE] Snapshot error - using fallback: {str(e)[:50]}")
            return self._fallback_snapshot(symbol)

    # --------------------------------------------------

    def _find_atm_strike(self, spot: float, strikes: List[float]) -> float:

        if not strikes:
            return spot

        idx = bisect.bisect_left(strikes, spot)

        if idx == 0:
            return strikes[0]

        if idx >= len(strikes):
            return strikes[-1]

        lower = strikes[idx - 1]
        upper = strikes[idx]

        return lower if (spot - lower) < (upper - spot) else upper

    # --------------------------------------------------

    async def _broadcast_snapshot(self, snapshot: ChainSnapshot):

        try:

            from app.core.ws_manager import manager, broadcast_with_strategy
            from app.services.analytics_broadcaster import analytics_broadcaster

            logger.info(f"PIPELINE → chain updated {snapshot.symbol}")
            logger.info(f"CHAIN SNAPSHOT → {snapshot.symbol} spot={snapshot.spot} atm={snapshot.atm_strike} pcr={snapshot.pcr} calls={snapshot.total_oi_calls} puts={snapshot.total_oi_puts}")
            logger.info(f"CHAIN STRIKES → {len(snapshot.strikes)}")
            
            # OI SANITY CHECK - Permanent debug metric
            logger.info(f"[DATA_HEALTH] strikes={len(snapshot.strikes)} call_oi={snapshot.total_oi_calls:,} put_oi={snapshot.total_oi_puts:,} pcr={snapshot.pcr:.2f}")
            
            # PATCH 5: PIPELINE HEALTH CHECK
            if snapshot.total_oi_calls == 0 and snapshot.total_oi_puts == 0:
                logger.warning(
                    "[DATA_HEALTH_ALERT] OI values zero - parser issue likely"
                )
            
            # Broadcast option chain update
            pipeline_start = time.perf_counter()
            
            # Extract calls and puts from strikes for frontend compatibility
            calls_dict = {}
            puts_dict = {}
            
            for strike_data in snapshot.strikes:
                strike = strike_data.get("strike", 0)
                if strike:
                    calls_dict[strike] = {
                        "ltp": strike_data.get("call_ltp", 0),
                        "oi": strike_data.get("call_oi", 0),
                        "volume": strike_data.get("call_volume", 0),
                        "iv": strike_data.get("call_iv", 0),
                        "delta": strike_data.get("call_delta", 0),
                        "gamma": strike_data.get("call_gamma", 0),
                        "theta": strike_data.get("call_theta", 0),
                        "vega": strike_data.get("call_vega", 0),
                        "bid": strike_data.get("call_bid", 0),
                        "ask": strike_data.get("call_ask", 0),
                    }
                    puts_dict[strike] = {
                        "ltp": strike_data.get("put_ltp", 0),
                        "oi": strike_data.get("put_oi", 0),
                        "volume": strike_data.get("put_volume", 0),
                        "iv": strike_data.get("put_iv", 0),
                        "delta": strike_data.get("put_delta", 0),
                        "gamma": strike_data.get("put_gamma", 0),
                        "theta": strike_data.get("put_theta", 0),
                        "vega": strike_data.get("put_vega", 0),
                        "bid": strike_data.get("put_bid", 0),
                        "ask": strike_data.get("put_ask", 0),
                    }
            
            payload = {
                "type": "option_chain_update",
                "symbol": snapshot.symbol,
                "expiry": snapshot.expiry,
                "spot": float(snapshot.spot) if snapshot.spot else 0.0,
                "atm": int(snapshot.atm_strike) if snapshot.atm_strike else 0,
                "pcr": float(snapshot.pcr) if snapshot.pcr else 0.0,
                "timestamp": int(snapshot.timestamp),
                "strikesCount": len(snapshot.strikes) if snapshot.strikes else 0,
                "calls": calls_dict,   # {strike: {ltp, oi, iv, delta, gamma, theta, vega, bid, ask}}
                "puts": puts_dict,    # same structure
                "data": snapshot.__dict__,   # keep for backward compat
            }
            
            # Broadcast analytics update separately
            if snapshot.analytics:
                # FALLBACK SAFETY - Check if using fallback snapshot
                if snapshot.analytics.get("is_fallback"):
                    self.log_once("_fallback_active", "[SAFE MODE] Using fallback snapshot")
                
                analytics_payload = {
                    "type": "analytics_update",
                    "symbol": snapshot.symbol,
                    "analytics": snapshot.analytics,
                    "timestamp": int(snapshot.timestamp)
                }
                
                # 🔥 ADD HERE ONLY - FINAL TARGETED PATCH
                analytics = analytics_payload.get("analytics") or {}
                
                # Run AI strategy engine directly (ai.regime_engine doesn't exist — use strategy_engine)
                try:
                    from ai.strategy_engine import strategy_engine as se
                    strategy_input = snapshot.analytics or {}
                    decision = se.should_trade(strategy_input)
                    strategy_str = decision.get("strategy", "NO_TRADE") if isinstance(decision, dict) else str(decision)
                    confidence_val = decision.get("confidence", 0.0) if isinstance(decision, dict) else 0.35
                    entry_val = decision.get("entry", 0) if isinstance(decision, dict) else 0
                    target_val = decision.get("target", 0) if isinstance(decision, dict) else 0
                    sl_val = decision.get("stop_loss", 0) if isinstance(decision, dict) else 0
                    regime_val = strategy_input.get("regime", "RANGING")

                    analytics.update({
                        "signal": strategy_str,
                        "strategy": strategy_str,
                        "confidence": confidence_val,
                        "entry": entry_val,
                        "target": target_val,
                        "stop_loss": sl_val,
                        "regime": regime_val,
                        "metadata": {"trade_score": confidence_val},
                        "blocked": False,
                    })
                except Exception as e:
                    logger.error(f"[AI ORCHESTRATOR ERROR] {e}")
                    analytics.update({
                        "signal": "WEAK_SIGNAL",
                        "strategy": "WEAK_SIGNAL",
                        "confidence": 0.35,
                        "blocked": False,
                        "regime": "RANGING",
                        "metadata": {"trade_score": 0.35},
                    })
                    
                # ADD EXECUTION LOGIC
                execution = {}
                strategy = analytics.get("strategy")
                
                try:
                    # FILTER BAD TRADES
                    trade_score = analytics.get("metadata", {}).get("trade_score", 0)
                    
                    if trade_score < 0.25:
                        print("[FILTER BLOCKED]", trade_score)
                        # TEMP DISABLED
                        # return
                    
                    # OPTIONAL (AGGRESSIVE MODE)
                    from app.core.risk_mode import RISK_MODE
                    if RISK_MODE == "AGGRESSIVE" and trade_score < 0.2:
                        analytics["strategy"] = "NO_TRADE"
                        analytics["execution"] = {}
                        return
                    
                    if analytics.get("blocked"):
                        # Don't abort — just downgrade to WEAK_SIGNAL to keep execution alive
                        analytics["strategy"] = analytics.get("strategy") or "WEAK_SIGNAL"
                        analytics["confidence"] = analytics.get("confidence") or 0.35
                        analytics["blocked"] = False
                    
                    # Check for valid trading strategies
                    if strategy in ["BUY", "SELL"]:
                        # FORCE EXECUTION IN AGGRESSIVE MODE
                        if RISK_MODE == "AGGRESSIVE" and analytics.get("confidence", 0) < 0.25:
                            analytics["confidence"] = 0.25
                        
                        atm = snapshot.atm_strike
                        spot = snapshot.spot

                        # STEP 1: SELECT STRIKE (UPGRADED TO ITM)
                        from app.config import INDEX_CONFIG
                        config = INDEX_CONFIG.get(snapshot.symbol, {"step": 50, "lot": 25})
                        step = config["step"]
                        
                        if analytics["strategy"] == "BUY":
                            strike = atm - step   # slightly ITM call
                            option_type = "CE"
                        else:
                            strike = atm + step   # slightly ITM put
                            option_type = "PE"

                        # STEP 2: GET LTP FROM STRIKES
                        ltp = None
                        for s in snapshot.strikes:
                            if s["strike"] == strike:
                                ltp = s.get("call_ltp") if option_type == "CE" else s.get("put_ltp")
                                break

                        if not ltp or ltp <= 0:
                            print(f"[NO LTP] Strike {strike} {option_type}")
                            return

                        # STEP 3: ENTRY (UPGRADED)
                        if analytics["confidence"] > 0.5:
                            entry = ltp  # aggressive entry
                        else:
                            entry = ltp * 0.98  # wait for slight pullback

                        # STEP 4: STOP LOSS (UPGRADED - 15%)
                        sl = entry * 0.85

                        # STEP 5: TARGET (RR 1:2)
                        target = entry + (abs(entry - sl) * 2)

                        execution = {
                            "strike": strike,
                            "option_type": option_type,
                            "entry": round(entry, 2),
                            "stop_loss": round(sl, 2),
                            "target": round(target, 2)
                        }

                        # ATTACH TO ANALYTICS
                        analytics["execution"] = execution
                        print("[FINAL FIXED EMITTER]", analytics)
                    else:
                        # No valid strategy - set empty execution
                        analytics["execution"] = {}
                        print(f"[NO STRATEGY] Strategy: {strategy}")
                    
                except Exception as e:
                    print("[STRATEGY ERROR]", str(e))

                    # FAILSAFE (IMPORTANT)
                    analytics["strategy"] = analytics.get("strategy", "NO_TRADE")
                    analytics["confidence"] = analytics.get("confidence", 0.2)
                
                print("[STRATEGY OUTPUT]", analytics)
                analytics_payload["analytics"] = analytics
                now = time.time()
                if not hasattr(self, '_last_emitter_log_ts'):
                    self._last_emitter_log_ts = 0
                if now - self._last_emitter_log_ts > 5:
                    logger.info(f"[FINAL FIXED EMITTER] size={len(json.dumps(analytics_payload, default=str))}")
                    self._last_emitter_log_ts = now
                
                try:
                    now = time.time()
                    if not hasattr(self, '_last_ws_emitter_log_ts'):
                        self._last_ws_emitter_log_ts = 0
                    if now - self._last_ws_emitter_log_ts > 5:
                        logger.info(f"[WS OUTGOING PAYLOAD] {analytics_payload.get('type')} size={len(json.dumps(analytics_payload, default=str))}")
                        self._last_ws_emitter_log_ts = now
                    await broadcast_with_strategy(analytics_payload)
                except Exception as e:
                    logger.warning(f"Analytics broadcast failed: {e}")
            
            try:
                now = time.time()
                if not hasattr(self, '_last_ws_payload_log_ts'):
                    self._last_ws_payload_log_ts = 0
                if now - self._last_ws_payload_log_ts > 5:
                    logger.info(f"[WS OUTGOING PAYLOAD] {payload.get('type')} size={len(json.dumps(payload, default=str))}")
                    self._last_ws_payload_log_ts = now
                await broadcast_with_strategy(payload)
            except Exception as e:
                logger.warning(f"WS send failed (client likely disconnected): {e}")
            pipeline_latency_ms = (time.perf_counter() - pipeline_start) * 1000
            
            # Add snapshot counter for sampling
            if not hasattr(self, 'snapshot_counter'):
                self.snapshot_counter = 0
            self.snapshot_counter += 1
            
            # Log latency only if it exceeds threshold (noise reduction)
            if pipeline_latency_ms > 5.0:
                logger.warning(f"[PIPELINE_LATENCY] {pipeline_latency_ms:.2f} ms")
            elif self.snapshot_counter % 500 == 0:
                logger.info(f"[PIPELINE_LATENCY_OK] {pipeline_latency_ms:.2f} ms")
            
            logger.info(f"PIPELINE → analytics triggered {snapshot.symbol}")
            
            # Trigger analytics engine
            try:
                analytics_broadcaster.compute_single_analytics(snapshot.symbol, snapshot.__dict__)
                logger.info(f"PIPELINE → analytics engine called {snapshot.symbol}")
            except Exception as e:
                logger.error(f"PIPELINE → analytics engine failed {snapshot.symbol}: {e}")

            logger.info("CHAIN BROADCAST SUCCESS")

        except Exception as e:
            logger.error("Snapshot broadcast error: %s", e)

    # --------------------------------------------------

    def update_index_price(self, symbol: str, price: float, open_price: float = 0.0, prev_close: float = 0.0):
        
        # STAGE 4: OPTION CHAIN BUILDER TRACE
        logger.info(
            "CHAIN BUILDER UPDATE → %s spot=%s",
            symbol,
            price
        )

        symbol = symbol.upper().replace(" ", "")

        if symbol == "BANKNIFTY":
            symbol = "BANKNIFTY"

        if symbol == "NIFTY":
            symbol = "NIFTY"

        self.spot_prices[symbol] = price
        
        if not hasattr(self, "price_metadata"):
            self.price_metadata = {}
        
        self.price_metadata[symbol] = {
            "open": open_price,
            "prev_close": prev_close
        }

        # Track price history for momentum fallback
        if not hasattr(self, "_price_history"):
            self._price_history = {}
        
        history = self._price_history.setdefault(symbol, [])
        history.append(price)
        if len(history) > 5:
            history.pop(0)

    # --------------------------------------------------

    def update_option_tick(
        self,
        symbol: str,
        strike: float,
        right: str,
        ltp: float,
        oi: int = 0,
        volume: int = 0,
        **kwargs
    ):

        try:

            symbol = symbol.upper().replace(" ", "")

            if right not in ("CE", "PE"):
                return

            strike = float(round(strike, 2))

            if symbol not in self.chains:
                self.chains[symbol] = {}

            # Phase 5 GUARD: skip if ltp <= 0
            if ltp is None:
                return

            if strike not in self.chains[symbol]:
                self.chains[symbol][strike] = {}

            if right not in self.chains[symbol][strike]:
                self.chains[symbol][strike][right] = OptionData(strike=strike)

            opt = self.chains[symbol][strike][right]

            # MERGE STRATEGY
            # Never overwrite a real non-zero value with zero.
            # Two data sources update this store:
            #   1. WebSocket full_d30 ticks — real-time LTP, bid/ask, OI, Greeks
            #   2. REST poller (every 2s) — OI, Greeks snapshot as fallback
            # A tick from one source may have zeros for fields the other provides.
            # The merge ensures we always keep the best known value per field.
            def merge(new_val, old_val, zero_val):
                """Return new_val if it differs from zero_val, else keep old_val."""
                if new_val != zero_val:
                    return new_val
                return old_val if old_val is not None else zero_val

            # Extract existing values for merge
            existing_ltp = opt.ltp
            existing_oi = opt.oi
            existing_volume = opt.volume
            existing_bid = opt.bid
            existing_ask = opt.ask
            existing_bid_qty = opt.bid_qty
            existing_ask_qty = opt.ask_qty
            existing_iv = opt.iv
            existing_delta = opt.delta
            existing_theta = opt.theta
            existing_vega = opt.vega
            existing_gamma = opt.gamma

            # Apply merge strategy
            opt.ltp = merge(float(ltp), existing_ltp, 0.0)
            
            # Special handling for OI to track changes
            new_oi = merge(int(oi), existing_oi, 0)
            if new_oi != existing_oi and existing_oi > 0 and new_oi > 0:
                opt.oi_prev = existing_oi
            opt.oi = new_oi
            
            opt.volume = merge(int(volume), existing_volume, 0)
            opt.bid = merge(float(kwargs.get("bid", 0)), existing_bid, 0.0)
            opt.ask = merge(float(kwargs.get("ask", 0)), existing_ask, 0.0)
            opt.bid_qty = merge(int(kwargs.get("bid_qty", 0)), existing_bid_qty, 0)
            opt.ask_qty = merge(int(kwargs.get("ask_qty", 0)), existing_ask_qty, 0)
            opt.iv = merge(float(kwargs.get("iv", 0)), existing_iv, 0.0)
            opt.delta = merge(float(kwargs.get("delta", 0)), existing_delta, 0.0)
            opt.theta = merge(float(kwargs.get("theta", 0)), existing_theta, 0.0)
            opt.vega = merge(float(kwargs.get("vega", 0)), existing_vega, 0.0)
            opt.gamma = merge(float(kwargs.get("gamma", 0)), existing_gamma, 0.0)
                
            opt.last_update = datetime.utcnow()
            
            # FIX 4: Maintain chain dictionary structure and compute metrics
            chain = self.chains[symbol]
            
            # Compute total call and put OI
            total_call_oi = 0
            total_put_oi = 0
            
            for strike_key, strike_data in chain.items():
                ce_data = strike_data.get("CE")
                pe_data = strike_data.get("PE")
                
                if ce_data:
                    total_call_oi += ce_data.oi or 0
                if pe_data:
                    total_put_oi += pe_data.oi or 0
            
            # Track full chain aggregates for PCR override
            if not hasattr(self, '_total_call_oi'):
                self._total_call_oi = {}
            if not hasattr(self, '_total_put_oi'):
                self._total_put_oi = {}
            
            self._total_call_oi[symbol] = total_call_oi
            self._total_put_oi[symbol] = total_put_oi
            
            # Compute PCR
            pcr = total_put_oi / total_call_oi if total_call_oi > 0 else 0.0
            
            # Log chain update with metrics
            now = time.time()
            if not hasattr(self, '_last_chain_log_ts'):
                self._last_chain_log_ts = 0
            if now - self._last_chain_log_ts > 5:
                logger.info(f"[CHAIN_UPDATE] {symbol} strikes={len(chain)}")
                self._last_chain_log_ts = now
            
            # Ensure snapshot stored globally for analytics
            self.chains[symbol] = chain
            
            # STEP 4: Merge cache data for missing fields
            try:
                # Convert strike to string key for cache lookup
                strike_key = str(int(strike))
                cache = option_chain_snapshot.option_chain_cache
                
                if symbol in cache and strike_key in cache[symbol]:
                    snapshot = cache[symbol][strike_key]
                    
                    # Update missing fields from cache (DO NOT override LTP)
                    if opt.oi == 0 and snapshot.get("oi", 0) > 0:
                        opt.oi = snapshot["oi"]
                    if opt.ltp == 0 and snapshot.get("ltp", 0) > 0:
                        opt.ltp = snapshot["ltp"]
                    if opt.bid == 0 and snapshot.get("bid", 0) > 0:
                        opt.bid = snapshot["bid"]
                    if opt.ask == 0 and snapshot.get("ask", 0) > 0:
                        opt.ask = snapshot["ask"]
                    if opt.iv == 0 and snapshot.get("iv", 0) > 0:
                        opt.iv = snapshot["iv"]
            except Exception as e:
                logger.warning(f"Cache merge failed: {e}")
            
            # STAGE 4: OPTION UPDATE
            now = time.time()
            if not hasattr(self, '_last_option_log_ts'):
                self._last_option_log_ts = 0
            if now - self._last_option_log_ts > 5:
                logger.info(f"[OPTION UPDATE] {symbol} {strike}{right}")
                self._last_option_log_ts = now

            logger.debug(f"OPTION TICK UPDATED → {symbol} {strike}{right} ltp={opt.ltp} oi={opt.oi}")

            instrument_key = f"{symbol}_{strike}{right}"

            signal = self.oi_buildup_engine.detect(instrument_key, opt.ltp, opt.oi)

            if signal:
                logger.debug("OI SIGNAL → %s → %s", instrument_key, signal)

        except Exception as e:
            logger.error("Option tick update failed: %s", e)

    # --------------------------------------------------

    def get_option_ltp(self, symbol: str, strike: float, right: str) -> float:
        """Helper to get LTP for a specific option contract"""
        try:
            if symbol not in self.chains: return 0.0
            strike = float(round(strike, 2))
            if strike not in self.chains[symbol]: return 0.0
            if right not in self.chains[symbol][strike]: return 0.0
            return self.chains[symbol][strike][right].ltp
        except Exception as e:
            logger.error(f"Error getting option ltp: {e}")
            return 0.0

    def get_latest_snapshot(self, symbol: str):
        """
        Returns a snapshot object for analytics broadcaster.
        Works even when spot price is 0 — never returns None
        if chain data exists.
        """
        chain = self.chains.get(symbol, {})

        # Debug: Log chain structure
        if chain:
            sample_key = list(chain.keys())[0]
            sample_val = chain[sample_key]
            logger.info(
                f"[SNAPSHOT_DEBUG] {symbol} chains has {len(chain)} keys. "
                f"Sample: {list(chain.items())[:1] if chain else 'EMPTY'}"
            )
            logger.info(
                f"[SNAPSHOT DEBUG] First key type={type(sample_key)} "
                f"val={repr(sample_key)[:50]} "
                f"data type={type(sample_val)} "
                f"data keys={list(sample_val.keys()) if isinstance(sample_val, dict) else 'not-dict'}"
            )

        # Return None only if we have zero strike data
        if not chain:
            logger.warning(
                f"get_latest_snapshot: chains[{symbol}] is empty — "
                f"no strike data yet"
            )
            return None

        class ChainSnapshot:
            pass

        snap = ChainSnapshot()

        # Spot price — 0 is acceptable, broadcaster will handle it
        snap.spot       = float(self.spot_prices.get(symbol, 0))
        snap.atm_strike = self._compute_atm(symbol, snap.spot)
        snap.dte        = self._get_dte(symbol)

        # Aggregate from chains dict
        call_oi = 0
        put_oi  = 0
        max_ce_oi     = 0
        max_pe_oi     = 0
        max_ce_strike = 0
        max_pe_strike = 0
        atm_iv        = 0.0
        calls_data    = {}
        puts_data     = {}

        for strike_key, sides in chain.items():
            # strike_key is a number (float/int), sides is a dict with 'CE'/'PE' keys
            try:
                strike = float(strike_key)
                if not isinstance(sides, dict):
                    continue
            except Exception:
                continue

            for right in ('CE', 'PE'):
                raw = sides.get(right)
                if raw is None:
                    continue

                # OptionData is an object — use getattr, NOT dict.get()
                def safe_attr(obj, attr, default=0):
                    val = getattr(obj, attr, None)
                    if val is None:
                        return default
                    try:
                        return float(val)
                    except (ValueError, TypeError):
                        return default

                ltp   = safe_attr(raw, 'ltp')
                oi    = int(safe_attr(raw, 'oi'))
                iv    = safe_attr(raw, 'iv')
                delta = safe_attr(raw, 'delta')
                gamma = safe_attr(raw, 'gamma')
                theta = safe_attr(raw, 'theta')
                vega  = safe_attr(raw, 'vega')
                bid   = safe_attr(raw, 'bid')
                ask   = safe_attr(raw, 'ask')

                entry      = {
                    'ltp': ltp, 'oi': oi, 'iv': iv,
                    'delta': delta, 'gamma': gamma,
                    'theta': theta, 'vega': vega,
                    'bid': bid, 'ask': ask,
                }
                strike_str = str(int(strike))

                if right == 'CE':
                    call_oi += oi
                    calls_data[strike_str] = entry
                    if oi > max_ce_oi:
                        max_ce_oi     = oi
                        max_ce_strike = int(strike)
                    if snap.atm_strike and int(strike) == snap.atm_strike:
                        atm_iv = iv

                else:  # PE
                    put_oi += oi
                    puts_data[strike_str] = entry
                    if oi > max_pe_oi:
                        max_pe_oi     = oi
                        max_pe_strike = int(strike)

        snap.total_call_oi      = call_oi
        snap.total_put_oi       = put_oi
        snap.pcr                = round(float(put_oi) / max(float(call_oi), 1.0), 4)
        snap.max_call_oi_strike = max_ce_strike
        snap.max_put_oi_strike  = max_pe_strike
        snap.atm_iv             = atm_iv
        snap.vwap               = float(
            getattr(self, '_vwap', {}).get(symbol, 0) or 0
        )
        snap.calls_data         = calls_data
        snap.puts_data          = puts_data

        # PCR OVERRIDE: Use tracked aggregate if available (full chain > window)
        tracked_call_oi = getattr(self, '_total_call_oi', {}).get(symbol, 0)
        tracked_put_oi  = getattr(self, '_total_put_oi', {}).get(symbol, 0)

        if tracked_call_oi > call_oi:  # use larger (more complete) value
            snap.total_call_oi = tracked_call_oi
            snap.total_put_oi  = tracked_put_oi
            snap.pcr = round(tracked_put_oi / max(tracked_call_oi, 1), 4)
            logger.info(f"[PCR_OVERRIDE] Using full chain: pcr={snap.pcr:.4f} calls={tracked_call_oi:,} puts={tracked_put_oi:,}")
        else:
            logger.info(f"[PCR_WINDOW] Using window: pcr={snap.pcr:.4f} calls={call_oi:,} puts={put_oi:,}")

        # PHASE 4: Inject AnalyticsEngine for live GEX/Regime
        try:
            from app.analytics.analytics_engine import analytics_engine
            # Construct mapped data for engine
            analytics_input = {
                "symbol": symbol,
                "spot": snap.spot,
                "calls": {
                    strike: {
                        "gamma": data.get("gamma", 0),
                        "oi": data.get("oi", 0)
                    } for strike, data in calls_data.items()
                },
                "puts": {
                    strike: {
                        "gamma": data.get("gamma", 0),
                        "oi": data.get("oi", 0)
                    } for strike, data in puts_data.items()
                }
            }
            snap.analytics = analytics_engine.analyze(analytics_input)
            logger.info(f"[SNAPSHOT_ANALYTICS] Computed GEX={snap.analytics.get('net_gex', 0)} for {symbol}")
        except Exception as e:
            logger.error(f"[SNAPSHOT_ANALYTICS] Failed: {e}")
            snap.analytics = {}

        return snap

    def _compute_atm(self, symbol: str, spot: float) -> int:
        """Compute ATM strike from spot price."""
        if spot <= 0:
            # Fall back to cached ATM if available
            cached = getattr(self, '_atm_strikes', {}).get(symbol, 0)
            return int(cached) if cached else 0

        step = 100 if symbol == 'BANKNIFTY' else 50
        return int(round(spot / step) * step)

    def _get_dte(self, symbol: str) -> int:
        """Get days to expiry for current subscription."""
        try:
            from datetime import datetime, date
            expiry_str = getattr(self, '_current_expiry', {}).get(symbol, '')
            if expiry_str:
                expiry_date = datetime.strptime(expiry_str, '%Y-%m-%d').date()
                return max((expiry_date - date.today()).days, 0)
        except Exception:
            pass
        return 0

    def get_chain(self, symbol: str):
        if symbol not in self.chains:
            return None
        return self._create_snapshot(symbol)


# global instance
option_chain_builder = OptionChainBuilder()