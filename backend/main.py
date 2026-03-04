import logging
import asyncio
import os
from dotenv import load_dotenv
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from contextlib import asynccontextmanager
from app.core.config import settings

# ================= LOGGING =================

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:%(name)s:%(message)s"
)

logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# ================= AI + SCHEDULER LOGGING CONFIG =================

# AI + Scheduler logs toggle from environment variable
AI_LOGS_ENABLED = os.getenv("AI_LOGS", "false").lower() == "true"

# Configure specific AI and scheduler loggers based on environment variable
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


# ================= CORE =================

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

async def start_market_feed():
    """Start Upstox Market Feed with current token"""
    try:
        feed = await ws_feed_manager.start_feed()
        if feed and feed.is_connected:
            logger.info("🟢 Upstox Market Feed Started")
        else:
            logger.info("📡 Market feed supervisor started")
    except Exception as e:
        logger.error(f"Market feed startup failed: {e}")


# ================= LIFESPAN =================

@asynccontextmanager
async def lifespan(app: FastAPI):

    logger.info("🚀 Starting StrikeIQ API...")

    # -------- REDIS --------
    try:
        redis_ok = await test_redis_connection()
        if redis_ok:
            logger.info("✅ Redis connection established")
        else:
            logger.warning("⚠️ Redis unavailable")
    except Exception as e:
        logger.error(f"Redis check failed: {e}")

    # -------- INSTRUMENT REGISTRY --------
    try:
        registry = get_instrument_registry()
        await registry.load()
        app.state.registry = registry
        logger.info("🟢 Instrument registry READY")
    except Exception as e:
        logger.error(f"Instrument load failed: {e}")

    # -------- START UPSTOX MARKET FEED --------
    try:
        from app.services.token_manager import token_manager
        
        # Check if we have a token first
        token = await token_manager.ensure_token()

        if token:

            logger.info("Starting Upstox market feed")

            await start_market_feed()

        else:

            logger.warning("Market feed disabled because token missing")
                
    except Exception as token_error:
        logger.warning(f"⚠️ Upstox token validation error: {token_error}")
        logger.info("Market feed running in REST-only mode")
    except Exception as e:
        logger.error(f"Upstox feed startup failed: {e}")

    # -------- MARKET SESSION --------
    try:
        from app.services.market_session_manager import get_market_session_manager
        app.state.market_session_manager = get_market_session_manager()
    except Exception as e:
        logger.error(f"Market session startup failed: {e}")

    # -------- ANALYTICS ENGINE --------
    try:
        app.state.live_engine = LiveStructuralEngine(ws_feed_manager)

        app.state.analytics_task = asyncio.create_task(
            app.state.live_engine.start_analytics_loop()
        )

        logger.info("🧠 Analytics Engine Started")

    except Exception as e:
        logger.error(f"Live engine startup failed: {e}")

    # -------- AI SCHEDULER --------
    try:
        if ENABLE_AI:
            ai_scheduler.start()
            logger.info("🧠 AI Scheduler Started")
        else:
            logger.info("🧠 AI Scheduler DISABLED")
    except Exception as e:
        logger.error(f"AI Scheduler start failed: {e}")

    yield

    # ================= SHUTDOWN =================

    logger.info("🛑 Shutdown initiated...")

    try:
        if hasattr(app.state, "analytics_task"):
            app.state.analytics_task.cancel()
            await asyncio.gather(app.state.analytics_task, return_exceptions=True)
            logger.info("Analytics loop stopped")
    except Exception as e:
        logger.error(f"Analytics shutdown error: {e}")

    try:
        await ws_feed_manager.cleanup_all()
        logger.info("WS feed cleaned")
    except Exception as e:
        logger.error(f"WS cleanup failed: {e}")

    try:
        if ENABLE_AI:
            ai_scheduler.stop()
    except Exception as e:
        logger.error(f"AI Scheduler stop failed: {e}")

    try:
        auth_service = get_upstox_auth_service()
        await auth_service.close()
        logger.info("Auth service closed")
    except Exception as e:
        logger.error(f"Auth shutdown failed: {e}")


# ================= APP =================

app = FastAPI(
    title="StrikeIQ API",
    version="2.1.0",
    lifespan=lifespan
)


# ================= CORS =================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ================= SESSION =================

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    session_cookie="session",
    same_site="strict"  # Enhanced security for financial app
)


# ================= REQUEST LOGGING =================

@app.middleware("http")
async def log_requests(request: Request, call_next):

    logger.info(f"REST → {request.method} {request.url.path}")

    response = await call_next(request)

    logger.info(f"REST ← {response.status_code}")

    return response


# ================= HEALTH =================

@app.get("/health")
async def health():
    return {"status": "ok"}


# ================= ROOT =================

@app.get("/")
async def root():
    return {"message": "StrikeIQ API running"}


# ================= MARKET DATA =================

@app.get("/api/v1/market-data/{symbol}")
async def get_market_data(symbol: str):

    try:

        data = await get_latest_option_chain(symbol.upper())

        return {"status": "success", "data": data}

    except Exception as e:

        logger.error(str(e))

        raise HTTPException(status_code=500, detail="Market fetch failed")


# ================= WS INIT =================

@app.get("/api/ws/init")
async def init_websocket(request: Request):

    async with _ws_start_lock:

        feed = await ws_feed_manager.get_feed()

        if feed and feed.is_connected:
            logger.info("WS already connected")
            return {"status": "already_connected"}

        try:
            feed = await ws_feed_manager.start_feed()

            if not feed:
                raise HTTPException(status_code=500, detail="WS connect failed - no feed returned")
                
            if not feed.is_connected:
                raise HTTPException(status_code=500, detail="WS connect failed - not connected")

            request.session["WS_CONNECTED"] = True

            logger.info("🟢 WS CONNECTED")

            return {"status": "connected"}

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"WS init failed: {str(e)}")
            raise HTTPException(status_code=500, detail="WebSocket init failed")


# ================= SYSTEM MONITORING =================

@app.get("/system/ws-status")
async def get_websocket_status():
    """Get WebSocket connection status"""
    try:
        feed = await ws_feed_manager.get_feed()
        
        if feed and feed.is_connected:
            return {
                "status": "connected",
                "connected": True,
                "last_heartbeat": "active",
                "uptime": "running"
            }
        else:
            return {
                "status": "disconnected", 
                "connected": False,
                "last_heartbeat": "none",
                "uptime": "offline"
            }
    except Exception as e:
        logger.error(f"WS status check failed: {e}")
        return {
            "status": "error",
            "connected": False,
            "last_heartbeat": "error",
            "uptime": "unknown"
        }

@app.get("/system/ai-status")
async def get_ai_status():
    """Get AI scheduler status and market state"""
    try:
        from ai.scheduler import ai_scheduler
        from app.services.market_session_manager import get_market_session_manager
        
        market_manager = get_market_session_manager()
        is_market_open = await market_manager.is_market_open()
        
        # Get AI scheduler status
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


# ================= RUN =================

if __name__ == "__main__":

    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )