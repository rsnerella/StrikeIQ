import asyncio
import json
import logging
import time
import os
from typing import Optional, List
from datetime import datetime

import httpx
import websockets
from fastapi import HTTPException

# Month mapping for expiry parsing
MONTH_MAP = {
    "JAN":1,"FEB":2,"MAR":3,"APR":4,
    "MAY":5,"JUN":6,"JUL":7,"AUG":8,
    "SEP":9,"OCT":10,"NOV":11,"DEC":12
}

from app.services.token_manager import token_manager
from app.services.market_session_manager import get_market_session_manager
from app.services.upstox_protobuf_parser_v3 import decode_protobuf_message, extract_index_price
from app.proto.MarketDataFeedV3_pb2 import FeedResponse
from app.core.live_market_state import MarketStateManager
from app.core.market_context import MARKET_CONTEXT
from app.services.live_chain_manager import chain_manager
from app.core.ws_manager import manager
from app.services.instrument_registry import get_instrument_registry
from app.services.live_structural_engine import LiveStructuralEngine
from app.core.live_market_state import get_market_state_manager
from app.core.logging_config import TICK_DEBUG
from app.core.diagnostics import diag, increment_counter

# Global market feed instance
market_feed_instance = None

def get_market_feed():
    """Get the global market feed instance"""
    return market_feed_instance

# Import new components
from app.services.message_router import message_router
from app.services.option_chain_builder import option_chain_builder
from app.services.oi_heatmap_engine import oi_heatmap_engine
from app.services.analytics_broadcaster import analytics_broadcaster

logger = logging.getLogger(__name__)

# Tick log throttling
_last_tick_log = 0

last_market_status = None


def get_index_instrument_keys():
    with open("app/data/NSE.json", "r") as f:
        instruments = json.load(f)
    
    keys = []
    
    for item in instruments:
        
        if item.get("segment") == "NSE_INDEX":
            
            symbol = item.get("trading_symbol")
            
            if symbol in ["NIFTY 50", "NIFTY BANK"]:
                
                keys.append(item.get("instrument_key"))
    
    return keys


def resolve_symbol_from_instrument(instrument_key: str):
    if not instrument_key:
        return None

    if instrument_key == "NSE_INDEX|NIFTY 50":
        return "NIFTY"

    if instrument_key == "NSE_INDEX|NIFTY BANK":
        return "BANKNIFTY"

    if "BANKNIFTY" in instrument_key:
        return "BANKNIFTY"

    if "FINNIFTY" in instrument_key:
        return "FINNIFTY"

    if "MIDCPNIFTY" in instrument_key:
        return "MIDCPNIFTY"

    if "NIFTY" in instrument_key:
        return "NIFTY"

    return None


