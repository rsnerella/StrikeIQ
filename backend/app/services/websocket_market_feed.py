import asyncio
import json
import logging
from typing import Optional
from datetime import datetime
from collections import deque

import httpx
import websockets
from fastapi import HTTPException

from app.services.token_manager import token_manager
from app.services.market_session_manager import get_market_session_manager
from app.services.upstox_protobuf_parser import decode_protobuf_message, extract_index_price
from app.core.live_market_state import MarketStateManager
from app.services.live_chain_manager import chain_manager
from app.core.ws_manager import manager
from app.services.instrument_registry import get_instrument_registry
from app.services.live_structural_engine import LiveStructuralEngine
from app.core.live_market_state import get_market_state_manager

logger = logging.getLogger(__name__)

last_market_status = None


def resolve_symbol_from_instrument(instrument_key: str):
    if not instrument_key:
        return None

    if instrument_key == "NSE_INDEX|Nifty 50":
        return "NIFTY"

    if instrument_key == "NSE_INDEX|Nifty Bank":
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

        self._message_queue = deque(maxlen=500)  # Reduced from 2000 to prevent memory bloat

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
            # Get NIFTY option instruments
            # ------------------------------------------------

            all_options = instrument_registry.get_option_instruments("NIFTY")

            if not all_options:
                logger.warning("⚠️ No option instruments found in registry")
                return

            # Prevent subscription overload
            limited_options = all_options[:40]

            # ------------------------------------------------
            # Build instrument list
            # ------------------------------------------------

            instrument_keys = [
                "NSE_INDEX|Nifty 50",
                "NSE_INDEX|Nifty Bank"
            ]

            instrument_keys.extend(limited_options)

            # Remove duplicates just in case
            instrument_keys = list(set(instrument_keys))

            # ------------------------------------------------
            # Subscription payload
            # ------------------------------------------------

            payload = {
                "guid": "strikeiq-feed",
                "method": "sub",
                "data": {
                    "mode": "full",   # REQUIRED for options + index feeds
                    "instrumentKeys": instrument_keys
                }
            }

            logger.info(f"UPSTOX SUBSCRIPTION PAYLOAD={len(instrument_keys)} instruments")

            if self.websocket is None:
                logger.error("WebSocket not initialized")
                return

            await self.websocket.send(json.dumps(payload))

            logger.info("📡 INDICES + OPTIONS SUBSCRIBED")

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
        """Receive messages from Upstox WebSocket and enqueue for processing.
        
        ARCHITECTURE: _recv_loop receives raw bytes and puts them into
        _message_queue. _process_loop reads from the queue, decodes protobuf,
        and broadcasts to frontend clients.
        """
        while self.running:
            try:
                if self.websocket is None:
                    logger.debug("WS connection missing")
                    await asyncio.sleep(1)
                    continue
                
                async for message in self.websocket:
                    try:
                        logger.info(f"UPSTOX RAW MESSAGE TYPE={type(message)} SIZE={len(message)}")
                        
                        if isinstance(message, bytes):
                            logger.info("UPSTOX RAW MESSAGE RECEIVED")
                            logger.info(f"UPSTOX RAW BYTES SIZE={len(message)}")
                            
                            # Enqueue for processing by _process_loop
                            self._message_queue.append(message)
                            
                        else:
                            # Ensure message is bytes
                            if isinstance(message, str):
                                message = message.encode()
                                
                            # Handle any JSON messages (unlikely with V3)
                            try:
                                data = json.loads(message)
                                
                                # Skip heartbeat messages
                                if data.get("type") == "heartbeat":
                                    continue
                                
                                # Broadcast market data directly for JSON
                                await manager.broadcast(data)
                                logger.info("WS BROADCAST SENT (JSON)")
                                
                            except json.JSONDecodeError:
                                logger.debug("Failed to parse JSON message")
                    
                    except Exception as e:
                        logger.error(f"Message processing error: {e}")
                
            except Exception as e:
                logger.error(f"Recv error → reconnecting: {e}")
                await self._handle_disconnect()
                break

    async def _process_loop(self):
        """Process queued binary messages: decode protobuf → extract ticks → broadcast."""

        while self.running:

            try:

                if self._message_queue:
                    raw = self._message_queue.popleft()
                else:
                    await asyncio.sleep(0.001)
                    continue

                # Decode protobuf in thread to avoid blocking event loop
                ticks = await asyncio.to_thread(decode_protobuf_message, raw)

                logger.info(f"PROTOBUF MESSAGE RECEIVED | TICKS={len(ticks)}")

                if not ticks:
                    continue

                for tick in ticks:

                    if tick.get("type") == "market_status":

                        status = tick.get("status")

                        global last_market_status

                        if status != last_market_status:

                            last_market_status = status

                            logger.warning(f"🚫 MARKET {status.upper()}")

                            await manager.broadcast(tick)

                        continue

                    # FIX 3: Broadcast NIFTY spot price
                    if "NSE_INDEX|Nifty 50" in tick.get("instrument", ""):

                        spot_tick = {
                            "type": "spot_tick",
                            "symbol": "NIFTY",
                            "spot": tick.get("ltp", 0)
                        }
                        await manager.broadcast(spot_tick)
                        logger.info(f"📡 BROADCAST → spot_tick NIFTY={tick.get('ltp', 0)}")

                    logger.info(f"📡 BROADCAST → {tick.get('type')} {tick.get('instrument')} LTP={tick.get('ltp')}")

                    # FIX 2: Ensure ticks broadcast to frontend
                    await manager.broadcast(tick)

            except Exception as e:

                logger.error(f"Process error: {e}")

    async def _handle_disconnect(self):
        self.is_connected = False
        self._reconnecting = False

        try:
            if self.websocket:
                await self.websocket.close()
        except Exception:
            pass

        await self._cancel_tasks()
        await asyncio.sleep(5)

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