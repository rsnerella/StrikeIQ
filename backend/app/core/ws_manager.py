from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect
import asyncio
import logging

logger = logging.getLogger(__name__)

# Global broadcast lock
broadcast_lock = asyncio.Lock()


class WSManager:

    def __init__(self):

        # Active connections
        self.active_connections: list[WebSocket] = []

        # Prevent race conditions
        self._lock = asyncio.Lock()

        # Instance broadcast lock
        self.broadcast_lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):

        async with self._lock:

            if websocket not in self.active_connections:
                self.active_connections.append(websocket)

            logger.info(f"🟢 WS CLIENT CONNECTED | clients={len(self.active_connections)}")

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
        """Broadcast message to all connected clients concurrently"""

        async with self.broadcast_lock:

            logger.info(f"BROADCAST CALLED → clients={len(self.active_connections)}")

            if not self.active_connections:
                return

            connections = self.active_connections.copy()

            tasks = []

            for connection in connections:
                tasks.append(connection.send_json(message))

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Remove dead connections
            for conn, result in zip(connections, results):

                if isinstance(result, Exception):
                    logger.warning("⚠️ Removing dead WS connection")

                    await self.disconnect(conn)


# Singleton instance
manager = WSManager()