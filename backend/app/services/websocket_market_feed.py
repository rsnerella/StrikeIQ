import asyncio
import json
import logging
import time
import os
from typing import Optional
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
from app.services.live_chain_manager import chain_manager
from app.core.ws_manager import manager
from app.services.instrument_registry import get_instrument_registry
from app.services.live_structural_engine import LiveStructuralEngine
from app.core.live_market_state import get_market_state_manager
from app.core.logging_config import TICK_DEBUG

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

        self._client = httpx.AsyncClient(timeout=30)
        
        # Option subscription tracking
        self.current_atm = None
        self.current_expiry = None
        self.current_option_keys = []
        self.subscribed_instruments = set()
        self.dropped_ticks = 0
        self.last_subscription_time = 0
        self.processed_ticks = 0
        self.last_queue_warning = 0
        self.max_tick_latency = 0
        self.tick_counter = 0
        self.last_atm = None
        self.instrument_registry = None
        
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
            getattr(self, "_throughput_task", None)
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
        ws_url = data.get("data", {}).get("authorizedRedirectUri")
        
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

    async def connect(self):
        """Public connection method - deprecated, use ensure_connection"""
        token = await token_manager.get_valid_token()
        await self._connect(token)
    
    async def ensure_connection(self):
        """
        Ensure websocket connection exists.
        Used by main startup.
        """

        try:

            if self.is_connected:
                return True

            token = await token_manager.get_valid_token()

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
        TASK 4: SUBSCRIBE TO NIFTY/BANKNIFTY INDICES USING REGISTRY ONLY
        """

        try:

            instrument_registry = get_instrument_registry()
            await instrument_registry.wait_until_ready()
            
            # Store instrument registry for expiry detection
            self.instrument_registry = instrument_registry
            
            # Debug logging for registry structure
            logger.info(f"Registry attributes → {dir(self.instrument_registry)}")
            
            # Detect NIFTY expiry if not already set
            if not self.current_expiry:
                self.current_expiry = self.get_nearest_nifty_expiry()
                logger.info(f"DETECTED NIFTY EXPIRY → {self.current_expiry}")

            # ------------------------------------------------
            # TASK 4: GET INSTRUMENT KEYS FROM REGISTRY (OPTIONS/FUTURES) + INDEX KEYS
            # ------------------------------------------------
            
            # Use registry to get correct instrument keys
            instrument_keys = []
            
            # TASK 4: ADD INDEX INSTRUMENTS DIRECTLY (NOT IN REGISTRY)
            # Index instruments are not in the options/futures registry
            index_instruments = [
                "NSE_INDEX|Nifty 50",
                "NSE_INDEX|Nifty Bank"
            ]
            
            for index_key in index_instruments:
                instrument_keys.append(index_key)
                logger.info(f"INDEX INSTRUMENT: {index_key}")
            
            # TASK 4: ADD DEFENSIVE CHECK
            if not instrument_keys:
                logger.error("NO INSTRUMENT KEYS FOUND")
                raise Exception("Instrument registry returned zero keys")
            
            logger.info("=== INSTRUMENT KEYS FOR SUBSCRIPTION ===")
            for k in instrument_keys:
                logger.info(k)

            # ------------------------------------------------
            # TASK 5: SUBSCRIPTION PAYLOAD WITH CORRECT MODES
            # ------------------------------------------------

            # INDEX instruments use "ltpc" mode
            index_payload = {
                "guid": "strikeiq-feed",
                "method": "sub",
                "data": {
                    "mode": "ltpc",
                    "instrumentKeys": instrument_keys
                }
            }
            
            # Store payload for failsafe retry
            self._subscription_payload = index_payload

            logger.info("=== INDEX SUBSCRIPTION PAYLOAD ===")
            logger.info(json.dumps(index_payload, indent=2))
            logger.info(f"INDEX INSTRUMENT COUNT: {len(instrument_keys)}")

            if self.websocket is None:
                logger.error("WebSocket not initialized")
                return

            # TASK 5: CRITICAL - ADD 1-SECOND DELAY BEFORE SUBSCRIPTION
            logger.info("⏳ WAITING 1 SECOND BEFORE SUBSCRIPTION...")
            await asyncio.sleep(1)
            
            if self.websocket:
                await self.websocket.send(json.dumps(index_payload).encode("utf-8"))
                logger.info("SUBSCRIPTION SENT — WAITING FOR DATA")

            # Confirm subscription sent
            logger.info("✅ SUBSCRIPTION SENT - WAITING FOR MARKET DATA")
            
            # TASK 6: START FAILSAFE TIMER FOR NO DATA DETECTION
            asyncio.create_task(self._failsafe_no_data_check())

        except Exception as e:

            logger.error(f"Subscription failed: {e}")

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
            
            # Filter out already subscribed instruments
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
                await self.websocket.send(json.dumps(payload))
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

    def get_nearest_nifty_expiry(self):
        """Get the nearest NIFTY expiry from instrument registry"""
        if not self.instrument_registry:
            logger.error("Instrument registry not loaded")
            return None

        expiries = []
        logger.info("SCANNING REGISTRY FOR NIFTY EXPIRIES")

        # Use registry methods instead of direct data access
        expiries = self.instrument_registry.get_expiries("NIFTY")

        valid_expiries = []

        for expiry in expiries:
            parsed = self.parse_expiry(expiry)
            
            if parsed:
                valid_expiries.append((parsed, expiry))

        if not valid_expiries:
            logger.error("No valid NIFTY expiries detected")
            return None

        nearest_expiry, nearest_expiry_str = min(valid_expiries, key=lambda x: x[0])

        logger.info(f"AVAILABLE EXPIRIES → {expiries}")
        logger.info(f"DETECTED NIFTY EXPIRY → {nearest_expiry_str}")

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
                await self.websocket.send(json.dumps(payload))
                logger.info(f"UNSUBSCRIBED {len(self.current_option_keys)} OLD OPTIONS")
                self.current_option_keys = []
            else:
                logger.error("Cannot unsubscribe from options - WebSocket not connected")
                
        except Exception as e:
            logger.error(f"Option unsubscription failed: {e}")

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

    async def _recv_loop(self):

        while self.running:

            try:

                if not self.websocket:
                    await asyncio.sleep(1)
                    continue

                raw = await self.websocket.recv()
                
                if getattr(self, "_debug_ws", True):
                    logger.info("WS FRAME RECEIVED")
                    try:
                        logger.info(f"WS FRAME SIZE = {len(raw)}")
                    except Exception:
                        logger.info("WS FRAME SIZE UNKNOWN")
                logger.info(f"WS FRAME TYPE = {type(raw)}")

                if not raw:
                    continue

                # STEP 1: PACKET SIZE LOGGING - DEBUG ONLY
                packet_size = len(raw)
                if TICK_DEBUG and logger.isEnabledFor(logging.DEBUG):
                    logger.debug("PACKET SIZE = %d", packet_size)
                
                # STEP 1: PROTOBUF DECODING LOGS - DEBUG ONLY
                if TICK_DEBUG:
                    logger.debug("STARTING PROTOBUF DECODE")
                
                # STEP 1: Detect JSON control frames
                if isinstance(raw, str):
                    logger.info(f"WS CONTROL MESSAGE: {raw}")
                    try:
                        import json
                        msg = json.loads(raw)

                        if "type" in msg:
                            logger.info(f"WS CONTROL TYPE: {msg['type']}")

                        if "data" in msg:
                            logger.info(f"CONTROL DATA: {msg['data']}")

                    except Exception as e:
                        logger.warning(f"CONTROL MESSAGE PARSE ERROR: {e}")

                    continue

                # STEP 3: Binary frame handling
                if not isinstance(raw, (bytes, bytearray)):
                    logger.warning(f"UNKNOWN FRAME TYPE: {type(raw)}")
                    continue

                # STEP 3: CRITICAL - RAW MESSAGE DEBUGGING BEFORE PARSING
                logger.debug(f"=== RAW MESSAGE DEBUG ===")
                logger.debug(f"RAW MESSAGE TYPE: {type(raw)}")
                logger.debug(f"RAW PACKET SIZE: {len(raw)}")
                
                # Log first 50 bytes for structure analysis
                if len(raw) > 0:
                    sample_bytes = raw[:50]
                    logger.debug(f"FIRST 50 BYTES: {sample_bytes.hex()}")
                
                if getattr(self, "_debug_ws", True):
                    logger.info("STARTING PROTOBUF DECODE")
                # STEP 4: DECODE PROTOBUF
                ticks = await decode_protobuf_message(raw)
                if getattr(self, "_debug_ws", True):
                    logger.info("PROTOBUF DECODE COMPLETE")
                if TICK_DEBUG and logger.isEnabledFor(logging.DEBUG):
                    logger.debug("PARSER OUTPUT → %d ticks", len(ticks))
                if TICK_DEBUG and logger.isEnabledFor(logging.DEBUG):
                    logger.debug("TICKS PARSED = %d", len(ticks))
                
                # Update throughput counter
                self.tick_counter += len(ticks)
                
                if not ticks:
                    if TICK_DEBUG:
                        logger.warning("NO TICKS IN MESSAGE")
                    
                if ticks:
                    # STEP 2: TICK PIPELINE TRACE - DEBUG ONLY
                    if TICK_DEBUG:
                        logger.debug("PUSHING TICKS INTO ANALYTICS QUEUE")
                        
                    self._debug_tick_counter = getattr(self, "_debug_tick_counter", 0)
                    queue_put = self._message_queue.put_nowait
                    now = time.time()
                    
                    for tick in ticks:
                        tick["_ingest_time"] = now
                        try:
                            self._debug_tick_counter += 1
                            if self._debug_tick_counter % 500 == 0:
                                logger.info(f"TICK PIPELINE ACTIVE count={self._debug_tick_counter}")
                            queue_put(tick)
                        except asyncio.QueueFull:
                            self.dropped_ticks += 1
                            if self.dropped_ticks % 100 == 0:
                                logger.warning(f"Dropped ticks count: {self.dropped_ticks}")
                    
                queue_size = self._message_queue.qsize()
                
                # AUDIT METRICS - STEP 1: Queue Consumer Lag Detection
                self.max_queue_size = max(self.max_queue_size, queue_size)
                
                # Bounded buffer to prevent memory growth with running total
                self.queue_size_samples.append(queue_size)
                self.queue_size_total += queue_size
                
                if len(self.queue_size_samples) > 100:
                    removed = self.queue_size_samples.pop(0)
                    self.queue_size_total -= removed
                
                queue_limit = int(self._message_queue.maxsize * 0.8)
                
                if queue_size > queue_limit and now - self.last_queue_lag_warning > 10:
                    logger.warning(f"QUEUE_LAG_WARNING: Queue size {queue_size}/{self._message_queue.maxsize} ({queue_size/self._message_queue.maxsize*100:.1f}%)")
                    logger.warning(f"  Max observed: {self.max_queue_size}, Avg: {self.avg_queue_size:.1f}")
                    self.last_queue_lag_warning = now
                    
                    # AUDIT METRICS - STEP 1: Queue Consumer Lag Detection
                    self.max_queue_size = max(self.max_queue_size, queue_size)
                    
                    # Bounded buffer to prevent memory growth with running total
                    self.queue_size_samples.append(queue_size)
                    self.queue_size_total += queue_size
                    
                    if len(self.queue_size_samples) > 100:
                        removed = self.queue_size_samples.pop(0)
                        self.queue_size_total -= removed
                    
                    queue_limit = int(self._message_queue.maxsize * 0.8)
                    
                    if queue_size > queue_limit and now - self.last_queue_lag_warning > 10:
                        logger.warning(f"QUEUE_LAG_WARNING: Queue size {queue_size}/{self._message_queue.maxsize} ({queue_size/self._message_queue.maxsize*100:.1f}%)")
                        logger.warning(f"  Max observed: {self.max_queue_size}, Avg: {self.avg_queue_size:.1f}")
                        self.last_queue_lag_warning = now

            except Exception as e:

                logger.error(f"WebSocket recv error: {e}")

                await self._handle_disconnect()

                break

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
                
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug("PROCESSING → %s", instrument)
                
                if not instrument:
                    continue  # Skip malformed ticks
                # Route tick to appropriate processor
                message = message_router.route_tick(tick)
                
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
            
            if message_type == "index_tick":
                # Update option chain builder with new spot price
                data = message.get("data", {})
                ltp = data.get("ltp")
                
                if not ltp:
                    return  # Skip malformed ticks
                
                # AUDIT METRICS - STEP 3: Option Chain Builder CPU Time
                start = time.time()
                option_chain_builder.update_index_price(symbol, ltp)
                elapsed = time.time() - start
                
                if elapsed > 0.02:
                    self.slow_option_builder_count += 1
                    loop_now = time.time()

                    if loop_now - getattr(self, "last_option_warning", 0) > 5:
                        logger.warning(f"OPTION_BUILDER_SLOW {elapsed:.4f}s")
                        self.last_option_warning = loop_now
                
                self.max_option_builder_time = max(self.max_option_builder_time, elapsed)
                
                # Detect ATM and subscribe to options for NIFTY
                if symbol == "NIFTY":
                    atm = get_atm_strike(ltp)
                    
                    if atm != self.current_atm:
                        # Rate limiter: prevent subscription spam, but allow ATM changes
                        if time.time() - self.last_subscription_time < 2 and atm == self.last_atm:
                            return
                        
                        self.current_atm = atm
                        
                        option_keys = build_option_keys(
                            symbol="NIFTY",
                            atm=atm,
                            expiry=self.current_expiry
                        )
                        
                        # Limit subscription to prevent overload
                        if len(option_keys) > 60:
                            option_keys = option_keys[:60]
                        
                        logger.debug(f"SUBSCRIBING OPTIONS AROUND ATM {atm}")
                        logger.debug(f"EXPIRY → {self.current_expiry}")
                        logger.debug(f"TOTAL OPTIONS → {len(option_keys)}")
                        
                        payload = {
                            "guid": "strikeiq-options",
                            "method": "sub",
                            "data": {
                                "mode": "full",
                                "instrumentKeys": option_keys
                            }
                        }
                        
                        if self.websocket:
                            await self.websocket.send(json.dumps(payload).encode("utf-8"))
                            logger.info(f"OPTIONS SUBSCRIPTION SENT → {len(option_keys)} instruments")
                        self.last_subscription_time = time.time()
                        self.last_atm = atm
                        logger.debug(f"OPTIONS SUBSCRIBED → {len(option_keys)} instruments")
                
                # Broadcast index tick immediately - AUDIT METRICS - STEP 8: WebSocket Broadcast Latency
                await self._monitor_broadcast("index_tick", manager.broadcast, message)
                
            elif message_type == "option_tick":
                # Update option chain builder with option data
                data = message.get("data", {})
                strike = data.get("strike")
                right = data.get("right")
                ltp = data.get("ltp")
                
                if not all([strike, right, ltp]):
                    return  # Skip malformed ticks
                
                # AUDIT METRICS - STEP 3: Option Chain Builder CPU Time
                start = time.time()
                option_chain_builder.update_option_tick(symbol, strike, right, ltp)
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
        
        logger.warning("NO MARKET DATA RECEIVED — RESUBSCRIBING")
        
        if self.websocket and hasattr(self, '_subscription_payload'):
            await self.websocket.send(json.dumps(self._subscription_payload))
        
        logger.warning("⚠️ FAILSAFE TIMER EXPIRED")
        logger.warning("   Check instrument keys and subscription mode")
        logger.warning("   Verify Upstox V3 WebSocket feed is active")

    async def _route_tick_to_builders(self, symbol, instrument_key, tick_data):

        active_keys = [
            key for key in manager.active_connections.keys()
            if key.startswith(f"{symbol}:")
        ]

        for key in active_keys:

            try:

                _, expiry_str = key.split(":")

                expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d").date()

                builder = await chain_manager.get_builder(symbol, expiry_date)

                if builder:
                    task = asyncio.create_task(
                        builder.handle_tick(symbol, instrument_key, tick_data)
                    )
                    task.add_done_callback(lambda t: logger.error(f"Task failed: {t.exception()}") if t.exception() else None)

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