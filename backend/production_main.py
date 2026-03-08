"""
Production Main Application for StrikeIQ
Implements clean architecture with all production-grade fixes
"""

import logging
import asyncio
import os
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from contextlib import asynccontextmanager

# Import production architecture
from app.core.production_architecture import production_lifecycle, get_architecture_orchestrator
from app.core.config import settings

# ================= LOGGING =================

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:%(name)s:%(message)s"
)

logger = logging.getLogger(__name__)

# ================= AI + SCHEDULER LOGGING CONFIG =================

AI_LOGS_ENABLED = os.getenv("AI_LOGS", "false").lower() == "true"

if AI_LOGS_ENABLED:
    logger.info("🤖 AI + Scheduler logs ENABLED")
else:
    # Suppress AI-related loggers
    logging.getLogger("ai").setLevel(logging.CRITICAL)
    logging.getLogger("app.services.ai_signal_engine").setLevel(logging.CRITICAL)
    logging.getLogger("app.services.paper_trade_engine").setLevel(logging.CRITICAL)
    
    # Suppress APScheduler loggers
    logging.getLogger("apscheduler.scheduler").setLevel(logging.CRITICAL)
    logging.getLogger("apscheduler.executors").setLevel(logging.CRITICAL)
    logging.getLogger("apscheduler").setLevel(logging.CRITICAL)
    
    logger.info("🤖 AI + Scheduler logs DISABLED")

# ================= AI CONFIG =================

ENABLE_AI = True

# ================= LEGACY IMPORTS (for compatibility) =================

# Keep these for backward compatibility during migration
from app.services.upstox_auth_service import get_upstox_auth_service
from app.services.websocket_market_feed import ws_feed_manager
from app.services.live_structural_engine import LiveStructuralEngine
from app.services.instrument_registry import get_instrument_registry
from app.core.redis_client import test_redis_connection
from app.market_data.market_data_service import get_latest_option_chain
from ai.scheduler import ai_scheduler

# ================= ROUTERS =================

from app.api.v1 import (
    auth_router,
    market_router,
    options_router,
    system_router,
    predictions_router,
    debug_router,
    intelligence_router,
    market_session_router,
    live_ws_router,
    ws_router,
    ai_status_router,
)

from app.api.v1.ws.live_options import router as ui_ws_router

# ================= LOCK =================

_ws_start_lock = asyncio.Lock()

