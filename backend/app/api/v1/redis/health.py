"""
Redis Health Check API Endpoint
Provides information about Redis provider status and health
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import logging

from app.core.unified_redis_client import unified_redis_client
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/health", response_model=Dict[str, Any])
async def redis_health():
    """Get Redis health status and provider information"""
    try:
        # Initialize unified client if not already done
        await unified_redis_client.initialize()
        
        # Get provider information
        provider_info = await unified_redis_client.get_provider_info()
        
        # Test connection
        is_healthy = await unified_redis_client.ping()
        
        # Test basic operations
        test_key = "health_check_test"
        test_value = "ok"
        
        # Test SET/GET operations
        set_success = await unified_redis_client.set(test_key, test_value, ex=10)
        get_result = await unified_redis_client.get(test_key)
        
        # Clean up test key
        await unified_redis_client.delete(test_key)
        
        operations_ok = set_success and get_result == test_value
        
        return {
            "status": "healthy" if is_healthy and operations_ok else "unhealthy",
            "provider": provider_info,
            "connection_test": {
                "ping": is_healthy,
                "set_get_operations": operations_ok
            },
            "configuration": {
                "redis_provider": settings.REDIS_PROVIDER,
                "upstash_enabled": settings.is_upstash_enabled,
                "effective_redis_url": settings.effective_redis_url
            }
        }
        
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Redis health check failed: {str(e)}"
        )

@router.get("/provider", response_model=Dict[str, Any])
async def redis_provider_info():
    """Get detailed Redis provider information"""
    try:
        await unified_redis_client.initialize()
        provider_info = await unified_redis_client.get_provider_info()
        
        return {
            "provider": provider_info,
            "configuration": {
                "redis_provider": settings.REDIS_PROVIDER,
                "upstash_enabled": settings.is_upstash_enabled,
                "upstash_url": settings.UPSTASH_REDIS_URL,
                "upstash_rest_url": settings.UPSTASH_REDIS_REST_URL,
                "local_redis_url": settings.REDIS_URL,
                "effective_redis_url": settings.effective_redis_url
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get Redis provider info: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get Redis provider info: {str(e)}"
        )

@router.post("/switch-provider")
async def switch_redis_provider(provider: str):
    """Switch Redis provider (for testing purposes)"""
    if provider not in ["local", "upstash", "auto"]:
        raise HTTPException(
            status_code=400,
            detail="Provider must be one of: local, upstash, auto"
        )
    
    # This would typically be done through environment variables
    # For now, just return what would happen
    return {
        "message": f"Provider switch to {provider} requested",
        "note": "Actual switch requires updating REDIS_PROVIDER environment variable",
        "current_provider": settings.REDIS_PROVIDER,
        "requested_provider": provider
    }
