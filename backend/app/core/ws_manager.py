from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect
import asyncio
import logging
import json
from datetime import datetime

def json_safe(obj):
    """JSON serializer for datetime objects"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

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

    async def broadcast(self, payload: dict):
        """Broadcasts a payload to all connected clients with serialization safety."""
        if not self.active_connections:
            logger.warning("[WS MANAGER] No active connections — nothing to broadcast")
            return

        # 1. JSON Serialization with fallback
        try:
            # Handle if payload is already a string
            if isinstance(payload, str):
                message = payload
            else:
                message = json.dumps(payload, default=json_safe)
        except Exception as e:
            logger.error(f"[WS MANAGER] Serialization failure: {e}")
            try:
                # Emergency fallback to simple string conversion
                message = json.dumps(payload, default=str)
            except:
                logger.error("[WS MANAGER] ABSOLUTE SERIALIZATION FAILURE")
                return

        # 2. Concurrently broadcast to all active connections
        async with self._lock:
            connections = self.active_connections.copy()

        # STEP 5: VERIFY WS LAYER
        message_type = payload.get('type') if isinstance(payload, dict) else 'string'
        print("[WS SEND]", message_type)

        logger.info(f"[WS MANAGER] Broadcasting to {len(connections)} clients | type={message_type}")

        results = await asyncio.gather(
            *[conn.send_text(message) for conn in connections],
            return_exceptions=True
        )

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
                    self.client_subscriptions.pop(conn, None)
            logger.warning(f"⚠️ Removed {len(dead)} dead WS connection(s)")


# Singleton instance
manager = WSManager()

# NUCLEAR FIX — GLOBAL STRATEGY INJECTION
async def broadcast_with_strategy(payload):
    """Global wrapper that passes through analytics_update payloads"""
    
    if payload.get("type") == "analytics_update":
        analytics = payload.get("analytics") or {}
        
        # Use real strategy (already coming from backend)
        print("[FINAL REAL ANALYTICS]", analytics)
        
        payload["analytics"] = analytics
    
    await manager.broadcast(payload)