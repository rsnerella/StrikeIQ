import asyncio
import json
import logging
import time
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

        self._message_queue = asyncio.Queue()
        self._recv_task: Optional[asyncio.Task] = None
        self._process_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None

        self._client = httpx.AsyncClient(timeout=30)
        
        # Option subscription tracking
        self.current_atm = None
        self.current_expiry = None
        self.current_option_keys = []
        self.instrument_registry = None

    async def start(self):

        if self.running:
            return

        self.running = True

        # Start new components
        await option_chain_builder.start()
        await oi_heatmap_engine.start()
        await analytics_broadcaster.start()

        # Try to connect, but don't fail if authentication fails
        success = await self.ensure_connection()
        
        if not success:
            logger.warning("⚠️ WebSocket connection failed - running in REST-only mode")
            self.running = True
            self._start_tasks()
            return

        self._start_tasks()

        logger.info("Shared Upstox WS started")

    def _start_tasks(self):

        self._recv_task = asyncio.create_task(self._recv_loop())
        self._process_task = asyncio.create_task(self._process_loop())
        self._heartbeat_task = asyncio.create_task(self._heartbeat())

    async def _cancel_tasks(self):

        tasks = [self._recv_task, self._process_task, self._heartbeat_task]
        
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
        
        async with httpx.AsyncClient() as client:
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
            # TASK 5: SUBSCRIPTION PAYLOAD WITH LTPC MODE
            # ------------------------------------------------

            payload = {
                "guid": "strikeiq-feed",
                "method": "sub",
                "data": {
                    "mode": "full",
                    "instrumentKeys": instrument_keys
                }
            }

            logger.info("=== SUBSCRIPTION PAYLOAD ===")
            logger.info(json.dumps(payload, indent=2))
            logger.info(f"INSTRUMENT COUNT: {len(instrument_keys)}")

            if self.websocket is None:
                logger.error("WebSocket not initialized")
                return

            # TASK 5: CRITICAL - ADD 1-SECOND DELAY BEFORE SUBSCRIPTION
            logger.info("⏳ WAITING 1 SECOND BEFORE SUBSCRIPTION...")
            await asyncio.sleep(1)
            
            await self.websocket.send(json.dumps(payload).encode("utf-8"))

            # Confirm subscription sent
            logger.info("✅ SUBSCRIPTION SENT - WAITING FOR MARKET DATA")
            
            # TASK 6: START FAILSAFE TIMER FOR NO DATA DETECTION
            asyncio.create_task(self._failsafe_no_data_check())

        except Exception as e:

            logger.error(f"Subscription failed: {e}")

    async def subscribe_options(self, instrument_keys):
        """Subscribe to option instruments"""
        try:
            # Unsubscribe from old options first
            await self.unsubscribe_options()
            
            payload = {
                "guid": "strikeiq-options",
                "method": "sub",
                "data": {
                    "mode": "full",
                    "instrumentKeys": instrument_keys
                }
            }
            
            if self.websocket:
                await self.websocket.send(json.dumps(payload))
                self.current_option_keys = instrument_keys
                logger.info(f"✅ OPTIONS SUBSCRIPTION SENT: {len(instrument_keys)} instruments")
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
                
                # STEP 1: MARKET DATA ENTRY POINT - DEBUG ONLY
                if TICK_DEBUG:
                    logger.debug("WS FRAME RECEIVED")

                if not raw:
                    continue

                # STEP 1: PACKET SIZE LOGGING - DEBUG ONLY
                packet_size = len(raw)
                if TICK_DEBUG:
                    logger.debug(f"PACKET SIZE = {packet_size}")
                
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
                logger.info(f"=== RAW MESSAGE DEBUG ===")
                logger.info(f"RAW MESSAGE TYPE: {type(raw)}")
                logger.info(f"RAW PACKET SIZE: {len(raw)}")
                
                # Log first 50 bytes for structure analysis
                if len(raw) > 0:
                    sample_bytes = raw[:50]
                    logger.info(f"FIRST 50 BYTES: {sample_bytes.hex()}")
                
                # STEP 4: DECODE PROTOBUF
                ticks = decode_protobuf_message(raw)
                logger.info(f"PARSER OUTPUT → {len(ticks)} ticks")
                if TICK_DEBUG:
                    logger.debug(f"TICKS PARSED = {len(ticks)}")
                
                # STEP 1: EMPTY TICKS WARNING
                if not ticks:
                    if TICK_DEBUG:
                        logger.warning("NO TICKS IN MESSAGE")
                    
                if ticks:
                    # STEP 2: TICK PIPELINE TRACE - DEBUG ONLY
                    if TICK_DEBUG:
                        logger.debug("PUSHING TICKS INTO ANALYTICS QUEUE")
                    await self._message_queue.put(ticks)

            except Exception as e:

                logger.error(f"WebSocket recv error: {e}")

                await self._handle_disconnect()

                break

    async def _process_loop(self):
        """Process queued binary messages: decode protobuf → route ticks → broadcast."""

        logger.info("PROCESS LOOP STARTED")

        while self.running:

            try:

                ticks = await self._message_queue.get()
                logger.info("PROCESSING TICK FROM QUEUE")
                
                # Process each tick through message router
                for tick in ticks:
                    instrument = tick.get("instrument_key")
                    logger.info(f"PROCESSING → {instrument}")
                    # Route tick to appropriate processor
                    message = message_router.route_tick(tick)
                    
                    if message:
                        # Handle different message types
                        await self._handle_routed_message(message)
                
                # STEP 2: QUEUE WORKER TRACE - DEBUG ONLY
                if TICK_DEBUG:
                    logger.debug("ANALYTICS QUEUE WORKER ACTIVE")

            except Exception as e:

                logger.error(f"Process error: {e}")

    async def _handle_routed_message(self, message):
        """Handle routed messages and update appropriate components"""
        try:
            message_type = message["type"]
            symbol = message["symbol"]
            
            if message_type == "index_tick":
                # Update option chain builder with new spot price
                ltp = message["data"]["ltp"]
                option_chain_builder.update_index_price(symbol, ltp)
                
                # Detect ATM and subscribe to options for NIFTY
                if symbol == "NIFTY":
                    atm = get_atm_strike(ltp)
                    
                    if atm != self.current_atm:
                        self.current_atm = atm
                        
                        option_keys = build_option_keys(
                            symbol="NIFTY",
                            atm=atm,
                            expiry=self.current_expiry
                        )
                        
                        # Limit subscription to prevent overload
                        if len(option_keys) > 60:
                            option_keys = option_keys[:60]
                        
                        logger.info(f"SUBSCRIBING OPTIONS AROUND ATM {atm}")
                        logger.info(f"EXPIRY → {self.current_expiry}")
                        logger.info(f"TOTAL OPTIONS → {len(option_keys)}")
                        
                        payload = {
                            "guid": "strikeiq-options",
                            "method": "sub",
                            "data": {
                                "mode": "full",
                                "instrumentKeys": option_keys
                            }
                        }
                        
                        await self.websocket.send(json.dumps(payload))
                        logger.info(f"OPTIONS SUBSCRIBED → {len(option_keys)} instruments")
                
                # Broadcast index tick immediately
                await manager.broadcast(message)
                
            elif message_type == "option_tick":
                # Update option chain builder with option data
                strike = message["data"]["strike"]
                right = message["data"]["right"]
                ltp = message["data"]["ltp"]
                
                option_chain_builder.update_option_tick(symbol, strike, right, ltp)
                
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
            await manager.broadcast(tick)
            
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