class WebSocketMarketFeed:

    def __init__(self):

        self.session_manager = get_market_session_manager()
        self.market_state_manager = MarketStateManager()
        
        # Initialize AI engine for analytics
        market_state_mgr = get_market_state_manager()
        self.ai_engine = LiveStructuralEngine(market_state_mgr)

        self.websocket = None
        self.is_connected = False
        self.running = False
        self._connecting = False
        self._reconnecting = False
        self._subscription_sent = False

        self._message_queue = asyncio.Queue(maxsize=5000)
        self._recv_task: Optional[asyncio.Task] = None
        self._process_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._metrics_task: Optional[asyncio.Task] = None

        self._client = httpx.AsyncClient(timeout=30)
        
        # Option subscription tracking - CONSOLIDATED
        self.current_atms = {"NIFTY": None, "BANKNIFTY": None}
        self.last_atms = {"NIFTY": None, "BANKNIFTY": None}
        self.current_expiries = {"NIFTY": None, "BANKNIFTY": None}
        self.current_option_keys = []
        self.subscribed_instruments = set()
        self.dropped_ticks = 0
        self.last_subscription_time = 0
        self.processed_ticks = 0
        self.last_queue_warning = 0
        self.max_tick_latency = 0
        self.tick_counter = 0
        self.instrument_registry = get_instrument_registry()
        self.last_index_prices = {"NIFTY": None, "BANKNIFTY": None}
        self._failsafe_task: Optional[asyncio.Task] = None  # P5: track to prevent leaks
        self._disconnect_task: Optional[asyncio.Task] = None  # P1: track to prevent duplicate reconnects
        self._atm_shift_task: Optional[asyncio.Task] = None  # P3: track ATM shift tasks
        self._option_sub_task: Optional[asyncio.Task] = None  # P3: track option subscription tasks
        
        # AUDIT METRICS - STEP 1: Queue Consumer Lag Detection
        self.max_queue_size = 0
        self.avg_queue_size = 0
        self.queue_size_samples = []
        self.queue_size_total = 0
        self.last_queue_lag_warning = 0
        
        # AUDIT METRICS - STEP 2: Tick Pipeline Throughput
        self.processed_ticks_10s = 0
        self.last_throughput_log = 0
        
        # AUDIT METRICS - STEP 3: Option Chain Builder CPU Time
        self.max_option_builder_time = 0
        self.slow_option_builder_count = 0
        
        # AUDIT METRICS - STEP 4: Message Router Latency
        self.max_router_latency = 0
        self.slow_router_count = 0
        
        # AUDIT METRICS - STEP 5: WebSocket Reconnect Stability
        self.duplicate_task_warnings = 0
        
        # AUDIT METRICS - STEP 6: Option Subscription Storm Detection
        self.subscription_counter = 0
        self.last_subscription_report = 0
        
        # AUDIT METRICS - STEP 7: Redis Latency Monitoring
        self.max_redis_latency = 0
        self.slow_redis_count = 0
        
        # AUDIT METRICS - STEP 8: WebSocket Broadcast Latency
        self.max_broadcast_latency = 0
        self.slow_broadcast_count = 0
        self.feeds_received_count = 0
        
        # PATCH 2: Symbol-driven subscription state
        self.active_symbol = None
        self.active_expiry = None
        self.last_spot_price = {}
        self.current_atm = None
        self._subscription_lock = asyncio.Lock()  # P4: prevent subscription race conditions

    async def stop(self):
        """Stop the WebSocket market feed"""
        logger.info("Stopping market feed...")
        self.running = False
        
        # Close WebSocket connection
        if hasattr(self, "websocket") and self.websocket:
            await self.websocket.close()
        
        # Cancel background tasks
        if hasattr(self, "_option_sub_task") and self._option_sub_task:
            self._option_sub_task.cancel()
            try:
                await self._option_sub_task
            except asyncio.CancelledError:
                pass
        
        # Stop components
        try:
            from app.services.option_chain_builder import option_chain_builder
            await option_chain_builder.stop()
        except Exception as e:
            logger.warning(f"Option chain builder stop error: {e}")
        
        try:
            from app.services.oi_heatmap_engine import oi_heatmap_engine
            await oi_heatmap_engine.stop()
        except Exception as e:
            logger.warning(f"OI heatmap stop error: {e}")
        
        try:
            from app.services.analytics_broadcaster import analytics_broadcaster
            await analytics_broadcaster.stop()
        except Exception as e:
            logger.warning(f"Analytics broadcaster stop error: {e}")
        
        logger.info("Market feed stopped")

    async def start(self):

        if self.running:
            return

        self.running = True

        # Start CPU profiling (debug mode only)
        self.profiler = None
        if os.getenv("STRIKEIQ_PROFILE") == "1":
            import cProfile
            self.profiler = cProfile.Profile()
            self.profiler.enable()

        # Start new components
        await option_chain_builder.start()
        await oi_heatmap_engine.start()
        await analytics_broadcaster.start()

        # Try to connect, but don't fail if authentication fails
        success = await self.ensure_connection()
        
        if not success:
            logger.warning("⚠️ WebSocket connection failed - running in REST-only mode")

        # Always start worker tasks
        self._start_tasks()

        if self.profiler and not getattr(self, "_profile_task", None):
            self._profile_task = asyncio.create_task(self._profile_logger())

        logger.info("Shared Upstox WS started")

    def _start_tasks(self):
        # AUDIT METRICS - STEP 5: WebSocket Reconnect Stability - Detect duplicate async tasks
        if self._recv_task and not self._recv_task.done():
            logger.warning("DUPLICATE_RECV_TASK_DETECTED")
            self.duplicate_task_warnings += 1
        if self._process_task and not self._process_task.done():
            logger.warning("DUPLICATE_PROCESS_TASK_DETECTED")
            self.duplicate_task_warnings += 1
        if self._heartbeat_task and not self._heartbeat_task.done():
            logger.warning("DUPLICATE_HEARTBEAT_TASK_DETECTED")
            self.duplicate_task_warnings += 1
        if getattr(self, "_metrics_task", None) and not self._metrics_task.done():
            logger.warning("DUPLICATE_METRICS_TASK_DETECTED")
            self.duplicate_task_warnings += 1
        if getattr(self, "_throughput_task", None) and not self._throughput_task.done():
            logger.warning("DUPLICATE_THROUGHPUT_TASK_DETECTED")
            self.duplicate_task_warnings += 1

        self._recv_task = asyncio.create_task(self._recv_loop())
        self._process_task = asyncio.create_task(self._process_loop())
        self._heartbeat_task = asyncio.create_task(self._heartbeat())
        self._metrics_task = asyncio.create_task(self._metrics_loop())

    async def _cancel_tasks(self):

        tasks = [
            self._recv_task, 
            self._process_task, 
            self._heartbeat_task, 
            self._metrics_task,
            getattr(self, "_profile_task", None),
            getattr(self, "_throughput_task", None),
            self._atm_shift_task,  # P3: Cancel ATM shift task
            self._option_sub_task,  # P3: Cancel option subscription task
            self._failsafe_task     # P3: Cancel failsafe task
        ]
        
        # Cancel all tasks safely
        for task in tasks:
            if task and not task.done():
                task.cancel()
        
        # Wait for tasks to complete without recursion
        await asyncio.gather(*[t for t in tasks if t], return_exceptions=True)

    async def _connect(self, token: str):
        """Internal connection method using Upstox V3 API"""
        
        if not token:
            raise Exception("Upstox token missing")
        
        logger.info("Getting Upstox V3 WebSocket URL...")
        
        # Get authorized WebSocket URL from V3 API
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        }
        
        client = self._client
        response = await client.get(
            "https://api.upstox.com/v3/feed/market-data-feed/authorize",
            headers=headers
        )
        
        if response.status_code != 200:
            raise Exception(f"V3 authorization failed: {response.status_code}")
        
        data = response.json()
        ws_url = data.get("data", {}).get("authorized_redirect_uri")
        
        if not ws_url:
            raise Exception("No WebSocket URL in V3 response")
        
        logger.info(f"Connecting to Upstox V3 WebSocket: {ws_url}")
        
        # Connect to V3 WebSocket (binary data expected)
        self.websocket = await websockets.connect(
            ws_url,
            ping_interval=20,
            ping_timeout=20
        )
        self.is_connected = True
        
        logger.info("🟢 UPSTOX WS CONNECTED")
        logger.info("WS HANDSHAKE COMPLETE — STABILIZING CONNECTION")
        await asyncio.sleep(1)
        logger.info("READY TO SEND SUBSCRIPTION")
        
        await self.subscribe_indices()
        
        # PATCH: Auto-trigger default subscription for initial data flow
        try:
            instrument_registry = get_instrument_registry()
            expiries = instrument_registry.get_expiries("NIFTY")
            if expiries:
                # Select nearest expiry (sorted by date)
                from datetime import datetime
                nearest_expiry = sorted(expiries, key=lambda x: datetime.strptime(x, '%Y-%m-%d'))[0]
                logger.info(f"AUTO-SUBSCRIPTION TRIGGER → NIFTY {nearest_expiry}")
                await self.switch_symbol("NIFTY", nearest_expiry)
            else:
                logger.warning("No NIFTY expiries available for auto-subscription")
        except Exception as e:
            logger.error(f"Auto-subscription failed: {e}")

    async def connect(self):
        """Public connection method - deprecated, use ensure_connection"""
        token = await token_manager.get_token()
        await self._connect(token)
    
    async def ensure_connection(self):
        """
        Ensure websocket connection exists.
        Used by main startup.
        """

        try:

            if self.is_connected:
                return True

            token = await token_manager.get_token()

            if not token:
                logger.warning("⚠️ No Upstox token available")
                return False

            await self._connect(token)

            return True

        except Exception as e:

            logger.error(f"WS connection failed: {e}")
            self.is_connected = False

            return False

    async def subscribe_indices(self):
        """
        Initialize instrument registry only.
        Subscriptions now handled via switch_symbol() calls.
        """

        try:

            instrument_registry = get_instrument_registry()
            await instrument_registry.wait_until_ready()
            
            # Store instrument registry for expiry detection
            self.instrument_registry = instrument_registry
            
            logger.info("Instrument registry initialized - ready for symbol-driven subscriptions")
            logger.info("SUBSCRIPTION MODE → Symbol-driven (no automatic dual subscription)")

        except Exception as e:
            logger.error(f"Registry initialization failed: {e}")

    async def subscribe_options(self, instrument_keys, atm=None):
        """Subscribe to option instruments"""
        try:
            # AUDIT METRICS - STEP 6: Option Subscription Storm Detection
            self.subscription_counter += 1
            
            # Rate limiter: prevent subscription spam, but allow ATM changes
            if time.time() - self.last_subscription_time < 2 and atm == self.last_atm:
                return
            
            # Unsubscribe from old options first
            await self.unsubscribe_options()
            
            # Filter out already subscribed instruments with thread safety
            async with self._subscription_lock:
                new_keys = []
                for k in instrument_keys:
                    if k not in self.subscribed_instruments:
                        new_keys.append(k)
            
            if not new_keys:
                logger.info("No new option instruments to subscribe")
                return
            
            payload = {
                "guid": "strikeiq-options",
                "method": "sub",
                "data": {
                    "mode": "full",
                    "instrumentKeys": new_keys
                }
            }
            
            if self.websocket:
                logger.info("SUBSCRIPTION PAYLOAD → %s", json.dumps(payload, indent=2))
                # ==================== STRICT PROTECTED SECTION ====================
                # WARNING: DO NOT MODIFY THIS LINE WITHOUT EXPLICIT REVIEW.
                # This WebSocket subscription must be sent as UTF-8 encoded bytes.
                # Changing this to plain json string will break Upstox V3 feed
                # and result in heartbeat / market_info frames only (no market feeds).
                # If modification is required, confirm protocol compatibility first.
                # ==================================================================
                await self.websocket.send(json.dumps(payload).encode("utf-8"))
                logger.info("SUBSCRIPTION SENT SUCCESSFULLY")
                self.current_option_keys = new_keys
                self.subscribed_instruments.update(new_keys)
                self.last_subscription_time = time.time()
                self.last_atm = atm
                logger.info(f"✅ OPTIONS SUBSCRIPTION SENT: {len(new_keys)} instruments")
            else:
                logger.error("Cannot subscribe to options - WebSocket not connected")
                
        except Exception as e:
            logger.error(f"Option subscription failed: {e}")

    def parse_expiry(self, expiry: str):
        """
        Parse expiry strings from Upstox instrument registry.
        Supports ISO and legacy formats.
        """
        formats = [
            "%Y-%m-%d",   # Upstox registry format (PRIMARY)
            "%d-%b-%Y",
            "%d%b%Y",
            "%d%b"
        ]
        
        for fmt in formats:
            try:
                parsed = datetime.strptime(expiry, fmt)
                
                # If year missing (example: 27MAR)
                if parsed.year == 1900:
                    parsed = parsed.replace(year=datetime.now().year)
                
                return parsed
                
            except ValueError:
                continue
        
        logger.warning(f"Invalid expiry format: {expiry}")
        return None

    async def _check_and_subscribe_options(self, symbol: str, atm: int):
        """Helper to manage ATM-based option subscriptions for a specific symbol"""
        if atm != self.current_atms.get(symbol):
            # Rate limiter: prevent subscription spam, but allow ATM changes
            if time.time() - self.last_subscription_time < 2 and atm == self.last_atms.get(symbol):
                return
            
            self.current_atms[symbol] = atm
            expiry = self.active_expiry
            
            if not expiry:
                return
                
            option_keys = build_option_keys(
                symbol=symbol,
                atm=atm,
                expiry=expiry
            )
            logger.info(f"DEBUG TOTAL OPTION INSTRUMENTS FOR {symbol} → {len(option_keys)}")
            
            # Limit subscription to prevent overload
            if len(option_keys) > 60:
                option_keys = option_keys[:60]
            
            logger.debug(f"SUBSCRIBING OPTIONS AROUND ATM {atm} for {symbol}")
            logger.debug(f"EXPIRY → {expiry}")
            
            payload = {
                "guid": f"strikeiq-options-{symbol.lower()}",
                "method": "sub",
                "data": {
                    "mode": "full",
                    "instrumentKeys": option_keys
                }
            }
            
            if self.websocket:
                logger.info("SUBSCRIPTION PAYLOAD → %s", json.dumps(payload, indent=2))
                payload_bytes = json.dumps(payload).encode("utf-8")
                await self.websocket.send(payload_bytes)
                logger.info(f"OPTIONS SUBSCRIPTION SENT → {len(option_keys)} instruments for {symbol}")
            
            self.last_subscription_time = time.time()
            self.last_atms[symbol] = atm

    def get_nearest_nifty_expiry(self, symbol: str = "NIFTY"):
        """Get the nearest expiry for symbol from instrument registry"""
        if not self.instrument_registry:
            logger.error("Instrument registry not loaded")
            return None

        expiries = []
        logger.info(f"SCANNING REGISTRY FOR {symbol} EXPIRIES")

        # Use registry methods instead of direct data access
        expiries = self.instrument_registry.get_expiries(symbol)

        valid_expiries = []

        for expiry in expiries:
            parsed = self.parse_expiry(expiry)
            
            if parsed:
                valid_expiries.append((parsed, expiry))

        if not valid_expiries:
            logger.error(f"No valid {symbol} expiries detected")
            return None

        nearest_expiry, nearest_expiry_str = min(valid_expiries, key=lambda x: x[0])

        logger.debug(f"AVAILABLE EXPIRIES for {symbol} → {expiries}")
        logger.debug(f"DETECTED {symbol} EXPIRY → {nearest_expiry_str}")

        return nearest_expiry_str

    async def unsubscribe_options(self):
        """Unsubscribe from current option instruments"""
        if not self.current_option_keys:
            return
            
        try:
            payload = {
                "guid": "strikeiq-options-unsub",
                "method": "unsub",
                "data": {
                    "instrumentKeys": self.current_option_keys
                }
            }
            
            if self.websocket:
                await self.websocket.send(json.dumps(payload).encode("utf-8"))
                logger.info(f"UNSUBSCRIBED {len(self.current_option_keys)} OLD OPTIONS")
                self.current_option_keys = []
            else:
                logger.error("Cannot unsubscribe from options - WebSocket not connected")
                
        except Exception as e:
            logger.error(f"Option unsubscription failed: {e}")

    # PATCH 3: SWITCH SYMBOL FUNCTION
    async def switch_symbol(self, symbol: str, expiry: str):
        """Switch subscription to new symbol and expiry"""
        if symbol == self.active_symbol and expiry == self.active_expiry:
            # SAFEGUARD: Ensure we have active subscriptions even if symbol matches
            if not self.subscribed_instruments:
                logger.info(f"SYMBOL SWITCH RESUBSCRIBING → No active instruments for {symbol} {expiry}")
                # Continue with subscription process
            else:
                logger.debug(f"SYMBOL SWITCH SKIPPED → Already subscribed to {symbol} {expiry}")
                return

        logger.info(f"Switching subscription → {symbol} {expiry}")

        # UPDATE GLOBAL CONTEXT
        MARKET_CONTEXT["symbol"] = symbol
        MARKET_CONTEXT["expiry"] = expiry

        await self.unsubscribe_options()
        
        # Prevent race condition between unsub and sub
        await asyncio.sleep(0.1)
        
        self._clear_option_cache()

        # Get index key for the symbol
        if symbol == "NIFTY":
            index_key = "NSE_INDEX|Nifty 50"
        elif symbol == "BANKNIFTY":
            index_key = "NSE_INDEX|Nifty Bank"
        elif symbol == "FINNIFTY":
            index_key = "NSE_INDEX|Nifty Fin Service"
        else:
            logger.error(f"Unsupported symbol: {symbol}")
            index_key = None

        # Get option instruments for the symbol and expiry
        option_keys = self._get_option_instruments(symbol, expiry)
        
        if option_keys is None:
            option_keys = []
        
        # Combine index and options
        instruments = []
        
        if index_key:
            instruments.append(index_key)
        else:
            logger.error(f"Index key missing for {symbol}")
        
        if option_keys:
            instruments.extend(option_keys)

        await self._subscribe(instruments)

        self.active_symbol = symbol
        self.active_expiry = expiry
        
        logger.info(f"SYMBOL SWITCH COMPLETE → {symbol} {expiry} ({len(instruments)} instruments)")

    def _get_index_key(self, symbol: str) -> Optional[str]:
        """Get index instrument key for symbol"""
        if symbol == "NIFTY":
            return "NSE_INDEX|Nifty 50"
        elif symbol == "BANKNIFTY":
            return "NSE_INDEX|Nifty Bank"
        else:
            logger.error(f"Unknown symbol for index key: {symbol}")
            return None

    def _get_option_instruments(self, symbol: str, expiry: str):
        try:
            options = self.instrument_registry.get_options(symbol, expiry)

            if not options:
                logger.error(f"No options found for {symbol}")
                return []

            spot = self.last_spot_price.get(symbol)

            if spot is None:
                logger.info("Index tick not received yet — delaying option generation")
                return []

            atm = int(spot // 50) * 50

            lower = atm - 500
            upper = atm + 500

            instrument_keys = []

            # registry returns {strike:{CE:key,PE:key}}
            if isinstance(options, dict):
                for strike_str, strikes in options.items():
                    try:
                        strike = int(strike_str)

                        if lower <= strike <= upper:
                            ce = strikes.get("CE")
                            pe = strikes.get("PE")

                            if isinstance(ce, str):
                                instrument_keys.append(ce)

                            if isinstance(pe, str):
                                instrument_keys.append(pe)

                    except Exception:
                        continue

            # Safety filter (very important)
            instrument_keys = [
                k for k in instrument_keys
                if isinstance(k, str)
            ]

            if len(instrument_keys) > 50:
                instrument_keys = instrument_keys[:50]

            logger.info(
                f"OPTION INSTRUMENTS GENERATED → {symbol} ATM={atm} count={len(instrument_keys)}"
            )

            return instrument_keys

        except Exception as e:
            logger.error(
                f"Failed to get option instruments for {symbol}: {e}"
            )

            return []

    # PATCH 4: UNSUBSCRIBE ALL FUNCTION
    async def _unsubscribe_all(self):
        """Unsubscribe from all currently subscribed instruments"""
        if not self.subscribed_instruments:
            return

        payload = {
            "method": "unsub",
            "data": {
                "instrumentKeys": list(self.subscribed_instruments)
            }
        }

        try:
            if self.websocket:
                await self.websocket.send(json.dumps(payload).encode("utf-8"))
                logger.info(f"UNSUBSCRIBED OLD INSTRUMENTS → {len(self.subscribed_instruments)} instruments")
            else:
                logger.warning("Cannot unsubscribe - WebSocket not connected")
        except Exception as e:
            logger.error(f"Unsubscribe failed: {e}")

        self.subscribed_instruments.clear()
        # P4: Clear subscription lock state
        self._subscription_lock = asyncio.Lock()

    # PATCH 5: OPTION CACHE CLEAR FUNCTION
    def _clear_option_cache(self):
        """Clear option chain cache"""
        try:
            from app.services.option_chain_builder import option_chain_builder
            option_chain_builder.chains.clear()
            logger.info("OPTION CHAIN CACHE CLEARED")
        except Exception as e:
            logger.error(f"Failed to clear option cache: {e}")

    async def _subscribe(self, instruments: List[str]):
        """Subscribe to list of instruments"""
        if not instruments:
            logger.warning("No instruments to subscribe")
            return

        payload = {
            "guid": "strikeiq-feed",
            "method": "sub",
            "data": {
                "mode": "full",
                "instrumentKeys": instruments
            }
        }

        try:
            new_instruments = [
                key for key in instruments
                if key not in self.subscribed_instruments
            ]

            if not new_instruments:
                logger.debug("Skipping duplicate subscription")
                return

            instruments = new_instruments
                
            if self.websocket:
                payload_bytes = json.dumps(payload).encode("utf-8")
                self._subscription_payload = payload
                await self.websocket.send(payload_bytes)
                logger.info(f"SUBSCRIBED → {len(instruments)} instruments")
                # P4: Update subscribed_instruments with thread safety
                async with self._subscription_lock:
                    self.subscribed_instruments.update(instruments)
                diag("FEED", f"Subscribed instruments count: {len(self.subscribed_instruments)}")
            else:
                logger.warning("WS not ready - delaying subscription")
                
                # retry after websocket stabilizes
                self._option_sub_task = asyncio.create_task(
                    self._delayed_subscribe(instruments)
                )
                return
        except Exception as e:
            logger.error(f"Subscribe failed: {e}")

    async def _delayed_subscribe(self, instruments):
        """Retry subscription after WebSocket stabilizes"""
        await asyncio.sleep(2)
        
        if not self.websocket:
            logger.error("Delayed subscribe failed - WS still not connected")
            return
            
        # Retry subscription with same payload
        payload = {
            "guid": "strikeiq-feed",
            "method": "sub",
            "data": {
                "mode": "full",
                "instrumentKeys": instruments
            }
        }
        
        try:
            await self.websocket.send(json.dumps(payload).encode("utf-8"))
            logger.info(f"SUBSCRIBED → {len(instruments)} instruments (delayed)")
            # P4: Update subscribed_instruments with thread safety
            async with self._subscription_lock:
                self.subscribed_instruments.update(instruments)
        except Exception as e:
            logger.error(f"Delayed subscribe failed: {e}")

    async def maintain_connection(self):
        """Maintain WebSocket connection with reconnect loop"""
        while self.running:
            if not self.is_connected and not self._reconnecting:
                logger.debug("WS connection missing → reconnecting")
                try:
                    await self.ensure_connection()
                except Exception as e:
                    logger.error(f"Reconnect failed: {e}")
            await asyncio.sleep(10)  # 10-second maintenance interval

    async def _heartbeat(self):

        while self.running:

            try:

                if self.websocket and self.is_connected:
                    await self.websocket.ping()
                    # Heartbeat broadcast disabled - only send WebSocket ping
                    # Do not send heartbeat messages to frontend

            except Exception:
                logger.warning("Heartbeat failed")

            await asyncio.sleep(10)

    async def _handle_message(self, raw: bytes) -> None:
        """
        Decode raw Upstox Protobuf frame → push valid ticks into self._message_queue.

        Pipeline:
            _recv_loop → _handle_message → _message_queue → _process_loop → message_router
        """
        try:
            logger.debug("DEBUG PARSER INPUT SIZE → %d", len(raw))
            res = await decode_protobuf_message(raw)
            if res is not None:
                self.feeds_received_count += 1
                ticks = res
            else:
                ticks = []

            if not ticks:
                return

            now = time.time()
            for tick in ticks:
                tick["_ingest_time"] = now
                try:
                    self._message_queue.put_nowait(tick)
                    self.tick_counter += 1
                except asyncio.QueueFull:
                    self.dropped_ticks += 1
                    now2 = time.time()
                    if now2 - self.last_queue_warning > 5:
                        logger.warning(
                            "QUEUE FULL — dropping tick. dropped_total=%d queue_size=%d",
                            self.dropped_ticks,
                            self._message_queue.qsize(),
                        )
                        self.last_queue_warning = now2
                        # P5: Apply backpressure - pause briefly when queue is full
                        await asyncio.sleep(0.001)

        except Exception as e:
            logger.error("_handle_message error: %s", e, exc_info=True)

    async def _recv_loop(self):
        try:
            while self.running:

                try:

                    if not self.websocket:
                        await asyncio.sleep(1)
                        continue

                    raw = await self.websocket.recv()
                    logger.debug("DEBUG RAW FRAME SIZE → %d", len(raw) if raw else 0)
                    if isinstance(raw, (bytes, bytearray)):
                        logger.info("DEBUG FRAME TYPE → binary")

                    if getattr(self, "_debug_ws", False):
                        logger.debug(f"WS FRAME SIZE = {len(raw) if raw else 0}")

                    if not raw:
                        continue

                    await self._handle_message(raw)

                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    logger.warning(f"WebSocket recv error: {e} — triggering disconnect handler")
                    # P1: only spawn one disconnect handler at a time
                    if not self._disconnect_task or self._disconnect_task.done():
                        self._disconnect_task = asyncio.create_task(self._handle_disconnect())
                    return  # Exit this recv loop; _handle_disconnect will restart tasks

        except asyncio.CancelledError:
            logger.info("WebSocket receive loop stopped")
            raise

    async def _process_loop(self):
        """Process queued binary messages: decode protobuf → route ticks → broadcast."""

        logger.debug("PROCESS LOOP STARTED")

        while self.running:

            try:

                tick = await self._message_queue.get()
                logger.debug("PROCESSING TICK FROM QUEUE")
                
                # Calculate processing latency
                ingest_time = tick.get("_ingest_time")
                
                if ingest_time:
                    latency = time.time() - ingest_time
                    
                    if latency > 0.05:
                        logger.warning(f"Tick processing delay {latency:.3f}s")
                    
                    self.max_tick_latency = max(self.max_tick_latency, latency)
                
                instrument = tick.get("instrument_key")
                
                # Add diagnostic logging for tick flow (only in debug mode)
                if TICK_DEBUG:
                    diag("FEED", f"Tick received for {instrument}")
                    diag("UPSTOX_TICK", f"Tick received {instrument}")
                
                # Add tick counter
                increment_counter("ticks_received")
                self.tick_counter += 1
                if self.tick_counter % 100 == 0:
                    diag("UPSTOX_TICK", f"Processed {self.tick_counter} ticks")
                
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug("PROCESSING → %s", instrument)
                
                if not instrument:
                    continue  # Skip malformed ticks
                # Route tick to appropriate processor
                message = message_router.route_tick(tick)
                if logger.isEnabledFor(logging.DEBUG):
                    if message:
                        logger.debug("ROUTED MESSAGE → %s", message.get("type"))
                    else:
                        logger.debug("ROUTED MESSAGE → None")
                
                if message:
                    # Handle different message types - AUDIT METRICS - STEP 4: Message Router Latency
                    start = time.time()
                    await self._handle_routed_message(message)
                    elapsed = time.time() - start
                    
                    # Track router latency metrics
                    self.max_router_latency = max(self.max_router_latency, elapsed)
                    
                    if elapsed > 0.01:
                        self.slow_router_count += 1
                        loop_now = time.time()

                        if loop_now - getattr(self, "last_router_warning", 0) > 5:
                            logger.warning(f"SLOW ROUTE HANDLER {elapsed:.4f}s")
                            self.last_router_warning = loop_now
                
                self.processed_ticks += 1
                self.processed_ticks_10s += 1
                
                # STEP 2: QUEUE WORKER TRACE - DEBUG ONLY
                if TICK_DEBUG:
                    logger.debug("ANALYTICS QUEUE WORKER ACTIVE")

            except Exception as e:

                logger.error(f"Process error: {e}")

    async def _metrics_loop(self):
        """Log system metrics every 30 seconds"""
        try:
            while self.running:
                await asyncio.sleep(30)
                metrics = {
                    "queue_size": self._message_queue.qsize(),
                    "dropped_ticks": self.dropped_ticks,
                    "processed_ticks": self.processed_ticks,
                    "max_tick_latency": self.max_tick_latency
                }
                if metrics["processed_ticks"] > 0:
                    logger.info(f"SYSTEM METRICS {metrics}")
                
                # Calculate avg queue size using running total (no sum() operation)
                if self.queue_size_samples:
                    self.avg_queue_size = (
                        self.queue_size_total / len(self.queue_size_samples)
                    )
                
                # AUDIT METRICS - STEP 6: Option Subscription Storm Detection
                await self._check_subscription_storm()
        except asyncio.CancelledError:
            logger.info("Metrics loop cancelled")

    async def _check_subscription_storm(self):
        """AUDIT METRICS - STEP 6: Check for option subscription storms"""
        now = time.time()
        
        if now - self.last_subscription_report >= 30:
            subscriptions_last_30s = self.subscription_counter
            
            logger.info(f"SUBSCRIPTIONS_LAST_30S: {subscriptions_last_30s}")
            
            if subscriptions_last_30s > 20:
                logger.warning(f"SUBSCRIPTION_STORM_WARNING: {subscriptions_last_30s} subscriptions in last 30s (>20 threshold)")
            
            # Reset counters for next interval
            self.subscription_counter = 0
            self.last_subscription_report = now

    async def _monitor_redis_call(self, operation_name: str, operation_func):
        """AUDIT METRICS - STEP 7: Monitor Redis call latency"""
        start = time.time()
        try:
            result = await operation_func()
            elapsed = time.time() - start
            
            # Track Redis latency metrics
            self.max_redis_latency = max(self.max_redis_latency, elapsed)
            
            if elapsed > 0.01:
                logger.warning(f"REDIS_SLOW: {operation_name} took {elapsed:.4f}s")
                self.slow_redis_count += 1
            
            return result
        except Exception as e:
            elapsed = time.time() - start
            logger.error(f"REDIS_ERROR: {operation_name} failed after {elapsed:.4f}s: {e}")
            raise

    async def _monitor_token_manager_redis(self):
        """AUDIT METRICS - STEP 7: Monitor token manager Redis calls"""
        try:
            # Monitor token retrieval from Redis
            await self._monitor_redis_call(
                "token_manager_get_token", 
                lambda: token_manager.get_token()
            )
        except Exception as e:
            logger.debug(f"Token manager Redis monitoring failed: {e}")

    async def _monitor_broadcast(self, name, fn, *args):
        """AUDIT METRICS - STEP 8: Monitor WebSocket broadcast latency"""
        start = time.time()
        try:
            await fn(*args)
        finally:
            now = time.time()
            elapsed = now - start
            
            if elapsed > 0.01:
                self.slow_broadcast_count += 1
                if now - getattr(self, "last_broadcast_warning", 0) > 5:
                    logger.warning(f"BROADCAST_SLOW {name} {elapsed:.4f}s")
                    self.last_broadcast_warning = now
            
            self.max_broadcast_latency = max(self.max_broadcast_latency, elapsed)

    async def _throughput_logger(self):
        """AUDIT METRICS - STEP 2: Log tick pipeline throughput every 10 seconds"""
        while self.running:
            try:
                await asyncio.sleep(10)
                
                # Calculate ticks per second for the last 10 seconds
                ticks_per_sec = self.processed_ticks_10s / 10
                logger.info(f"TICK PIPELINE RATE {ticks_per_sec:.1f}/sec")
                
                # Reset counter for next interval
                self.processed_ticks_10s = 0
                self.last_throughput_log = time.time()
                
            except Exception as e:
                logger.error(f"Throughput logger error: {e}")

    async def _profile_logger(self):
        """Profile CPU hotspots after 30 seconds"""
        try:
            await asyncio.sleep(30)
            self.profiler.disable()
            logger.info("CPU PROFILING RESULTS:")
            self.profiler.print_stats(sort="cumtime")
        except Exception as e:
            logger.error(f"Profile logger error: {e}")

    async def _handle_routed_message(self, message):
        """Handle routed messages and update appropriate components"""
        try:
            message_type = message.get("type")
            symbol = message.get("symbol")
            
            logger.info(f"PIPELINE → tick received {message_type} {symbol}")
            
            if TICK_DEBUG:
                logger.debug(f"ROUTED MESSAGE → {message_type} for {symbol}")
            
            if message_type == "index_tick":
                instrument_key = message.get("instrument_key")
                if TICK_DEBUG:
                    logger.info(f"PIPELINE CHECK → index_tick received for {instrument_key}")
                
                # Update option chain builder with new spot price
                data = message.get("data", {})
                ltp = data.get("ltp")
                
                if ltp is not None:
                    if TICK_DEBUG:
                        logger.info(f"PIPELINE CHECK → Spot price extracted {ltp}")
                    
                    logger.info(f"PIPELINE → forwarded tick to option_chain_builder {symbol}")
                    
                    option_chain_builder.update_index_price(
                        symbol,
                        float(ltp)
                    )
                    
                    try:
                        from app.services.candle_builder import candle_builder
                        vol = data.get("volume", 0.0)
                        ts = data.get("timestamp", time.time())
                        candle_builder.push_tick(symbol, float(ltp), float(vol), ts)
                    except Exception as e:
                        logger.debug(f"Candle builder tick failed {e}")
                    
                    logger.info(f"PIPELINE → chain updated {symbol}")
                    
                    # Store last spot price for ATM calculation
                    self.last_spot_price[symbol] = ltp
                    
                    # PATCH 6: Safe ATM shift detector
                    new_atm = int(ltp // 50) * 50
                    
                    if self.current_atm is None:
                        self.current_atm = new_atm
                    elif abs(new_atm - self.current_atm) >= 200 and new_atm != self.current_atm:
                        now = time.time()
                        
                        if now - self.last_subscription_time < 5:
                            return
                        
                        logger.info(f"ATM SHIFT DETECTED → {self.current_atm} → {new_atm}")
                        self.current_atm = new_atm
                        
                        await self.switch_symbol(self.active_symbol, self.active_expiry)
                    
                    # Update tracked index price for ATM calculation and filtering
                    if symbol in ["NIFTY", "BANKNIFTY"]:
                        self.last_index_prices[symbol] = ltp
                    
                    # Detect ATM and subscribe to options
                    if symbol in ["NIFTY", "BANKNIFTY"]:
                        logger.info("DEBUG ATM CALCULATION INPUT SPOT → %s", ltp)
                        step = 50 if symbol == "NIFTY" else 100
                        atm = get_atm_strike(ltp, step=step)
                        if time.time() - self.last_subscription_time > 2:
                            # P3: Cancel existing option subscription task before creating new one
                            if self._option_sub_task and not self._option_sub_task.done():
                                self._option_sub_task.cancel()
                                try:
                                    await self._option_sub_task
                                except asyncio.CancelledError:
                                    pass
                            
                            loop = asyncio.get_running_loop()
                            self._option_sub_task = loop.create_task(
                                self._check_and_subscribe_options(symbol, atm)
                            )
                    
                    # Broadcast index tick using router message directly (no payload reconstruction)
                    logger.info(f"INDEX BROADCAST → {message}")
                    
                    await self._monitor_broadcast(
                        "index_tick",
                        manager.broadcast,
                        message
                    )
                else:
                    return  # Skip malformed ticks
                
            elif message_type == "option_tick":
                # Update option chain builder with option data
                data = message.get("data", {})
                strike = data.get("strike")
                right = data.get("right")
                ltp = data.get("ltp")
                
                # CRITICAL DEBUG: Log raw Upstox payload
                logger.info(f"RAW TICK PAYLOAD → {data}")
                
                if not strike or not right:
                    return  # Skip malformed ticks (LTP is optional for OI updates)
                
                # CRITICAL FIX: Parse OI from multiple possible field names
                oi = (
                    data.get("oi")
                    or data.get("open_interest")
                    or data.get("oi_day_high")
                    or data.get("oi_day_low")
                    or 0
                )
                volume = data.get("volume", 0)
                
                # CRITICAL DEBUG: Log raw option data
                logger.info(
                    f"OPTION RAW DATA → strike={strike} right={right} "
                    f"ltp={ltp} oi={oi}"
                )
                
                logger.info(f"PIPELINE → forwarded tick to option_chain_builder {symbol}")

                # AUDIT METRICS - STEP 3: Option Chain Builder CPU Time
                start = time.time()

                option_chain_builder.update_option_tick(
                    symbol,
                    strike,
                    right,
                    ltp,
                    oi,
                    volume
                )
                elapsed = time.time() - start
                
                if elapsed > 0.02:
                    self.slow_option_builder_count += 1
                    loop_now = time.time()

                    if loop_now - getattr(self, "last_option_warning", 0) > 5:
                        logger.warning(f"OPTION_BUILDER_SLOW {elapsed:.4f}s")
                        self.last_option_warning = loop_now
                
                self.max_option_builder_time = max(self.max_option_builder_time, elapsed)
                
                # Option ticks are included in chain snapshots, no individual broadcast
                
            else:
                logger.warning(f"Unknown message type: {message_type}")
                
        except Exception as e:
            logger.error(f"Error handling routed message: {e}")

    async def _handle_disconnect(self):
        """Handle WebSocket disconnect with automatic reconnect and resubscribe (STEP 8)"""
        logger.warning("🔌 WebSocket disconnected - attempting reconnect")
        self.is_connected = False
        self._reconnecting = False

        try:
            if self.websocket:
                await self.websocket.close()
        except Exception:
            pass

        await self._cancel_tasks()
        
        # Wait before reconnecting
        await asyncio.sleep(5)
        
        # Attempt to reconnect and resubscribe
        if self.running:
            try:
                logger.info("🔄 Attempting to reconnect...")
                success = await self.ensure_connection()
                if success:
                    logger.info("✅ Reconnected successfully")
                else:
                    logger.error("❌ Reconnection failed")
            except Exception as e:
                logger.error(f"Reconnection error: {e}")

    async def disconnect(self):

        self.running = False
        self.is_connected = False

        # Stop new components
        await option_chain_builder.stop()
        await oi_heatmap_engine.stop()
        await analytics_broadcaster.stop()

        await self._cancel_tasks()

        try:
            if self.websocket:
                await self.websocket.close()
        except Exception:
            pass

        await self._client.aclose()

    async def _failsafe_no_data_check(self):
        """
        STEP7: FAILSAFE - Log warning after 10 seconds
        """
        logger.info("⏱️ STARTING 10-SECOND FAILSAFE TIMER...")
        await asyncio.sleep(10)
        
        # P3: Track and cancel failsafe task on cleanup
        self._failsafe_task = None
        
        # Only resubscribe if no feeds were received at all
        if self.feeds_received_count == 0:
            logger.warning("NO FEEDS RECEIVED — RESUBSCRIBING")
            
            if self.websocket and hasattr(self, '_subscription_payload'):
                logger.info("SUBSCRIPTION PAYLOAD → %s", json.dumps(self._subscription_payload, indent=2))
                payload_bytes = json.dumps(self._subscription_payload).encode("utf-8")
                await self.websocket.send(payload_bytes)
                logger.info("SUBSCRIPTION SENT SUCCESSFULLY")
            return

        if self.feeds_received_count > 0:
            logger.info("Market feed active — waiting for LTPC values")
            return

    async def _route_tick_to_builders(self, symbol, instrument_key, tick_data):

        active_keys = [
            key for key in manager.active_connections
            if key.startswith(f"{symbol}:")
        ]

        for key in active_keys:

            try:

                _, expiry_str = key.split(":")

                expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d").date()

                builder = await chain_manager.get_builder(symbol, expiry_date)

                if builder:
                    # P2: Create task with proper cleanup
                    task = asyncio.create_task(
                        builder.handle_tick(symbol, instrument_key, tick_data)
                    )
                    # Add cleanup callback to prevent task leaks
                    task.add_done_callback(
                        lambda t: logger.error(f"Task failed: {t.exception()}") if t.exception() and not t.cancelled() else None
                    )

            except Exception as e:

                logger.error(f"Tick routing failed for {key}: {e}")

    async def broadcast_ticks(self, ticks):
        """Broadcast ticks to frontend"""
        for tick in ticks:
            # STEP 7: PERFORMANCE TRACE - DEBUG ONLY
            if TICK_DEBUG:
                start = time.time()
            
            logger.debug("BROADCASTING TICK TO FRONTEND")
            # AUDIT METRICS - STEP 8: WebSocket Broadcast Latency
            await self._monitor_broadcast("tick_broadcast", manager.broadcast, tick)
            
            # STEP 7: PROCESSING LATENCY - DEBUG ONLY
            if TICK_DEBUG:
                logger.debug(f"PROCESSING LATENCY = {time.time() - start}")


class WebSocketFeedManager:

    def __init__(self):

        self.feed: Optional[WebSocketMarketFeed] = None
        self._lock = asyncio.Lock()

        self.market_states = {}

    @property
    def is_connected(self) -> bool:
        return self.feed is not None and self.feed.is_connected

    async def start_feed(self):

        async with self._lock:

            if self.feed and self.feed.running:
                return self.feed

            self.feed = WebSocketMarketFeed()

            await self.feed.start()

            return self.feed

    async def get_feed(self):

        async with self._lock:

            if self.feed and self.feed.running:
                return self.feed

            return None

    async def cleanup_all(self):

        async with self._lock:

            if self.feed:
                await self.feed.disconnect()
                self.feed = None


ws_feed_manager = WebSocketFeedManager()


# Helper functions for option subscription
def get_atm_strike(price: float, step: int = 50) -> int:
    """Calculate ATM strike rounded to nearest step"""
    return int(round(price / step) * step)


def build_option_keys(symbol: str, atm: int, expiry: str):

    keys = []

    try:

        registry = get_instrument_registry()

        options = registry.get_options(symbol, expiry)

        logger.info(f"TOTAL OPTIONS FROM REGISTRY → {len(options)}")

        # registry returns dict: {strike:{CE:key,PE:key}}
        if isinstance(options, dict):

            for strike_str, strikes in options.items():

                try:

                    strike = int(strike_str)

                    if atm - 600 <= strike <= atm + 600:

                        ce = strikes.get("CE")
                        pe = strikes.get("PE")

                        if ce:
                            keys.append(ce)

                        if pe:
                            keys.append(pe)

                except Exception as e:
                    logger.debug(f"OPTION PARSE ERROR → {e}")
                    continue

        logger.info(f"OPTION KEYS GENERATED → {len(keys)}")

    except Exception as e:

        logger.error(f"OPTION KEY BUILD FAILED: {e}")

    return keys


async def start_market_feed():
    """Start the global market feed singleton. Safe to call multiple times."""
    global market_feed_instance
    
    if market_feed_instance and market_feed_instance.running:
        logger.info("Market feed already running — skipping duplicate start")
        return
    
    market_feed_instance = WebSocketMarketFeed()
    await market_feed_instance.start()


async def stop_market_feed():
    """Stop the global market feed singleton."""
    global market_feed_instance
    
    if market_feed_instance:
        try:
            await market_feed_instance.disconnect()
        except Exception as e:
            logger.error(f"stop_market_feed error: {e}")
        finally:
            market_feed_instance = None


def get_live_structural_engine():
    """Access the AI engine from the global market feed instance."""
    if market_feed_instance:
        return market_feed_instance.ai_engine
    return None