from dotenv import load_dotenv
load_dotenv()

import os
import logging
import asyncio
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

# ================= CORE CONFIG =================

from app.core.config import settings
from app.core.diagnostics import diag

# ================= SERVICES =================

from app.services.token_manager import token_manager
from app.services.websocket_market_feed import ws_feed_manager
from app.services.instrument_registry import get_instrument_registry
from app.services.live_structural_engine import LiveStructuralEngine
from app.services.poller_service import PollerService

# ================= INFRA =================

from app.core.redis_client import test_redis_connection
from db.init_schema import load_schema

# ================= AI =================

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
    ws_router,
    ai_status_router,
    redis_health_router,
)

from app.api.v1.diagnostics import router as diagnostics_router

from app.api.v1.ws.live_options import router as ui_ws_router


# ================= LOGGING =================

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:%(name)s:%(message)s"
)

logger = logging.getLogger(__name__)


# ================= BACKGROUND TASKS =================

async def snapshot_cleanup_worker():

    try:
        while True:

            from app.models.database import engine
            from sqlalchemy import text

            async with engine.begin() as conn:

                result = await conn.execute(
                    text("SELECT cleanup_old_snapshots()")
                )

                cleanup_result = result.scalar()

            logger.info(f"🧹 Snapshot cleanup executed: {cleanup_result}")

            await asyncio.sleep(86400)

    except asyncio.CancelledError:
        logger.info("Snapshot cleanup worker cancelled")
        raise


async def diagnostic_heartbeat():

    try:

        while True:

            diag("HEARTBEAT", "Backend alive")

            from app.core.diagnostics import log_pipeline_stats
            log_pipeline_stats()

            await asyncio.sleep(30)

    except asyncio.CancelledError:
        logger.info("Diagnostic heartbeat cancelled")
        raise


# ================= TOKEN WATCHER =================

async def token_watcher():

    try:

        token = await token_manager.ensure_token()

        if not token:

            logger.warning("Market feed waiting for Upstox token...")

            while not token:
                await asyncio.sleep(2)
                token = await token_manager.get_token()

        logger.info("Upstox token detected")

        from app.services.websocket_market_feed import start_market_feed

        await start_market_feed()

        logger.info("📡 Market feed started")

    except asyncio.CancelledError:
        logger.info("Token watcher cancelled")
        raise

    except Exception as e:
        logger.error(f"Token watcher failed: {e}")


# ================= POLLER LOOP =================

async def poller_loop():

    poller = PollerService()

    try:

        while True:

            diag("POLLER", "Polling market data")

            await poller.poll_market_data()

            await asyncio.sleep(2)

    except asyncio.CancelledError:
        logger.info("Poller loop cancelled")
        raise

    except Exception as e:
        logger.error(f"Poller loop error: {e}")


# ================= LIFESPAN =================