# ================= PRODUCTION LIFESPAN =================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Production lifespan with clean architecture initialization
    """
    logger.info("🚀 Starting StrikeIQ Production API...")
    
    async with production_lifecycle() as orchestrator:
        # Store orchestrator in app state
        app.state.orchestrator = orchestrator
        
        # Legacy component initialization for compatibility
        await _initialize_legacy_components(app)
        
        yield
    
    logger.info("🛑 StrikeIQ Production API shutdown complete")

async def _initialize_legacy_components(app: FastAPI):
    """Initialize legacy components during migration"""
    try:
        # Instrument Registry
        registry = get_instrument_registry()
        await registry.load()
        app.state.registry = registry
        logger.info("🟢 Instrument registry READY")
    except Exception as e:
        logger.error(f"Instrument load failed: {e}")

    try:
        # Market Session Manager
        from app.services.market_session_manager import get_market_session_manager
        app.state.market_session_manager = get_market_session_manager()
    except Exception as e:
        logger.error(f"Market session startup failed: {e}")

    try:
        # Analytics Engine (if enabled)
        if ENABLE_AI:
            app.state.live_engine = LiveStructuralEngine(ws_feed_manager)
            app.state.analytics_task = asyncio.create_task(
                app.state.live_engine.start_analytics_loop()
            )
            logger.info("🧠 Analytics Engine Started")
    except Exception as e:
        logger.error(f"Live engine startup failed: {e}")

    try:
        # AI Scheduler (if enabled)
        if ENABLE_AI:
            ai_scheduler.start()
            logger.info("🧠 AI Scheduler Started")
        else:
            logger.info("🧠 AI Scheduler DISABLED")
    except Exception as e:
        logger.error(f"AI Scheduler start failed: {e}")

# ================= APP =================

app = FastAPI(
    title="StrikeIQ Production API",
    version="3.0.0",
    description="Real-time trading intelligence platform with production-grade architecture",
    lifespan=lifespan
)

# ================= CORS =================

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================= SESSION (SECURE) =================

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    session_cookie="session",
    same_site="strict",  # Enhanced security for financial app
    httponly=True,      # Prevent XSS
    secure=False        # Set to True in production with HTTPS
)

# ================= REQUEST LOGGING =================

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"REST → {request.method} {request.url.path}")
    
    response = await call_next(request)
    
    logger.info(f"REST ← {response.status_code}")
    
    return response

# ================= HEALTH ENDPOINTS =================

@app.get("/health")
async def health():
    """Basic health check"""
    return {"status": "ok", "version": "3.0.0"}

@app.get("/health/detailed")
async def detailed_health():
    """Detailed system health check"""
    try:
        orchestrator = get_architecture_orchestrator()
        return await orchestrator.get_system_health()
    except Exception as e:
        logger.error(f"Detailed health check failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "StrikeIQ Production API running",
        "version": "3.0.0",
        "architecture": "clean",
        "status": "operational"
    }

# ================= LEGACY ENDPOINTS (for compatibility) =================

@app.get("/api/v1/market-data/{symbol}")
async def get_market_data(symbol: str):
    """Legacy market data endpoint"""
    try:
        data = await get_latest_option_chain(symbol.upper())
        return {"status": "success", "data": data}
    except Exception as e:
        logger.error(str(e))
        raise HTTPException(status_code=500, detail="Market fetch failed")

@app.get("/system/ai-status")
async def get_ai_status():
    """AI system status"""
    try:
        from ai.scheduler import ai_scheduler
        from app.services.market_session_manager import get_market_session_manager
        
        market_manager = get_market_session_manager()
        is_market_open = await market_manager.is_market_open()
        
        job_status = ai_scheduler.get_job_status()
        
        return {
            "status": "running" if ai_scheduler.scheduler.running else "stopped",
            "market_open": is_market_open,
            "active_jobs": len(job_status),
            "last_run": "active" if ai_scheduler.scheduler.running else "inactive",
            "jobs": job_status
        }
    except Exception as e:
        logger.error(f"AI status check failed: {e}")
        return {
            "status": "error",
            "market_open": False,
            "active_jobs": 0,
            "last_run": "error",
            "jobs": []
        }

# ================= PRODUCTION ENDPOINTS =================

@app.get("/system/architecture")
async def get_architecture_status():
    """Get architecture status and metrics"""
    try:
        orchestrator = get_architecture_orchestrator()
        return await orchestrator.get_architecture_metrics()
    except Exception as e:
        logger.error(f"Architecture status failed: {e}")
        raise HTTPException(status_code=500, detail="Architecture status failed")

@app.post("/system/process-feed")
async def process_market_feed(feed_data: dict):
    """Process market feed through clean architecture"""
    try:
        orchestrator = get_architecture_orchestrator()
        await orchestrator.process_market_feed(feed_data)
        return {"status": "success", "message": "Feed processed successfully"}
    except Exception as e:
        logger.error(f"Feed processing failed: {e}")
        raise HTTPException(status_code=500, detail="Feed processing failed")

# ================= ROUTERS =================

app.include_router(auth_router)
app.include_router(market_router)
app.include_router(options_router)
app.include_router(system_router)
app.include_router(predictions_router)
app.include_router(debug_router)
app.include_router(intelligence_router)
app.include_router(market_session_router)
app.include_router(live_ws_router)
app.include_router(ws_router)
app.include_router(ai_status_router)
app.include_router(ui_ws_router)

# ================= PRODUCTION RUN =================

if __name__ == "__main__":
    uvicorn.run(
        "production_main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # No reload in production
        log_level="info"
    )
