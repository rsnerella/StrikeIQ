"""
Option Chain Builder for StrikeIQ
Maintains in-memory option chain and produces snapshots
"""

import asyncio
import logging
import math
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import bisect

from app.services.oi_buildup_engine import OIBuildupEngine
from app.core.diagnostics import diag, increment_counter
from app.core.ai_health_state import mark_health

logger = logging.getLogger(__name__)

@dataclass
class OptionData:
    """Data structure for a single option"""
    strike: float
    ltp: float = 0.0
    oi: int = 0
    volume: int = 0
    last_update: datetime = field(default_factory=datetime.now)

@dataclass
class ChainSnapshot:
    """Snapshot of option chain for broadcasting"""
    symbol: str
    spot: float
    atm_strike: float
    expiry: str
    strikes: List[Dict[str, Any]]
    timestamp: int

class OptionChainBuilder:
    """Builds and maintains real-time option chains"""
    
    def __init__(self):
        # Symbol -> {strike -> {CE/PE -> OptionData}}
        self.chains: Dict[str, Dict[float, Dict[str, OptionData]]] = {}
        
        # Symbol -> current spot price
        self.spot_prices: Dict[str, float] = {}
        
        # Symbol -> last snapshot timestamp
        self.last_snapshots: Dict[str, datetime] = {}
        
        # Background task for periodic snapshots
        self._snapshot_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Default expiry (next Thursday)
        self.default_expiry = self._get_next_expiry()
        
        # Initialize OI Buildup Engine
        self.oi_buildup_engine = OIBuildupEngine()
        logger.info("Option Chain Builder initialized with OI Buildup Engine")
    
    def _get_next_expiry(self) -> str:
        """Get the nearest Thursday expiry date.
        On expiry Thursday before 3:30 PM IST, return today (active expiry).
        After 3:30 PM or if today is not Thursday, return next Thursday.
        """
        import pytz
        ist = pytz.timezone("Asia/Kolkata")
        today = datetime.now(ist).date()
        now_ist = datetime.now(ist)

        days_until_thursday = (3 - today.weekday()) % 7

        if days_until_thursday == 0:
            # Today is Thursday — check if expiry is still active (before 3:30 PM)
            if now_ist.hour < 15 or (now_ist.hour == 15 and now_ist.minute <= 30):
                # Expiry still live — use today
                expiry_date = today
            else:
                # Expiry passed — use next Thursday
                expiry_date = today + timedelta(days=7)
        else:
            expiry_date = today + timedelta(days=days_until_thursday)

        return expiry_date.strftime("%Y-%m-%d")
    
    async def start(self):
        """Start the background snapshot task"""
        if self._running:
            return
        
        self._running = True
        self._snapshot_task = asyncio.create_task(self._snapshot_loop())
        logger.info("Option chain builder started")
    
    async def stop(self):
        """Stop the background task"""
        self._running = False
        if self._snapshot_task:
            self._snapshot_task.cancel()
            try:
                await self._snapshot_task
            except asyncio.CancelledError:
                pass
        logger.info("Option chain builder stopped")
    
    async def _snapshot_loop(self):
        """Periodic snapshot generation"""
        try:
            while self._running:
                try:
                    await asyncio.sleep(0.5)  # 500ms intervals
                    await self._generate_snapshots()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in snapshot loop: {e}")
        except asyncio.CancelledError:
            logger.info("Option chain snapshot loop stopped")
            raise
    
    async def _generate_snapshots(self):
        """Generate snapshots for all active symbols"""

        logger.debug("OPTION CHAIN ENGINE LOOP RUNNING")

        current_time = datetime.now()

        logger.debug(f"SNAPSHOT LOOP SYMBOLS → {list(self.spot_prices.keys())}")

        for symbol in list(self.spot_prices.keys()):

            spot = self.spot_prices.get(symbol, 0)

            # Skip if no chain data yet
            chain = self.chains.get(symbol)
            if not chain:
                continue

            # P3: Evict strikes far from spot to bound memory
            if spot > 0:
                far_strikes = [
                    s for s in list(chain.keys())
                    if abs(s - spot) > 1500
                ]

                for s in far_strikes:
                    chain.pop(s, None)

            # Check if we need to generate snapshot
            last_snapshot = self.last_snapshots.get(symbol, datetime.min)

            if (current_time - last_snapshot).total_seconds() >= 0.5:

                snapshot = self._create_snapshot(symbol)

                if snapshot is None:
                    logger.warning("Snapshot not generated – skipping broadcast")
                    continue

                spot = getattr(snapshot, "spot", None)

                if spot is None:
                    logger.warning("Snapshot missing spot price")
                    continue

                self.last_snapshots[symbol] = current_time

                # DIAGNOSTICS AFTER SUCCESSFUL SNAPSHOT
                diag("CHAIN_ENGINE", "Option chain update triggered")
                increment_counter("chain_updates")

                # ONLY broadcast option chain (tick already comes from market feed)
                await self._broadcast_snapshot(snapshot)
    
    def _create_snapshot(self, symbol: str) -> Optional[ChainSnapshot]:
        """Create a snapshot for the given symbol"""
        try:
            # STEP 3: Add debug log for snapshot creation start
            logger.info(f"CREATE SNAPSHOT CALLED → {symbol}")
            
            # Only require spot price, allow empty chains
            if symbol not in self.spot_prices:
                return None
            
            spot = self.spot_prices[symbol]
            chain = self.chains.get(symbol, {})  # Use .get() to allow empty chains
            
            # Add diagnostic log before building snapshot
            diag("CHAIN", f"Building option chain snapshot from {len(chain)} strikes")
            
            # Find ATM strike (use spot if no strikes available)
            strikes_list = list(chain.keys()) if chain else []
            atm_strike = self._find_atm_strike(spot, strikes_list) if strikes_list else spot
            
            # Add diagnostic logging for ATM calculation
            diag("CHAIN_ENGINE", f"ATM calculated: {atm_strike}")
            
            # Build strikes list
            strikes = []
            sorted_strikes = sorted(chain.keys())
            for strike in sorted_strikes:
                strike_data = chain[strike]
                
                call_data = strike_data.get("CE")
                put_data = strike_data.get("PE")
                
                strike_info = {
                    "strike": strike,
                    "call_oi": call_data.oi if call_data else 0,
                    "call_ltp": call_data.ltp if call_data else 0,
                    "call_volume": call_data.volume if call_data else 0,
                    "put_oi": put_data.oi if put_data else 0,
                    "put_ltp": put_data.ltp if put_data else 0,
                    "put_volume": put_data.volume if put_data else 0
                }
                
                strikes.append(strike_info)
            
            # Add diagnostic logging for option instruments active
            diag("CHAIN_ENGINE", f"Option instruments active: {len(strikes)}")
            
            # Mark option chain as healthy
            mark_health("option_chain")
            
            # STEP 3: Add debug log for snapshot result
            logger.info(f"SNAPSHOT RESULT → spot={spot}")
            
            return ChainSnapshot(
                symbol=symbol,
                spot=spot,
                atm_strike=atm_strike,
                expiry=self.default_expiry,
                strikes=strikes,
                timestamp=int(datetime.now().timestamp())
            )
            
        except Exception as e:
            logger.error(f"Error creating snapshot for {symbol}: {e}")
            return None
    
    def _find_atm_strike(self, spot: float, strikes: List[float]) -> float:
        """Find the ATM strike closest to spot"""
        if not strikes:
            return spot
        
        # Use bisect to find insertion point
        sorted_strikes = sorted(strikes)
        idx = bisect.bisect_left(sorted_strikes, spot)
        
        if idx == 0:
            return sorted_strikes[0]
        elif idx >= len(sorted_strikes):
            return sorted_strikes[-1]
        else:
            # Choose closer strike
            lower = sorted_strikes[idx - 1]
            upper = sorted_strikes[idx]
            return lower if (spot - lower) < (upper - spot) else upper
    
    async def _broadcast_snapshot(self, snapshot: ChainSnapshot):
        """Broadcast snapshot to WebSocket clients"""
        try:
            from app.core.ws_manager import manager
            
            message = {
                "type": "option_chain_update",
                "symbol": snapshot.symbol,
                "timestamp": snapshot.timestamp,
                "data": {
                    "symbol": snapshot.symbol,
                    "spot": snapshot.spot,
                    "atm_strike": snapshot.atm_strike,
                    "expiry": snapshot.expiry,
                    "strikes": snapshot.strikes
                }
            }
            
            await manager.broadcast(message)
            logger.debug(f"Broadcasted option chain snapshot for {snapshot.symbol}")
            
        except Exception as e:
            logger.error(f"Error broadcasting snapshot: {e}")
    
    def update_index_price(self, symbol: str, price: float):
        """Update index spot price"""
        # STEP 2: Add debug log for chain engine receiving tick
        logger.info(f"CHAIN ENGINE RECEIVED TICK → {symbol} {price}")
        
        # STEP 4: Normalize symbol
        symbol = symbol.upper().strip()
        
        if symbol in ["BANKNIFTY", "BANK NIFTY"]:
            symbol = "BANKNIFTY"

        elif symbol == "NIFTY":
            symbol = "NIFTY"
        
        self.spot_prices[symbol] = price
        logger.info(f"SPOT PRICE STORE → {symbol}")
        logger.debug(f"Updated {symbol} spot price to {price}")
    
