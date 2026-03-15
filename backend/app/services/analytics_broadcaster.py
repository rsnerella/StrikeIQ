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

    async def _compute_and_broadcast(self, symbol: str):
        """
        Executes the AI orchestrator cycle and broadcasts results.
        Adheres to the standardized 'market_update' contract.
        """
        try:
            # 1. Get current chain snapshot
            chain_snapshot = option_chain_builder.get_chain(symbol)
            if not chain_snapshot:
                logger.debug(f"Waiting for chain data: {symbol}")
                return

            # Convert to dict for orchestrator
            snapshot_dict = chain_snapshot.__dict__ if hasattr(chain_snapshot, '__dict__') else chain_snapshot
            spot = snapshot_dict.get("spot", 0)
            
            # 2. Run the 10-step AI Orchestrator cycle
            ai_data = await ai_orchestrator.run_cycle(symbol, snapshot_dict)
            
            # 3. Construct standardized payload (WebSocket Contract)
            payload = {
                "type": "market_update",
                "symbol": symbol,
                "timestamp": int(time.time()),
                "spotPrice": spot,
                "liveSpot": spot,
                "currentSpot": spot,
                "atmStrike": snapshot_dict.get("atm_strike", 0),
                "aiIntelligence": {
                    "regime": ai_data.get("regime"),
                    "bias": ai_data.get("bias"),
                    "bias_strength": ai_data.get("bias_strength"),
                    "early_warnings": ai_data.get("early_warnings", []),
                    "trade_plan": ai_data.get("trade_plan"),
                    "market_summary": ai_data.get("market_summary"),
                    "gamma_analysis": ai_data.get("gamma_analysis"),
                    "volatility_state": ai_data.get("volatility_state"),
                    "confidence_score": ai_data.get("confidence_score"),
                    "drift_score": ai_data.get("drift_score"),
                    "sentiment_overlay": ai_data.get("sentiment_overlay"),
                    "cycle_time_ms": ai_data.get("cycle_time_ms")
                },
                "dataQuality": {
                    "latency_ms": ai_data.get("cycle_time_ms", 0),
                    "accuracy": 0.99, # Placeholder for pipeline accuracy
                    "status": "HEALTHY" if ai_data.get("status") == "AI_READY" else "DEGRADED"
                },
                "aiReady": ai_data.get("status") == "AI_READY"
            }

            # 4. Global cache update (serving new clients)
            global LAST_ANALYTICS
            LAST_ANALYTICS[symbol] = payload

            # 5. Emit payload to all clients
            await manager.broadcast(json.dumps(payload, default=json_safe))
            
            logger.debug(f"BROADCAST COMPLETED: {symbol} (Cycle: {ai_data.get('cycle_time_ms')}ms)")

        except Exception as e:
            logger.error(f"Broadcaster failure for {symbol}: {e}", exc_info=True)

    async def _analytics_loop(self):
        """Main loop ensuring 500ms broadcast cycles"""
        logger.info("Analytics Loop Started")
        while self._running:
            try:
                if not manager.active_connections:
                    await asyncio.sleep(1)
                    continue

                loop_start = time.time()
                
                # Broadly targeting main symbols
                symbols = ["NIFTY", "BANKNIFTY", "FINNIFTY"]
                tasks = [self._compute_and_broadcast(s) for s in symbols]
                await asyncio.gather(*tasks)

                # Control interval
                elapsed = time.time() - loop_start
                sleep_time = max(0, self.ANALYTICS_INTERVAL - elapsed)
                await asyncio.sleep(sleep_time)

            except Exception as e:
                logger.error(f"Loop error: {e}")
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