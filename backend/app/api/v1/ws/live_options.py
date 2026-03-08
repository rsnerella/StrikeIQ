import asyncio
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.ws_manager import manager
from app.services.live_chain_manager import chain_manager
from app.services.instrument_registry import get_instrument_registry
from app.services.websocket_market_feed import ws_feed_manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/live-options/{symbol}")
async def live_options_ws(websocket: WebSocket, symbol: str):

    expiry = websocket.query_params.get("expiry")

    if expiry in [None, "null", "None", "", "undefined"]:
        await websocket.close()
        return

    key = f"{symbol}:{expiry}"

    await websocket.accept()
    await manager.connect(websocket)
    await manager.register_subscription(websocket, symbol, expiry or "")

    logger.info(f"🟢 WS CONNECTED → {key}")

    builder = None

    try:

        # GET REGISTRY SINGLETON
        registry = get_instrument_registry()
        await registry.wait_until_ready()

        # GET BUILDER (PER EXPIRY)
        builder = await chain_manager.get_builder(symbol, expiry)

        # START BUILDER ONLY ONCE
        await builder.start()

        # Passive keepalive loop.
        # Frontend does not send messages — server broadcasts via manager.broadcast()
        while True:
            await asyncio.sleep(60)

    except WebSocketDisconnect:

        logger.info(f"🔴 WS DISCONNECTED → {key}")
        await manager.disconnect(websocket)

        if builder:
            await builder.stop_tasks()

    except Exception as e:
        logger.error(f"❌ WS ERROR → {key}: {e}")
        await manager.disconnect(websocket)

        if builder:
            try:
                await builder.stop_tasks()
            except Exception:
                pass