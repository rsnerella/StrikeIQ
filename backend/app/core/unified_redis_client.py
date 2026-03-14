"""
Unified Redis Client for StrikeIQ
Supports both local Redis and Upstash Redis with automatic fallback
"""

import json
import logging
import asyncio
from enum import Enum
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager

import redis
from upstash_redis import Redis

from app.core.config import settings
from app.core.diagnostics import diag

logger = logging.getLogger(__name__)


class UpstashLock:
    """Simple lock implementation for Upstash Redis using key-based locking"""
    
    def __init__(self, client, name: str, timeout: Optional[int] = None):
        self.client = client
        self.name = f"lock:{name}"
        self.timeout = timeout or 30
        self.acquired = False
        
    async def acquire(self):
        """Acquire the lock"""
        import time
        start_time = time.time()
        
        while time.time() - start_time < self.timeout:
            # Try to set lock key with NX (only if not exists)
            result = self.client.set(self.name, "locked", nx=True, ex=self.timeout)
            if result:
                self.acquired = True
                return True
            await asyncio.sleep(0.1)
        
        return False
    
    async def release(self):
        """Release the lock"""
        if self.acquired:
            self.client.delete(self.name)
            self.acquired = False
    
    async def __aenter__(self):
        await self.acquire()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.release()


class RedisProvider(Enum):
    """Redis provider types"""
    LOCAL = "local"
    UPSTASH = "upstash"


