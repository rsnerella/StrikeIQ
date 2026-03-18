import asyncio
from datetime import datetime, date
from app.services.live_option_chain_builder import LiveOptionChainBuilder
from app.core.ws_manager import manager, broadcast_with_strategy
from app.analytics.greeks_engine import greeks_engine
import logging
import time

logger = logging.getLogger(__name__)

class LiveChainManager:

    def __init__(self):
        self.builders = {}
        self.lock = asyncio.Lock()
        self.chain = {}  # Full option chain storage
        self._broadcast_lock = asyncio.Lock()  # Broadcast lock for thread safety
        self._last_broadcast = 0  # Throttling timestamp
        self._last_spot = None  # For greeks performance optimization
        self.MAX_STRIKES = 200  # Memory limit

    async def get_builder(self, symbol: str, expiry):

        # NORMALIZE EXPIRY
        if isinstance(expiry, str):
            expiry = datetime.strptime(expiry, "%Y-%m-%d").date()

        if isinstance(expiry, datetime):
            expiry = expiry.date()

        key = f"{symbol}:{expiry.isoformat()}"

        async with self.lock:

            if key in self.builders:
                print(f"♻️ REUSING Builder → {key}")
                return self.builders[key]

            print(f"🔨 CREATING Builder → {key}")

            builder = LiveOptionChainBuilder(
                symbol=symbol,
                expiry=expiry
            )

            self.builders[key] = builder

            return builder

    async def update_tick(self, tick):
        """Update option chain with new tick data"""
        try:
            # Extract strike and option type from instrument key
            instrument_key = tick.get("instrument_key", "")
            if not instrument_key or "|" not in instrument_key:
                return
            
            # Parse instrument key to get strike and option type
            # Format: NSE_FO|NIFTY-30-Jan-2025-24100-CE
            parts = instrument_key.split("|")
            if len(parts) < 2:
                return
                
            instrument_details = parts[1]
            detail_parts = instrument_details.split("-")
            
            if len(detail_parts) < 5:
                return
                
            # Extract strike (second to last part) and option type (last part)
            try:
                strike = int(detail_parts[-2].lstrip('0') or 0)  # Safe parsing
                option_type = detail_parts[-1]  # CE or PE
            except (ValueError, IndexError):
                return

            # Initialize strike in chain if not exists
            self.chain.setdefault(strike, {"CE": {}, "PE": {}})
            
            # Update option data
            self.chain[strike][option_type] = {
                "ltp": tick.get("ltp"),
                "oi": tick.get("oi"),
                "volume": tick.get("volume"),
                "iv": tick.get("iv")
            }

            # Cache chain in Redis (throttled to prevent Redis storm)
            try:
                import json
                import time
                from app.core.redis_client import redis_client
                
                # Throttle Redis writes to once per second
                if not hasattr(self, "_last_redis_write"):
                    self._last_redis_write = 0
                
                now = time.time()
                if now - self._last_redis_write > 1:
                    redis_client.set(
                        "strikeiq:option_chain",
                        json.dumps(self.chain, default=float),
                        ex=300  # 5 minutes TTL
                    )
                    self._last_redis_write = now
            except Exception:
                pass  # Redis is optional

            logger.info(f"CHAIN UPDATED strike={strike} type={option_type} ltp={tick.get('ltp')}")
            
            # Manage memory to prevent unlimited growth
            self._manage_memory()
            
            # Broadcast updated chain
            await self.broadcast_chain()
            
        except Exception as e:
            logger.error(f"Error updating tick: {e}")

    async def broadcast_chain(self, spot=None):
        """Broadcast option chain to all WebSocket clients with greeks and throttling"""
        try:
            # Throttle broadcasts to 200ms minimum with broadcast lock
            async with self._broadcast_lock:
                current_time = time.time() * 1000  # Convert to milliseconds
                if current_time - self._last_broadcast < 200:
                    return
                
                self._last_broadcast = current_time
                
                # Compute greeks if spot is available
                if spot and self.chain:
                    self.chain = greeks_engine.compute_chain_greeks(self.chain, spot)
                
                await broadcast_with_strategy(
                    {
                        "type": "option_chain",
                        "chain": self.chain
                    }
                )
                logger.info("BROADCAST option_chain")
        except Exception as e:
            logger.error(f"Error broadcasting chain: {e}")

    async def update_spot_and_compute_greeks(self, spot):
        """Update spot price and recompute greeks for entire chain with 2-point threshold"""
        try:
            # Only recompute greeks if spot moved more than 2 points
            if self._last_spot is None or abs(spot - self._last_spot) > 2:
                if self.chain:
                    self.chain = greeks_engine.compute_chain_greeks(self.chain, spot)
                    await self.broadcast_chain(spot)
                    logger.info(f"GREEKS RECOMPUTED for spot={spot} (moved from {self._last_spot})")
                self._last_spot = spot
            else:
                # Still broadcast spot update without recompute
                await self.broadcast_chain(spot)
                logger.info(f"SPOT UPDATED without greeks recompute: {spot}")
        except Exception as e:
            logger.error(f"Error updating spot and computing greeks: {e}")

    def _manage_memory(self):
        """Limit chain memory to MAX_STRIKES with ATM-proximate filtering"""
        try:
            if len(self.chain) > self.MAX_STRIKES:
                sorted_strikes = sorted(self.chain.keys())
                
                # If we have spot price, keep ATM-proximate strikes
                if self._last_spot:
                    atm = min(sorted_strikes, key=lambda x: abs(x - self._last_spot))
                    # Sort by distance from ATM and keep closest MAX_STRIKES
                    filtered = sorted(sorted_strikes, key=lambda x: abs(x - atm))[:self.MAX_STRIKES]
                    self.chain = {k: self.chain[k] for k in filtered}
                else:
                    # Fallback: remove oldest ones
                    strikes_to_remove = sorted_strikes[:-self.MAX_STRIKES]
                    for strike in strikes_to_remove:
                        del self.chain[strike]
                
                logger.info(f"MEMORY CLEANUP: kept {len(self.chain)} ATM-proximate strikes")
        except Exception as e:
            logger.error(f"Error managing memory: {e}")

chain_manager = LiveChainManager()