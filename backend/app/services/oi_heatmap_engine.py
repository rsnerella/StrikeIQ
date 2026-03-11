"""
OI Heatmap Engine for StrikeIQ
Calculates OI distribution and intensity for heatmap visualization
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from app.services.option_chain_builder import option_chain_builder

logger = logging.getLogger(__name__)


class OIHeatmapEngine:
    """Computes OI heatmap data for option chain visualization"""

    def __init__(self):

        self._heatmap_task: Optional[asyncio.Task] = None
        self._running = False

        self.heatmap_cache: Dict[str, Dict[str, Any]] = {}

        self.update_interval = 3.0

    async def start(self):

        if self._running:
            return

        self._running = True
        self._heatmap_task = asyncio.create_task(self._heatmap_loop())

        logger.info("OI heatmap engine started")

    async def stop(self):

        self._running = False

        if self._heatmap_task:
            self._heatmap_task.cancel()

            try:
                await self._heatmap_task
            except asyncio.CancelledError:
                pass

        logger.info("OI heatmap engine stopped")

    async def _heatmap_loop(self):

        try:

            while self._running:

                await asyncio.sleep(self.update_interval)

                try:
                    await self._compute_and_broadcast_heatmaps()

                except Exception as e:
                    logger.error(f"Error in heatmap computation: {e}")

        except asyncio.CancelledError:
            logger.info("Heatmap loop stopped")
            raise

    async def _compute_and_broadcast_heatmaps(self):

        try:

            for symbol in ["NIFTY", "BANKNIFTY"]:

                chain_data = option_chain_builder.get_chain(symbol)

                if not chain_data:
                    continue

                heatmap = self._compute_heatmap(chain_data)

                if heatmap:
                    await self._broadcast_heatmap(heatmap)

        except Exception as e:
            logger.error(f"Error computing heatmaps: {e}")

    def _compute_heatmap(self, chain_data) -> Optional[Dict[str, Any]]:

        try:

            # -----------------------------------------
            # SUPPORT BOTH dict AND ChainSnapshot
            # -----------------------------------------

            if isinstance(chain_data, dict):

                symbol = chain_data.get("symbol")
                spot = chain_data.get("spot")
                atm_strike = chain_data.get("atm_strike")
                strikes = chain_data.get("strikes", [])

            else:

                symbol = getattr(chain_data, "symbol", None)
                spot = getattr(chain_data, "spot", None)
                atm_strike = getattr(chain_data, "atm_strike", None)
                strikes = getattr(chain_data, "strikes", [])

            if not strikes:
                return None

            # -----------------------------------------
            # SAFE OI CALCULATION
            # -----------------------------------------

            total_call_oi = sum((s.get("call_oi") or 0) for s in strikes)
            total_put_oi = sum((s.get("put_oi") or 0) for s in strikes)

            pcr = total_put_oi / total_call_oi if total_call_oi > 0 else 0

            max_call_oi = max((s.get("call_oi") or 0) for s in strikes) or 1
            max_put_oi = max((s.get("put_oi") or 0) for s in strikes) or 1

            heatmap_entries = []

            for strike in strikes:

                call_oi = strike.get("call_oi") or 0
                put_oi = strike.get("put_oi") or 0
                strike_price = strike.get("strike")

                call_intensity = call_oi / max_call_oi
                put_intensity = put_oi / max_put_oi

                distance_from_atm = (
                    abs(strike_price - atm_strike) / atm_strike * 100
                    if atm_strike
                    else 0
                )

                entry = {
                    "strike": strike_price,
                    "call_oi_intensity": round(call_intensity, 3),
                    "put_oi_intensity": round(put_intensity, 3),
                    "distance_from_atm": round(distance_from_atm, 2),
                    "call_oi": call_oi,
                    "put_oi": put_oi,
                    "total_oi": call_oi + put_oi
                }

                heatmap_entries.append(entry)

            heatmap_entries.sort(key=lambda x: x["strike"])

            heatmap_data = {
                "type": "heatmap_update",
                "symbol": symbol,
                "timestamp": int(datetime.now().timestamp()),
                "data": {
                    "symbol": symbol,
                    "spot": spot,
                    "atm_strike": atm_strike,
                    "pcr": round(pcr, 3),
                    "total_call_oi": total_call_oi,
                    "total_put_oi": total_put_oi,
                    "heatmap": heatmap_entries
                }
            }

            self.heatmap_cache[symbol] = heatmap_data

            return heatmap_data

        except Exception as e:

            logger.error(f"Error computing heatmap: {e}")

            return None

    async def _broadcast_heatmap(self, heatmap_data):

        try:

            from app.core.ws_manager import manager

            await manager.broadcast(heatmap_data)

            logger.debug(f"Broadcasted heatmap for {heatmap_data['symbol']}")

        except Exception as e:

            logger.error(f"Error broadcasting heatmap: {e}")

    def get_cached_heatmap(self, symbol: str):

        return self.heatmap_cache.get(symbol)


# Global instance
oi_heatmap_engine = OIHeatmapEngine()