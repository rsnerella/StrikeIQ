# app/services/analytics_broadcaster.py

"""
Analytics Broadcaster for StrikeIQ
Stable production version
"""

import asyncio
import logging
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

        # engines (lazy loaded)
        self._bias_engine = None
        self._expected_move_engine = None
        self._structural_engine = None

    # --------------------------------------------------------
    # ANALYTICS COMPUTATION
    # --------------------------------------------------------

    async def _compute_analytics(
        self, symbol: str, chain_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:

        try:

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

                    logger.info(f"COMPUTING MARKET BIAS FOR {symbol}")

                    bias = bias_engine.compute(engine_data)

                    analytics_results["market_bias"] = {
                        "pcr": bias.pcr,
                        "bias": bias.bias,
                        "bias_strength": bias.bias_strength,
                    }

                except Exception as e:
                    logger.error(f"Error computing market bias: {e}")

            # -----------------------
            # EXPECTED MOVE
            # -----------------------

            move_engine = self._get_expected_move_engine()

            if move_engine and engine_data["calls"] and engine_data["puts"]:

                try:

                    logger.info(f"COMPUTING EXPECTED MOVE FOR {symbol}")

                    move = move_engine.compute(engine_data)

                    analytics_results["expected_move"] = {
                        "range": move.range,
                        "probability": move.probability,
                    }

                except Exception as e:
                    logger.error(f"Error computing expected move: {e}")

            # -----------------------
            # STRUCTURAL ANALYSIS
            # -----------------------

            structural_engine = self._get_structural_engine()

            if structural_engine and engine_data["calls"] and engine_data["puts"]:

                try:

                    logger.info(f"COMPUTING STRUCTURAL ANALYSIS FOR {symbol}")

                    structural = structural_engine.compute(engine_data)

                    analytics_results["structural"] = {
                        "gamma": structural.gamma,
                        "vega": structural.vega,
                        "theta": structural.theta,
                        "delta": structural.delta,
                    }

                except Exception as e:
                    logger.error(f"Error computing structural analysis: {e}")

            # metadata
            analytics_results["symbol"] = symbol
            analytics_results["timestamp"] = datetime.now().isoformat()

            # cache store
            self.analytics_cache[symbol] = analytics_results

            logger.info(
                f"ANALYTICS COMPUTED FOR {symbol} → {len(analytics_results)} fields"
            )

            return analytics_results

        except Exception as e:

            logger.error(f"Error computing analytics for {symbol}: {e}")
            return None

    # --------------------------------------------------------
    # BROADCAST
    # --------------------------------------------------------

    async def _broadcast_analytics(self, analytics_data: Dict[str, Any]):

        try:

            from app.core.ws_manager import manager

            logger.info(
                f"BROADCASTING ANALYTICS UPDATE → {analytics_data.get('symbol','UNKNOWN')}"
            )

            await manager.broadcast(analytics_data)

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

        while self._running:

            try:

                logger.info("COMPUTING ANALYTICS FOR ACTIVE SYMBOLS")

                for symbol in ["NIFTY", "BANKNIFTY"]:

                    logger.info(f"PROCESSING ANALYTICS FOR {symbol}")

                    chain_data = option_chain_builder.get_chain(symbol)

                    if chain_data:

                        analytics = await self._compute_analytics(symbol, chain_data)

                        if analytics:
                            await self._broadcast_analytics(analytics)

                    else:

                        logger.warning(f"No chain data available for {symbol}")

                await asyncio.sleep(self.update_interval)

            except Exception as e:

                logger.error(f"Error in analytics loop: {e}")

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

                from app.services.live_structural_engine import (
                    LiveStructuralEngine,
                    market_state_mgr,
                )

                self._structural_engine = LiveStructuralEngine(market_state_mgr())

            except ImportError as e:

                logger.error(f"Could not import LiveStructuralEngine: {e}")

        return self._structural_engine


# --------------------------------------------------------
# GLOBAL INSTANCE (IMPORTANT)
# --------------------------------------------------------

analytics_broadcaster = AnalyticsBroadcaster()