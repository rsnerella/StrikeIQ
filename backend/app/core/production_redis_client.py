"""
Production Redis Client with Upstash Support
Optimized for high-performance async operations with Upstash Redis integration
"""

import logging
from typing import Optional, Any, Union, List
import json
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.unified_redis_client import unified_redis_client, UnifiedRedisClient

logger = logging.getLogger(__name__)

class ProductionRedisClient:
    """Production-grade Redis client with Upstash support"""
    
    def __init__(self):
        self._unified_client = unified_redis_client
    
    async def initialize(self):
        """Initialize Redis connection (delegated to unified client)"""
        await self._unified_client.initialize()
    
    async def close(self):
        """Close Redis connection (delegated to unified client)"""
        await self._unified_client.close()
    
    @asynccontextmanager
    async def get_client(self):
        """Get Redis client from unified client"""
        async with self._unified_client.get_redis_client() as client:
            yield client
    
    async def get(self, key: str) -> Optional[str]:
        """Get value from Redis"""
        return await self._unified_client.get(key)
    
    async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """Set value in Redis with optional expiration"""
        return await self._unified_client.set(key, value, ex)
    
    async def set_json(self, key: str, data: dict, ex: Optional[int] = None) -> bool:
        """Set JSON data in Redis"""
        return await self._unified_client.set_json(key, data, ex)
    
    async def get_json(self, key: str) -> Optional[dict]:
        """Get JSON data from Redis"""
        return await self._unified_client.get_json(key)
    
    async def delete(self, key: str) -> bool:
        """Delete key from Redis"""
        return await self._unified_client.delete(key)
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis"""
        return await self._unified_client.exists(key)
    
    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration for key"""
        return await self._unified_client.expire(key, seconds)
    
    async def keys(self, pattern: str) -> List[str]:
        """Get keys matching pattern"""
        return await self._unified_client.keys(pattern)
    
    async def hget(self, key: str, field: str) -> Optional[str]:
        """Get hash field"""
        return await self._unified_client.hget(key, field)
    
    async def hset(self, key: str, field: str, value: str) -> bool:
        """Set hash field"""
        return await self._unified_client.hset(key, field, value)
    
    async def hgetall(self, key: str) -> dict:
        """Get all hash fields"""
        return await self._unified_client.hgetall(key)
    
    async def lpush(self, key: str, *values) -> int:
        """Push values to list head"""
        return await self._unified_client.lpush(key, *values)
    
    async def rpop(self, key: str) -> Optional[str]:
        """Pop value from list tail"""
        return await self._unified_client.rpop(key)
    
    async def lrange(self, key: str, start: int, end: int) -> List[str]:
        """Get range of list values"""
        return await self._unified_client.lrange(key, start, end)
    
    async def publish(self, channel: str, message: str) -> int:
        """Publish message to channel"""
        try:
            client = await self._unified_client.get_client()
            result = await client.publish(channel, message)
            return result or 0
        except Exception as e:
            logger.error(f"Redis PUBLISH failed for {channel}: {e}")
            return 0
    
    async def subscribe(self, *channels) -> Any:
        """Subscribe to channels"""
        try:
            client = await self._unified_client.get_client()
            return await client.subscribe(*channels)
        except Exception as e:
            logger.error(f"Redis SUBSCRIBE failed: {e}")
            return None
    
    async def pipeline(self):
        """Get Redis pipeline for batch operations"""
        try:
            client = await self._unified_client.get_client()
            return client.pipeline()
        except Exception as e:
            logger.error(f"Redis pipeline creation failed: {e}")
            return None
    
    async def test_connection(self) -> bool:
        """Test Redis connection"""
        return await self._unified_client.ping()
    
    async def get_provider_info(self) -> dict:
        """Get information about Redis provider"""
        return await self._unified_client.get_provider_info()


# Global Redis client instance
production_redis = ProductionRedisClient()

# Convenience functions for backward compatibility
async def get_redis_client() -> ProductionRedisClient:
    """Get Redis client instance"""
    return production_redis

# Legacy compatibility - direct access to client
redis_client = production_redis

async def test_redis_connection():
    """Test Redis connection during startup"""
    return await production_redis.test_connection()
