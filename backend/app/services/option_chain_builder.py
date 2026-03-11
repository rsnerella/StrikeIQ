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

from app.services.oi_buildup_engine import OIBuildupEngine
from app.core.diagnostics import diag, increment_counter
from app.core.ai_health_state import mark_health

logger = logging.getLogger(__name__)


@dataclass
class OptionData:
    strike: float
    ltp: float = 0.0
    oi: int = 0
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


class OptionChainBuilder:

    def __init__(self):

        self.chains: Dict[str, Dict[float, Dict[str, OptionData]]] = {}

        self.spot_prices: Dict[str, float] = {}

        self.last_snapshots: Dict[str, datetime] = {}
        
        self.stale_timeout = 300  # 5 minutes

        self._snapshot_task: Optional[asyncio.Task] = None
        self._running = False

        self.default_expiry = self._get_next_expiry()

        self.oi_buildup_engine = OIBuildupEngine()

        logger.info("Option Chain Builder initialized")

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

            # Evict far strikes
            far = [s for s in chain.keys() if abs(s - spot) > 1500]

            for s in far:
                chain.pop(s, None)

            last = self.last_snapshots.get(symbol, datetime.min)

            if (now - last).total_seconds() < 0.5:
                continue

            snapshot = self._create_snapshot(symbol)

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

        if symbol not in self.spot_prices:
            return None

        spot = self.spot_prices[symbol]

        chain = self.chains.get(symbol, {})

        strikes = []

        strike_keys = sorted(chain.keys())

        atm = self._find_atm_strike(spot, strike_keys)
        
        now = datetime.utcnow()

        for strike in strike_keys:

            data = chain[strike]

            ce = data.get("CE")
            pe = data.get("PE")
            
            ce_valid = ce and (now - ce.last_update).total_seconds() <= 30
            pe_valid = pe and (now - pe.last_update).total_seconds() <= 30
            
            if not ce_valid and not pe_valid:
                continue

            strikes.append(
                {
                    "strike": strike,
                    "call_oi": ce.oi if ce_valid else 0,
                    "call_ltp": ce.ltp if ce_valid else 0,
                    "call_volume": ce.volume if ce_valid else 0,
                    "put_oi": pe.oi if pe_valid else 0,
                    "put_ltp": pe.ltp if pe_valid else 0,
                    "put_volume": pe.volume if pe_valid else 0,
                }
            )

        # Calculate PCR and total OI
        total_call_oi = sum(strike.get("call_oi", 0) for strike in strikes)
        total_put_oi = sum(strike.get("put_oi", 0) for strike in strikes)
        pcr = total_put_oi / total_call_oi if total_call_oi > 0 else 0.0

        logger.info(f"[CHAIN_OI_SUMMARY] strikes={len(strikes)} call_oi={total_call_oi} put_oi={total_put_oi}")

        mark_health("option_chain")

        return ChainSnapshot(
            symbol=symbol,
            spot=spot,
            atm_strike=atm,
            expiry=self.default_expiry,
            strikes=strikes,
            timestamp=int(datetime.utcnow().timestamp()),
            pcr=pcr,
            total_oi_calls=total_call_oi,
            total_oi_puts=total_put_oi
        )

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

            from app.core.ws_manager import manager
            from app.services.analytics_broadcaster import analytics_broadcaster

            logger.info(f"PIPELINE → chain updated {snapshot.symbol}")
            logger.info(f"CHAIN SNAPSHOT → {snapshot.symbol} spot={snapshot.spot} atm={snapshot.atm_strike} pcr={snapshot.pcr} calls={snapshot.total_oi_calls} puts={snapshot.total_oi_puts}")
            logger.info(f"CHAIN STRIKES → {len(snapshot.strikes)}")
            
            # OI SANITY CHECK - Permanent debug metric
            logger.info(f"[DATA_HEALTH] strikes={len(snapshot.strikes)} call_oi={snapshot.total_oi_calls:,} put_oi={snapshot.total_oi_puts:,} pcr={snapshot.pcr:.2f}")
            
            # OI Data Health Alert
            if len(snapshot.strikes) > 0 and snapshot.total_oi_calls == 0 and snapshot.total_oi_puts == 0:
                logger.warning("[DATA_HEALTH_ALERT] OI values zero - feed issue possible")
            
            # Broadcast option chain update
            pipeline_start = time.perf_counter()
            await manager.broadcast(
                {
                    "type": "option_chain_update",
                    "symbol": snapshot.symbol,
                    "timestamp": snapshot.timestamp,
                    "data": snapshot.__dict__,
                }
            )
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
                await analytics_broadcaster.compute_single_analytics(snapshot.symbol, snapshot.__dict__)
                logger.info(f"PIPELINE → analytics engine called {snapshot.symbol}")
            except Exception as e:
                logger.error(f"PIPELINE → analytics engine failed {snapshot.symbol}: {e}")

            logger.info("CHAIN BROADCAST SUCCESS")

        except Exception as e:
            logger.error("Snapshot broadcast error: %s", e)

    # --------------------------------------------------

    def update_index_price(self, symbol: str, price: float):

        symbol = symbol.upper().replace(" ", "")

        if symbol == "BANKNIFTY":
            symbol = "BANKNIFTY"

        if symbol == "NIFTY":
            symbol = "NIFTY"

        self.spot_prices[symbol] = price

    # --------------------------------------------------

    def update_option_tick(
        self,
        symbol: str,
        strike: float,
        right: str,
        ltp: float,
        oi: int = 0,
        volume: int = 0,
    ):

        try:

            symbol = symbol.upper().replace(" ", "")

            if right not in ("CE", "PE"):
                return

            strike = float(round(strike, 2))

            if symbol not in self.chains:
                self.chains[symbol] = {}

            if strike not in self.chains[symbol]:
                self.chains[symbol][strike] = {}

            if right not in self.chains[symbol][strike]:
                self.chains[symbol][strike][right] = OptionData(strike=strike)

            opt = self.chains[symbol][strike][right]

            if ltp is not None and ltp >= 0:
                opt.ltp = ltp
            if oi > 0:
                opt.oi = oi
            if volume > 0:
                opt.volume = volume
                
            opt.last_update = datetime.utcnow()
            
            logger.debug(f"OPTION TICK UPDATED → {symbol} {strike}{right} ltp={ltp} oi={oi}")

            instrument_key = f"{symbol}_{strike}{right}"

            signal = self.oi_buildup_engine.detect(instrument_key, ltp, oi)

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

    def get_chain(self, symbol: str):

        if symbol not in self.chains:
            return None

        return self._create_snapshot(symbol)


# global instance
option_chain_builder = OptionChainBuilder()