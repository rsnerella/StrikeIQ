import logging
from app.core.config import settings
from app.core.diagnostics import diag
from app.core.unified_redis_client import unified_redis_client

logger = logging.getLogger(__name__)

# Redis client for distributed locking and shared state (now uses unified client)
redis_client = unified_redis_client

async def test_redis_connection(max_retries: int = 3, delay: int = 2):
    """Test Redis connection during startup with retry (Task 7)"""
    # Add diagnostic logging for Redis connection test
    diag("REDIS", "Testing Redis connection with unified client")
    
    for attempt in range(1, max_retries + 1):
        try:
            await redis_client.initialize()
            if await redis_client.ping():
                provider_info = await redis_client.get_provider_info()
                diag("REDIS", f"Redis connection OK using {provider_info['active_provider']}")
                logger.info(f"✅ Redis connection established using {provider_info['active_provider']}")
                return True
        except Exception as e:
            diag("REDIS", f"Redis FAILED: {e}")
            logger.warning(f"⚠️ Redis connection attempt {attempt} failed: {e}")
            if attempt < max_retries:
                import asyncio
                await asyncio.sleep(delay)
    
    logger.error("❌ Redis unavailable after retries - system will use local cache fallback")
    return False
