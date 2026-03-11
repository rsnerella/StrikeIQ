from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect
import asyncio
import logging

logger = logging.getLogger(__name__)


class WSManager:

    def __init__(self):

        # Active connections
        self.active_connections: list[WebSocket] = []

        # Track subscriptions per client
        self.client_subscriptions: dict[WebSocket, dict] = {}

        # Prevent race conditions on list mutation
        self._lock = asyncio.Lock()

        # STEP 13 MONITORING: broadcast statistics
        self._total_broadcasts = 0
        self._total_connects = 0
        self._peak_connections = 0

    async def connect(self, websocket: WebSocket):

        async with self._lock:

            if websocket not in self.active_connections:
                self.active_connections.append(websocket)
                self._total_connects += 1
                self._peak_connections = max(self._peak_connections, len(self.active_connections))

            logger.info(
                f"🟢 WS CLIENT CONNECTED | clients={len(self.active_connections)} "
                f"total={self._total_connects} peak={self._peak_connections}"
            )

    async def disconnect(self, websocket: WebSocket):

        async with self._lock:

            if websocket in self.active_connections:
                self.active_connections.remove(websocket)

            # Remove client subscriptions
            self.client_subscriptions.pop(websocket, None)

            logger.info(
                f"🔴 WebSocket client disconnected | clients={len(self.active_connections)}"
            )

    async def register_subscription(self, websocket: WebSocket, symbol: str, expiry: str):
        """Register a subscription for a client"""
        logger.info(f"📡 Subscription registered → {symbol} {expiry}")
        
        async with self._lock:
            self.client_subscriptions[websocket] = {
                "symbol": symbol,
                "expiry": expiry
            }

    async def broadcast(self, message):
        """Broadcast message to all connected clients concurrently.

        We snapshot the connection list under _lock (brief), then release
        the lock BEFORE awaiting sends — this prevents a slow/dead client
        from blocking all other clients (head-of-line blocking).
        """

        # Brief lock to snapshot connections and subscriptions, then immediately release
        async with self._lock:
            connections = self.active_connections.copy()
            subscriptions = self.client_subscriptions.copy()
        
        logger.debug(f"WS CLIENT COUNT → {len(connections)}")
        logger.info(f"CLIENTS CONNECTED → {len(connections)}")
        
        if not connections:
            return

        logger.debug(f"WS broadcast → clients={len(connections)}")

        # Filter connections based on symbol subscription
        target_connections = []
        message_symbol = message.get("symbol")
        
        # TEMP DEBUG: Send to all clients for testing
        target_connections = connections
        logger.info(f"TEMP DEBUG: Broadcasting to all {len(connections)} clients")
        
        # TODO: Re-enable symbol filtering after debugging
        # if message_symbol:
        #     # Only send to clients subscribed to this symbol
        #     logger.info(f"FILTERING for symbol {message_symbol} across {len(connections)} clients")
        #     for conn in connections:
        #         client_sub = subscriptions.get(conn, {})
        #         logger.debug(f"Client subscription: {client_sub}")
        #         if client_sub.get("symbol") == message_symbol:
        #             target_connections.append(conn)
        #             logger.debug(f"Client MATCHES subscription")
        # else:
        #     # Non-symbol messages (like market status) go to all clients
        #     target_connections = connections

        # logger.info(f"TARGET CONNECTIONS: {len(target_connections)} for {message_symbol}")
        # if not target_connections:
        #     logger.warning(f"No clients subscribed to {message_symbol}")
        #     logger.warning(f"Available subscriptions: {[sub.get('symbol') for sub in subscriptions.values()]}")
        #     return

        results = await asyncio.gather(
            *[conn.send_json(message) for conn in target_connections],
            return_exceptions=True
        )

        # STEP 13 MONITORING: track broadcast count
        self._total_broadcasts += 1

        # Remove dead connections (re-acquire lock only for list mutation)
        dead = [
            conn for conn, result in zip(target_connections, results)
            if isinstance(result, Exception)
        ]
        if dead:
            async with self._lock:
                for conn in dead:
                    if conn in self.active_connections:
                        self.active_connections.remove(conn)
                    self.client_subscriptions.pop(conn, None)
            logger.warning(f"⚠️ Removed {len(dead)} dead WS connection(s)")


# Singleton instance
manager = WSManager()