from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect
import asyncio
import logging

logger = logging.getLogger(__name__)


class WSManager:

    def __init__(self):

        # Active connections
        self.active_connections: list[WebSocket] = []

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

                logger.info(
                    f"🔴 WebSocket client disconnected | clients={len(self.active_connections)}"
                )

    async def register_subscription(self, websocket: WebSocket, symbol: str, expiry: str):
        """Register a subscription for a client"""
        logger.info(f"📡 Subscription registered → {symbol} {expiry}")
        # Future enhancement: track subscriptions per client
        pass

    async def broadcast(self, message):
        """Broadcast message to all connected clients concurrently.

        We snapshot the connection list under _lock (brief), then release
        the lock BEFORE awaiting sends — this prevents a slow/dead client
        from blocking all other clients (head-of-line blocking).
        """

        # Brief lock to snapshot connections, then immediately release
        async with self._lock:
            connections = self.active_connections.copy()

        if not connections:
            return

        logger.debug(f"WS broadcast → clients={len(connections)}")

        results = await asyncio.gather(
            *[conn.send_json(message) for conn in connections],
            return_exceptions=True
        )

        # STEP 13 MONITORING: track broadcast count
        self._total_broadcasts += 1

        # Remove dead connections (re-acquire lock only for list mutation)
        dead = [
            conn for conn, result in zip(connections, results)
            if isinstance(result, Exception)
        ]
        if dead:
            async with self._lock:
                for conn in dead:
                    if conn in self.active_connections:
                        self.active_connections.remove(conn)
            logger.warning(f"⚠️ Removed {len(dead)} dead WS connection(s)")


# Singleton instance
manager = WSManager()