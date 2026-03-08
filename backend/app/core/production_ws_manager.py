"""
Production-Grade WebSocket Manager for StrikeIQ
Manages connections, cleanup, and prevents memory leaks
"""

import asyncio
import logging
from typing import Dict, Set, Optional, Any, List
from datetime import datetime, timedelta
from fastapi import WebSocket
from contextlib import asynccontextmanager
import json
import weakref

logger = logging.getLogger(__name__)

class WebSocketConnection:
    """Individual WebSocket connection with metadata"""
    
    def __init__(self, websocket: WebSocket, connection_id: str):
        self.websocket = websocket
        self.connection_id = connection_id
        self.connected_at = datetime.utcnow()
        self.last_activity = datetime.utcnow()
        self.is_alive = True
        self._ping_task: Optional[asyncio.Task] = None
        self._pong_received = True
    
    async def start_ping_monitor(self):
        """Start ping/pong monitoring"""
        self._ping_task = asyncio.create_task(self._ping_loop())
    
    async def _ping_loop(self):
        """Send periodic pings to check connection health"""
        try:
            while self.is_alive:
                await asyncio.sleep(30)  # Ping every 30 seconds
                
                if not self._pong_received:
                    logger.warning(f"Connection {self.connection_id} missed pong - marking as dead")
                    self.is_alive = False
                    break
                
                self._pong_received = False
                await self.websocket.ping()
                
        except Exception as e:
            logger.error(f"Ping loop error for {self.connection_id}: {e}")
            self.is_alive = False
    
    def handle_pong(self):
        """Handle pong response"""
        self._pong_received = True
        self.last_activity = datetime.utcnow()
    
    async def cleanup(self):
        """Cleanup connection resources"""
        self.is_alive = False
        if self._ping_task:
            self._ping_task.cancel()
            try:
                await self._ping_task
            except asyncio.CancelledError:
                pass