@asynccontextmanager
async def lifespan(app: FastAPI):

    logger.info("🚀 Starting StrikeIQ API...")

    app.state.background_tasks = []

    # -------- DATABASE --------

    try:

        from app.models.database import test_db_connection

        diag("DB", "Testing PostgreSQL connection")

        await load_schema()

        db_ok = await test_db_connection()

        if db_ok:
            diag("DB", "Connection OK")
            logger.info("✅ Database connected")
        else:
            diag("DB", "Connection FAILED")

    except Exception as e:
        logger.error(f"Database startup failed: {e}")

    # -------- REDIS --------

    try:

        redis_ok = await test_redis_connection()

        if redis_ok:
            logger.info("✅ Redis connected")
        else:
            logger.warning("Redis unavailable")

    except Exception as e:
        logger.error(f"Redis startup failed: {e}")

    # -------- INSTRUMENT REGISTRY --------

    try:

        registry = get_instrument_registry()

        await registry.load()

        app.state.registry = registry

        logger.info("🟢 Instrument registry ready")

    except Exception as e:
        logger.error(f"Instrument registry failed: {e}")

    # -------- MARKET CONTEXT --------

    try:

        from app.services.market_context_engine import market_context_engine

        await market_context_engine.initialize()

        logger.info("📈 Market context engine ready")

    except Exception as e:
        logger.error(f"Market context engine failed: {e}")

    # -------- TOKEN WATCHER --------

    try:

        task = asyncio.create_task(token_watcher(), name="token_watcher")

        app.state.background_tasks.append(task)

    except Exception as e:
        logger.error(f"Token watcher start failed: {e}")

    # -------- ANALYTICS BROADCASTER --------
    try:
        from app.services.analytics_broadcaster import analytics_broadcaster
        task = asyncio.create_task(
            analytics_broadcaster.start(),
            name="analytics_broadcaster"
        )
        app.state.background_tasks.append(task)
        logger.info("🧠 Analytics Broadcaster (Elite Engine) started")
    except Exception as e:
        logger.error(f"Analytics broadcaster failed: {e}")

    # -------- AI SCHEDULER --------

    try:

        import os
        env = os.getenv("ENV", "development")
        
        if env == "production":
            ai_scheduler.start()
            logger.info("🧠 AI Scheduler started (production)")
        else:
            logger.info("🧠 AI Scheduler disabled (development mode)")

    except Exception as e:
        logger.error(f"AI Scheduler failed: {e}")

    # -------- HEARTBEAT --------

    try:

        task = asyncio.create_task(
            diagnostic_heartbeat(),
            name="diagnostic_heartbeat"
        )

        app.state.background_tasks.append(task)

    except Exception as e:
        logger.error(f"Heartbeat failed: {e}")

    # -------- POLLER --------

    try:

        task = asyncio.create_task(
            poller_loop(),
            name="poller_loop"
        )

        app.state.background_tasks.append(task)

        logger.info("Option chain poller started")

    except Exception as e:
        logger.error(f"Poller failed: {e}")

    # -------- SNAPSHOT CLEANUP --------

    try:

        task = asyncio.create_task(
            snapshot_cleanup_worker(),
            name="snapshot_cleanup"
        )

        app.state.background_tasks.append(task)

        logger.info("Snapshot cleanup worker started")

    except Exception as e:
        logger.error(f"Cleanup worker failed: {e}")

    yield

    # ================= SHUTDOWN =================

    logger.info("🛑 Shutdown initiated...")

    try:

        for task in app.state.background_tasks:
            task.cancel()

        await asyncio.gather(
            *app.state.background_tasks,
            return_exceptions=True
        )

    except Exception as e:
        logger.warning(f"Background shutdown error: {e}")

    try:

        from app.services.websocket_market_feed import market_feed_instance

        if market_feed_instance:
            await market_feed_instance.stop()

    except Exception as e:
        logger.warning(f"Market feed stop error: {e}")

    logger.info("Shutdown complete")


# ================= FASTAPI APP =================

app = FastAPI(
    title="StrikeIQ API",
    version="2.1.0",
    lifespan=lifespan
)

# ================= SHUTDOWN EVENTS =================

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("StrikeIQ shutting down")
    
    try:
        from app.services.websocket_market_feed import market_feed_instance
        if market_feed_instance:
            await market_feed_instance.stop()
    except Exception as e:
        logger.warning(f"Market feed stop error: {e}")
    
    try:
        from app.services.oi_heatmap_engine import oi_heatmap_engine
        await oi_heatmap_engine.stop()
    except Exception as e:
        logger.warning(f"Heatmap stop error: {e}")
    
    try:
        from app.services.analytics_broadcaster import analytics_broadcaster
        await analytics_broadcaster.stop()
    except Exception as e:
        logger.warning(f"Analytics stop error: {e}")
    
    try:
        from app.services.live_structural_engine import structural_engine_instance
        if structural_engine_instance:
            await structural_engine_instance.stop()
    except Exception as e:
        logger.warning(f"Structural engine stop error: {e}")
    
    try:
        from ai.scheduler import ai_scheduler
        if ai_scheduler.running:
            ai_scheduler.shutdown(wait=False)
    except Exception as e:
        logger.warning(f"AI scheduler stop error: {e}")
    
    logger.info("All services stopped")


# ================= CORS =================

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ================= SESSION =================

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    session_cookie="session",
)


# ================= HEALTH =================

@app.get("/health")
async def health():
    return {"status": "ok"}


# ================= ROUTERS =================

app.include_router(auth_router, prefix="/api/v1/auth")
app.include_router(market_router, prefix="/api/v1/market")
app.include_router(options_router, prefix="/api/v1/options")
app.include_router(system_router, prefix="/api/v1")
app.include_router(predictions_router, prefix="/api/v1/predictions")
app.include_router(debug_router, prefix="/api/v1/debug")
app.include_router(intelligence_router, prefix="/api/v1/intelligence")
app.include_router(market_session_router, prefix="/api/v1/market")
app.include_router(ws_router)
app.include_router(ai_status_router, prefix="/api/v1/ai")
app.include_router(ui_ws_router)
app.include_router(diagnostics_router)
app.include_router(redis_health_router, prefix="/api/v1/redis")


# ================= RUN =================

if __name__ == "__main__":

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )