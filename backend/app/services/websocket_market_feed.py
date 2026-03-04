import asyncio
import json
import logging
from typing import Optional
from datetime import datetime

import httpx
import websockets
from fastapi import HTTPException

from app.services.token_manager import token_manager
from app.services.market_session_manager import get_market_session_manager
from app.services.upstox_protobuf_parser_v3 import decode_protobuf_message, extract_index_price
from app.proto.MarketDataFeed_pb2 import FeedResponse
from app.core.live_market_state import MarketStateManager
from app.services.live_chain_manager import chain_manager
from app.core.ws_manager import manager
from app.services.instrument_registry import get_instrument_registry
from app.services.live_structural_engine import LiveStructuralEngine
from app.core.live_market_state import get_market_state_manager

logger = logging.getLogger(__name__)

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
        self.last_tick_timestamp = None

        self._recv_task: Optional[asyncio.Task] = None
        self._process_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None

        self._client = httpx.AsyncClient(timeout=30)

    async def start(self):

        if self.running:
            return

        self.running = True

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
        logger.info("WS STATE → CONNECTED")
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
        Subscribe to NIFTY/BANKNIFTY indices + limited option contracts.
        """

        try:

            instrument_registry = get_instrument_registry()
            await instrument_registry.wait_until_ready()

            # ------------------------------------------------
            # TEST MINIMAL SUBSCRIPTION FIRST (STEP 4)
            # ------------------------------------------------
            
            instrument_keys = [
                "NSE_INDEX|NIFTY 50",
                "NSE_INDEX|NIFTY BANK",
                "NSE_EQ|INE009A01021"
            ]
            
            logger.info("INSTRUMENT KEYS (CORRECTED):")
            for k in instrument_keys:
                logger.info(k)

            # ------------------------------------------------
            # Subscription payload
            # ------------------------------------------------

            payload = {
                "guid": "strikeiq-feed",
                "method": "sub",
                "data": {
                    "mode": "ltpc",
                    "instrumentKeys": instrument_keys
                }
            }

            logger.info("SUBSCRIPTION PAYLOAD:")
            logger.info(json.dumps(payload, indent=2))
            logger.info(f"UPSTOX SUBSCRIPTION PAYLOAD={len(instrument_keys)} instruments")

            # STEP 1: Confirm subscription details
            logger.info(f"SUBSCRIBE MODE: {payload['data']['mode']}")
            logger.info(f"INSTRUMENT COUNT: {len(payload['data']['instrumentKeys'])}")
            for key in payload["data"]["instrumentKeys"]:
                logger.info(f"SUBSCRIBING → {key}")

            if self.websocket is None:
                logger.error("WebSocket not initialized")
                return

            await self.websocket.send(json.dumps(payload))

            # STEP 1: Confirm subscription sent
            logger.info("SUBSCRIPTION MESSAGE SENT TO UPSTOX")

            logger.info("📡 MINIMAL INDICES SUBSCRIPTION SENT")

        except Exception as e:

            logger.error(f"Subscription failed: {e}")

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
                
                # STEP 3: Improve WebSocket frame diagnostics
                logger.info("WS FRAME RECEIVED")

                if not raw:
                    continue

                # STEP 4: Detect JSON control frames
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

                packet_size = len(raw)
                logger.info(f"RAW PACKET SIZE = {packet_size}")

                # STEP 3: Always attempt protobuf decode
                logger.info("DECODING PROTOBUF MESSAGE")
                ticks = decode_protobuf_message(raw)

                if not ticks:
                    logger.debug("No ticks in packet")

                if ticks:
                    logger.info(f"PUSHING {len(ticks)} TICKS INTO QUEUE")
                    self.last_tick_timestamp = datetime.now()
                    await self._message_queue.put(ticks)

            except Exception as e:

                logger.error(f"WebSocket recv error: {e}")

                await self._handle_disconnect()

                break

    async def _process_loop(self):
        """Process queued binary messages: decode protobuf → extract ticks → broadcast."""

        logger.info("PROCESS LOOP STARTED")

        while self.running:

            try:

                ticks = await self._message_queue.get()
                logger.info("PROCESSING TICK FROM QUEUE")
                
                await self.broadcast_ticks(ticks)

            except Exception as e:

                logger.error(f"Process error: {e}")

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

        await self._cancel_tasks()

        try:
            if self.websocket:
                await self.websocket.close()
        except Exception:
            pass

        await self._client.aclose()

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
            logger.info("BROADCASTING TICK TO FRONTEND")
            await manager.broadcast(tick)


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