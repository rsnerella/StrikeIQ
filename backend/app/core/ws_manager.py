from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect
import asyncio
import logging

logger = logging.getLogger(__name__)

# Global broadcast lock
broadcast_lock = asyncio.Lock()

class WSManager:

    def __init__(self):

        # Use set to prevent duplicates and allow O(1) operations
        self.connections: set[WebSocket] = set()

        # Lock prevents race conditions during connect/disconnect
        self._lock = asyncio.Lock()
        
        # Instance broadcast lock
        self.broadcast_lock = asyncio.Lock()


    async def connect(self, websocket: WebSocket):

        async with self._lock:

            # Prevent duplicate connection BEFORE accepting
            if websocket in self.connections:

                logger.warning(
                    "⚠️ Duplicate websocket connection ignored"
                )
                return

            await websocket.accept()

            self.connections.add(websocket)

            logger.info(f"🟢 WebSocket client connected | clients={len(self.connections)}")


    async def disconnect(self, websocket: WebSocket):

        async with self._lock:

            if websocket in self.connections:

                self.connections.remove(websocket)

                logger.info(
                    f"🔴 WebSocket client disconnected | clients={len(self.connections)}"
                )


    async def broadcast(self, message):

        async with self.broadcast_lock:

            dead_connections = []

            for connection in list(self.connections):

                try:
                    await connection.send_json(message)

                except Exception:

                    dead_connections.append(connection)

            for conn in dead_connections:
                if conn in self.connections:
                    self.connections.remove(conn)


# singleton instance
manager = WSManager()