class ProductionWebSocketManager:
    """Production-grade WebSocket connection manager"""
    
    def __init__(self):
        self.connections: Dict[str, WebSocketConnection] = {}
        self.channel_subscriptions: Dict[str, Set[str]] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        self._connection_counter = 0
    
    async def start(self):
        """Start the manager background tasks"""
        if not self._cleanup_task:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("WebSocket manager started")
    
    async def stop(self):
        """Stop the manager and cleanup all connections"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Close all connections
        for connection in list(self.connections.values()):
            await self._close_connection(connection)
        
        self.connections.clear()
        self.channel_subscriptions.clear()
        logger.info("WebSocket manager stopped")
    
    async def _cleanup_loop(self):
        """Periodic cleanup of dead connections"""
        while True:
            try:
                await asyncio.sleep(60)  # Cleanup every minute
                
                async with self._lock:
                    dead_connections = [
                        conn for conn in self.connections.values()
                        if not conn.is_alive or 
                        (datetime.utcnow() - conn.last_activity) > timedelta(minutes=5)
                    ]
                    
                    for conn in dead_connections:
                        await self._close_connection(conn)
                        if conn.connection_id in self.connections:
                            del self.connections[conn.connection_id]
                
                if dead_connections:
                    logger.info(f"Cleaned up {len(dead_connections)} dead connections")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup loop error: {e}")
    
    async def connect(self, websocket: WebSocket, channels: List[str] = None) -> str:
        """Connect a new WebSocket client"""
        await websocket.accept()
        
        self._connection_counter += 1
        connection_id = f"ws_{self._connection_counter}_{int(datetime.utcnow().timestamp())}"
        
        connection = WebSocketConnection(websocket, connection_id)
        await connection.start_ping_monitor()
        
        async with self._lock:
            self.connections[connection_id] = connection
            
            # Subscribe to channels
            if channels:
                for channel in channels:
                    if channel not in self.channel_subscriptions:
                        self.channel_subscriptions[channel] = set()
                    self.channel_subscriptions[channel].add(connection_id)
        
        logger.info(f"WebSocket connected: {connection_id} to channels: {channels}")
        
        # Send initial state
        await self._send_initial_state(connection, channels)
        
        return connection_id
    
    async def disconnect(self, connection_id: str):
        """Disconnect a WebSocket client"""
        async with self._lock:
            connection = self.connections.get(connection_id)
            if connection:
                await self._close_connection(connection)
                del self.connections[connection_id]
                
                # Remove from channel subscriptions
                for channel, subscribers in self.channel_subscriptions.items():
                    subscribers.discard(connection_id)
                
                logger.info(f"WebSocket disconnected: {connection_id}")
    
    async def _close_connection(self, connection: WebSocketConnection):
        """Close a single connection"""
        try:
            await connection.cleanup()
            await connection.websocket.close()
        except Exception as e:
            logger.error(f"Error closing connection {connection.connection_id}: {e}")
    
    async def _send_initial_state(self, connection: WebSocketConnection, channels: List[str]):
        """Send initial state to newly connected client"""
        try:
            # Send market status
            from app.services.market_session_manager import get_market_session_manager
            from app.services.market_status_service import get_market_status
            market_manager = get_market_session_manager()
            market_open = await market_manager.is_market_open()
            market_status = await get_market_status()
            
            await connection.websocket.send_json({
                "type": "market_status",
                "market_open": market_open,
                "status": market_status,
                "timestamp": datetime.utcnow().isoformat(),
                "connection_id": connection.connection_id
            })
            
            # Send last tick if available
            from app.core.redis_client import redis_client
            last_tick = await redis_client.get("market:last_tick")
            if last_tick:
                await connection.websocket.send_json({
                    "type": "market_tick",
                    "data": json.loads(last_tick),
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            logger.info(f"Initial state sent to {connection.connection_id}")
            
        except Exception as e:
            logger.error(f"Failed to send initial state to {connection.connection_id}: {e}")
    
    async def broadcast_to_channel(self, channel: str, message: Dict[str, Any]):
        """Broadcast message to all subscribers of a channel"""
        async with self._lock:
            subscribers = self.channel_subscriptions.get(channel, set()).copy()
        
        if not subscribers:
            return
        
        dead_connections = []
        
        for connection_id in subscribers:
            connection = self.connections.get(connection_id)
            if connection and connection.is_alive:
                try:
                    await connection.websocket.send_json(message)
                    connection.last_activity = datetime.utcnow()
                except Exception as e:
                    logger.error(f"Failed to send to {connection_id}: {e}")
                    dead_connections.append(connection_id)
            else:
                dead_connections.append(connection_id)
        
        # Clean up dead connections
        for conn_id in dead_connections:
            await self.disconnect(conn_id)
    
    async def broadcast_to_all(self, message: Dict[str, Any]):
        """Broadcast message to all connected clients"""
        async with self._lock:
            connection_ids = list(self.connections.keys())
        
        for connection_id in connection_ids:
            connection = self.connections.get(connection_id)
            if connection and connection.is_alive:
                try:
                    await connection.websocket.send_json(message)
                    connection.last_activity = datetime.utcnow()
                except Exception as e:
                    logger.error(f"Broadcast failed to {connection_id}: {e}")
                    await self.disconnect(connection_id)
    
    async def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        async with self._lock:
            total_connections = len(self.connections)
            alive_connections = sum(1 for conn in self.connections.values() if conn.is_alive)
            channel_stats = {
                channel: len(subscribers) 
                for channel, subscribers in self.channel_subscriptions.items()
            }
        
        return {
            "total_connections": total_connections,
            "alive_connections": alive_connections,
            "dead_connections": total_connections - alive_connections,
            "channel_subscriptions": channel_stats,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def handle_pong(self, connection_id: str):
        """Handle pong message from client"""
        async with self._lock:
            connection = self.connections.get(connection_id)
            if connection:
                connection.handle_pong()

# Global WebSocket manager instance
ws_manager = ProductionWebSocketManager()

async def get_ws_manager() -> ProductionWebSocketManager:
    """Get WebSocket manager instance"""
    return ws_manager

# WebSocket endpoint decorator
@asynccontextmanager
async def websocket_endpoint(websocket: WebSocket, channels: List[str] = None):
    """Context manager for WebSocket endpoints"""
    connection_id = None
    try:
        connection_id = await ws_manager.connect(websocket, channels)
        yield connection_id
    except Exception as e:
        logger.error(f"WebSocket endpoint error: {e}")
        if connection_id:
            await ws_manager.disconnect(connection_id)
        raise
    finally:
        if connection_id:
            await ws_manager.disconnect(connection_id)