def update_option_tick(self, symbol: str, strike: float, right: str, ltp: float, oi: int = 0, volume: int = 0):
    """Update option data from tick"""

    try:

        # normalize symbol
        symbol = symbol.upper().strip()

        if symbol in ["BANK NIFTY", "BANKNIFTY"]:
            symbol = "BANKNIFTY"
        elif symbol in ["NIFTY", "NIFTY 50"]:
            symbol = "NIFTY"

        # validate option type
        if right not in ["CE", "PE"]:
            return

        # normalize strike
        strike = float(round(strike, 2))

        logger.debug(
            f"OPTION TICK → {symbol}_{strike}{right} LTP={ltp} OI={oi}"
        )

        if symbol not in self.chains:
            self.chains[symbol] = {}

        if strike not in self.chains[symbol]:
            self.chains[symbol][strike] = {}

        if right not in self.chains[symbol][strike]:
            self.chains[symbol][strike][right] = OptionData(strike=strike)

        option_data = self.chains[symbol][strike][right]

        # guard bad LTP
        if ltp is None or not isinstance(ltp, (int, float)) or ltp < 0:
            return

        option_data.ltp = ltp
        option_data.oi = max(0, oi)
        option_data.volume = max(0, volume)
        option_data.last_update = datetime.utcnow()

        # detect OI buildup
        instrument_key = f"{symbol}_{strike}{right}"

        try:
            signal = self.oi_buildup_engine.detect(instrument_key, ltp, oi)
        except Exception as e:
            logger.error(f"OI engine error: {e}")
            signal = None

        if signal:
            logger.info(f"OI SIGNAL → {instrument_key} → {signal}")

    except Exception as e:
        logger.error(f"Option tick update failed: {e}")
    
    async def process_option_tick(self, tick: dict):
        """
        Receives normalized option ticks from message_router
        and updates the option chain state.
        """

        try:

            instrument_key = tick["instrument_key"]
            ltp = tick.get("ltp")
            oi = tick.get("oi", 0)
            volume = tick.get("volume", 0)

            from app.services.instrument_registry import get_instrument_registry

            registry = get_instrument_registry()

            meta = registry.get_option_meta(instrument_key)

            if not meta:
                return

            symbol = meta["symbol"]
            expiry = meta["expiry"]
            strike = meta["strike"]
            option_type = meta["option_type"]

            if not symbol or not strike or not option_type:
                return

            # Add diagnostic log for option tick processing
            diag("CHAIN", f"Processing option tick strike={strike} type={option_type}")

            # call existing internal update function
            self.update_option_tick(
                symbol=symbol,
                strike=strike,
                right=option_type,
                ltp=ltp,
                oi=oi,
                volume=volume
            )

        except Exception as e:
            logger.error(f"Option chain update failed: {e}")
    
    def get_chain(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get current chain data for a symbol"""
        if symbol not in self.chains or symbol not in self.spot_prices:
            return None
        
        snapshot = self._create_snapshot(symbol)
        if snapshot:
            return {
                "symbol": snapshot.symbol,
                "spot": snapshot.spot,
                "atm_strike": snapshot.atm_strike,
                "expiry": snapshot.expiry,
                "strikes": snapshot.strikes,
                "timestamp": snapshot.timestamp
            }
        
        return None

# Global instance
option_chain_builder = OptionChainBuilder()