class UnifiedRedisClient:
    """Unified Redis client supporting both local and Upstash Redis"""
    
    def __init__(self):
        self.local_client: Optional[redis.Redis] = None
        self.upstash_client: Optional[Redis] = None
        self.active_provider: Optional[RedisProvider] = None
        self._initialized = False
        
    async def initialize(self):
        """Setup Redis clients based on configuration"""
        # Setup local Redis client
        try:
            self.local_client = redis.Redis(
                host=settings.REDIS_HOST or "127.0.0.1",
                port=settings.REDIS_PORT or 6379,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
            # Test local connection
            await self.local_client.ping()
            diag("REDIS", "Local Redis client initialized")
            logger.info("✅ Local Redis client initialized")
        except Exception as e:
            diag("REDIS", f"Local Redis initialization failed: {e}")
            logger.warning(f"⚠️ Local Redis initialization failed: {e}")
            self.local_client = None
            
        # Setup Upstash Redis client
        if settings.is_upstash_enabled:
            try:
                self.upstash_client = Redis(
                    url=settings.UPSTASH_REDIS_REST_URL,
                    token=settings.UPSTASH_REDIS_TOKEN
                )
                # Test Upstash connection
                self.upstash_client.ping()
                diag("REDIS", "Upstash Redis client initialized")
                logger.info("✅ Upstash Redis client initialized")
            except Exception as e:
                diag("REDIS", f"Upstash Redis initialization failed: {e}")
                logger.warning(f"⚠️ Upstash Redis initialization failed: {e}")
                self.upstash_client = None
                
        # Determine active provider
        self.active_provider = await self._select_active_provider()
        
    async def _select_active_provider(self) -> Optional[RedisProvider]:
        """Select the active Redis provider based on availability and configuration"""
        if settings.REDIS_PROVIDER == "local":
            if self.local_client:
                return RedisProvider.LOCAL
            else:
                logger.error("❌ Local Redis requested but unavailable")
                return None
                
        elif settings.REDIS_PROVIDER == "upstash":
            if self.upstash_client:
                return RedisProvider.UPSTASH
            else:
                logger.error("❌ Upstash Redis requested but unavailable")
                return None
                
        else:  # auto mode
            # Prefer Upstash if available, otherwise use local
            if self.upstash_client:
                return RedisProvider.UPSTASH
            elif self.local_client:
                return RedisProvider.LOCAL
            else:
                logger.error("❌ No Redis provider available")
                return None
                
    async def get_client(self):
        """Get the active Redis client"""
        if not self._initialized:
            await self.initialize()
            
        if not self.active_provider:
            raise RuntimeError("No Redis provider available")
            
        if self.active_provider == RedisProvider.UPSTASH:
            return self.upstash_client
        else:
            return self.local_client
            
    @asynccontextmanager
    async def get_redis_client(self):
        """Context manager for getting Redis client"""
        client = await self.get_client()
        try:
            yield client
        except Exception as e:
            logger.error(f"Redis operation failed: {e}")
            # Try fallback if available
            if await self._try_fallback():
                client = await self.get_client()
                yield client
            else:
                raise
                
    async def _try_fallback(self) -> bool:
        """Try to fallback to alternative Redis provider"""
        if self.active_provider == RedisProvider.UPSTASH and self.local_client:
            try:
                await self.local_client.ping()
                self.active_provider = RedisProvider.LOCAL
                logger.info("🔄 Fallback to local Redis")
                return True
            except Exception:
                return False
        elif self.active_provider == RedisProvider.LOCAL and self.upstash_client:
            try:
                self.upstash_client.ping()
                self.active_provider = RedisProvider.UPSTASH
                logger.info("🔄 Fallback to Upstash Redis")
                return True
            except Exception:
                return False
        return False
        
    # Redis operation methods
    async def get(self, key: str) -> Optional[str]:
        """Get value from Redis"""
        try:
            client = await self.get_client()
            if self.active_provider == RedisProvider.UPSTASH:
                # Upstash Redis get is synchronous
                return client.get(key)
            else:
                # Local Redis get is async
                return await client.get(key)
        except Exception as e:
            logger.error(f"Redis GET failed for {key}: {e}")
            return None
            
    async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """Set value in Redis with optional expiration"""
        try:
            client = await self.get_client()
            if self.active_provider == RedisProvider.UPSTASH:
                # Upstash Redis uses different method signature
                if ex:
                    result = client.setex(key, ex, value)
                else:
                    result = client.set(key, value)
                return result is not None
            else:
                # Local Redis
                result = await client.set(key, value, ex=ex)
                return result
        except Exception as e:
            logger.error(f"Redis SET failed for {key}: {e}")
            return False
            
    async def setex(self, key: str, seconds: int, value: str) -> bool:
        """Set value with expiration (for compatibility)"""
        return await self.set(key, value, ex=seconds)
        
    async def set_json(self, key: str, data: dict, ex: Optional[int] = None) -> bool:
        """Set JSON data in Redis"""
        try:
            json_str = json.dumps(data)
            return await self.set(key, json_str, ex)
        except Exception as e:
            logger.error(f"Redis SET JSON failed for {key}: {e}")
            return False
            
    async def get_json(self, key: str) -> Optional[dict]:
        """Get JSON data from Redis"""
        try:
            value = await self.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Redis GET JSON failed for {key}: {e}")
            return None
            
    async def delete(self, key: str) -> bool:
        """Delete key from Redis"""
        try:
            client = await self.get_client()
            if self.active_provider == RedisProvider.UPSTASH:
                # Upstash Redis delete is synchronous
                result = client.delete(key)
                return result > 0
            else:
                # Local Redis delete is async
                result = await client.delete(key)
                return result > 0
        except Exception as e:
            logger.error(f"Redis DELETE failed for {key}: {e}")
            return False
            
    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis"""
        try:
            client = await self.get_client()
            if self.active_provider == RedisProvider.UPSTASH:
                # Upstash Redis exists is synchronous
                result = client.exists(key)
                return result > 0
            else:
                # Local Redis exists is async
                result = await client.exists(key)
                return result > 0
        except Exception as e:
            logger.error(f"Redis EXISTS failed for {key}: {e}")
            return False
            
    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration for key"""
        try:
            client = await self.get_client()
            if self.active_provider == RedisProvider.UPSTASH:
                # Upstash Redis expire is synchronous
                result = client.expire(key, seconds)
                return result
            else:
                # Local Redis expire is async
                result = await client.expire(key, seconds)
                return result
        except Exception as e:
            logger.error(f"Redis EXPIRE failed for {key}: {e}")
            return False
            
    async def keys(self, pattern: str) -> List[str]:
        """Get keys matching pattern"""
        try:
            client = await self.get_client()
            if self.active_provider == RedisProvider.UPSTASH:
                # Upstash Redis keys is synchronous
                result = client.keys(pattern)
                return result or []
            else:
                # Local Redis keys is async
                result = await client.keys(pattern)
                return result or []
        except Exception as e:
            logger.error(f"Redis KEYS failed for pattern {pattern}: {e}")
            return []
            
    async def hset(self, key: str, field: str, value: str) -> bool:
        """Set hash field in Redis"""
        try:
            client = await self.get_client()
            if self.active_provider == RedisProvider.UPSTASH:
                # Upstash Redis hset is synchronous
                result = client.hset(key, field, value)
                return result > 0
            else:
                # Local Redis hset is async
                result = await client.hset(key, field, value)
                return result > 0
        except Exception as e:
            logger.error(f"Redis HSET failed for {key}.{field}: {e}")
            return False
            
    async def hget(self, key: str, field: str) -> Optional[str]:
        """Get hash field from Redis"""
        try:
            client = await self.get_client()
            if self.active_provider == RedisProvider.UPSTASH:
                # Upstash Redis hget is synchronous
                return client.hget(key, field)
            else:
                # Local Redis hget is async
                return await client.hget(key, field)
        except Exception as e:
            logger.error(f"Redis HGET failed for {key}.{field}: {e}")
            return None
            
    async def hgetall(self, key: str) -> Dict[str, str]:
        """Get all hash fields from Redis"""
        try:
            client = await self.get_client()
            if self.active_provider == RedisProvider.UPSTASH:
                # Upstash Redis hgetall is synchronous
                result = client.hgetall(key)
                return result or {}
            else:
                # Local Redis hgetall is async
                result = await client.hgetall(key)
                return result or {}
        except Exception as e:
            logger.error(f"Redis HGETALL failed for {key}: {e}")
            return {}
            
    async def lpush(self, key: str, *values) -> int:
        """Push values to list head"""
        try:
            client = await self.get_client()
            if self.active_provider == RedisProvider.UPSTASH:
                # Upstash Redis lpush is synchronous
                result = client.lpush(key, *values)
                return result or 0
            else:
                # Local Redis lpush is async
                result = await client.lpush(key, *values)
                return result or 0
        except Exception as e:
            logger.error(f"Redis LPUSH failed for {key}: {e}")
            return 0
            
    async def lrange(self, key: str, start: int, end: int) -> List[str]:
        """Get list range"""
        try:
            client = await self.get_client()
            if self.active_provider == RedisProvider.UPSTASH:
                # Upstash Redis lrange is synchronous
                result = client.lrange(key, start, end)
                return result or []
            else:
                # Local Redis lrange is async
                result = await client.lrange(key, start, end)
                return result or []
        except Exception as e:
            logger.error(f"Redis LRANGE failed for {key}: {e}")
            return []
            
    async def rpop(self, key: str) -> Optional[str]:
        """Pop value from list tail"""
        try:
            client = await self.get_client()
            if self.active_provider == RedisProvider.UPSTASH:
                # Upstash Redis rpop is synchronous
                return client.rpop(key)
            else:
                # Local Redis rpop is async
                return await client.rpop(key)
        except Exception as e:
            logger.error(f"Redis RPOP failed for {key}: {e}")
            return None
            
    async def ping(self) -> bool:
        """Test Redis connection"""
        try:
            client = await self.get_client()
            if self.active_provider == RedisProvider.UPSTASH:
                # Upstash Redis ping is synchronous
                client.ping()
                return True
            else:
                # Local Redis ping is async
                await client.ping()
                return True
        except Exception as e:
            logger.error(f"Redis ping failed: {e}")
            return False
            
    async def lock(self, name: str, timeout: Optional[int] = None):
        """Create a distributed lock (Upstash compatible)"""
        client = await self.get_client()
        if self.active_provider == RedisProvider.UPSTASH:
            # Upstash Redis doesn't have native lock, use simple key-based lock
            return UpstashLock(client, name, timeout)
        else:
            # Local Redis has native lock support
            return client.lock(name, timeout=timeout)
    
    async def get_provider_info(self) -> Dict[str, Any]:
        """Get information about active Redis provider"""
        return {
            "active_provider": self.active_provider.value if self.active_provider else None,
            "local_available": self.local_client is not None,
            "upstash_available": self.upstash_client is not None,
            "configured_provider": settings.REDIS_PROVIDER,
            "upstash_enabled": settings.is_upstash_enabled
        }
        
    async def close(self):
        """Close Redis connections"""
        if self.local_client:
            await self.local_client.close()
        if self.upstash_client:
            # Upstash Redis doesn't need explicit close
            pass
        self._initialized = False
        logger.info("✅ Redis connections closed")


# Global unified Redis client instance
unified_redis_client = UnifiedRedisClient()

# Convenience functions for backward compatibility
async def get_redis_client() -> UnifiedRedisClient:
    """Get unified Redis client instance"""
    return unified_redis_client

# Legacy compatibility - direct access to client
redis_client = unified_redis_client

async def test_redis_connection(max_retries: int = 3, delay: int = 2):
    """Test Redis connection during startup with retry"""
    diag("REDIS", "Testing unified Redis connection")
    
    for attempt in range(1, max_retries + 1):
        try:
            await unified_redis_client.initialize()
            if await unified_redis_client.ping():
                provider_info = await unified_redis_client.get_provider_info()
                diag("REDIS", f"Redis connection OK using {provider_info['active_provider']}")
                logger.info(f"✅ Redis connection established using {provider_info['active_provider']}")
                return True
        except Exception as e:
            diag("REDIS", f"Redis FAILED: {e}")
            logger.warning(f"⚠️ Redis connection attempt {attempt} failed: {e}")
            if attempt < max_retries:
                await asyncio.sleep(delay)
    
    logger.error("❌ Redis unavailable after retries - system will use local cache fallback")
    return False
