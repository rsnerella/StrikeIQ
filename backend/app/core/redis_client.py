import redis.asyncio as redis
import logging
from app.core.config import settings
from app.core.diagnostics import diag
import asyncio

logger = logging.getLogger(__name__)

# Redis client for distributed locking and shared state
redis_client = redis.Redis(
    host=settings.REDIS_HOST or "127.0.0.1",
    port=settings.REDIS_PORT or 6379,
    decode_responses=True,
    socket_connect_timeout=5,
    socket_timeout=5,
    retry_on_timeout=True
)

async def test_redis_connection(max_retries: int = 3, delay: int = 2):
    """Test Redis connection during startup with retry (Task 7)"""
    # Add diagnostic logging for Redis connection test
    diag("REDIS", "Testing Redis connection")
    
    for attempt in range(1, max_retries + 1):
        try:
            await redis_client.ping()
            diag("REDIS", "Redis connection OK")
            logger.info("✅ Redis connection established")
            return True
        except Exception as e:
            diag("REDIS", f"Redis FAILED: {e}")
            logger.warning(f"⚠️ Redis connection attempt {attempt} failed: {e}")
            if attempt < max_retries:
                await asyncio.sleep(delay)
    
    logger.error("❌ Redis unavailable after retries - system will use local cache fallback")
    return False
