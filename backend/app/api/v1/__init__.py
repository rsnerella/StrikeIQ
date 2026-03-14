"""
v1 API routers for StrikeIQ
"""

from .auth import router as auth_router
from .market.market_api import router as market_router
from .options import router as options_router
from .system import router as system_router
from .predictions import router as predictions_router
from .debug import router as debug_router
from .intelligence import router as intelligence_router
from .market_session import router as market_session_router
from .live_ws import router as live_ws_router
from .ws import router as ws_router
from .ai_status import router as ai_status_router
from .redis.health import router as redis_health_router

__all__ = [
    "auth_router",
    "market_router", 
    "options_router",
    "system_router",
    "predictions_router",
    "debug_router",
    "intelligence_router",
    "market_session_router",
    "live_ws_router",
    "ws_router",
    "ai_status_router",
    "redis_health_router"
]
