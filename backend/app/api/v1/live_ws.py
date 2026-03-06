import asyncio
import logging
from datetime import datetime, timezone

from fastapi import WebSocket, WebSocketDisconnect, APIRouter, HTTPException

from app.services.websocket_market_feed import ws_feed_manager
from app.services.upstox_auth_service import get_upstox_auth_service
from app.services.instrument_registry import get_instrument_registry
from app.services.live_chain_manager import chain_manager
from app.core.ws_manager import manager

router = APIRouter(tags=["websocket"])
logger = logging.getLogger(__name__)

# Global dict for market status checks
upstox_feeds = {}


# =========================================================
# GLOBAL MARKET SOCKET
# =========================================================

@router.websocket("/market")
async def websocket_market(websocket: WebSocket):

    symbol = "GLOBAL"
    expiry = websocket.query_params.get("expiry") or "2023-12-31"
    key = f"{symbol}:{expiry}"

    await websocket.accept()
    logger.info(f"WS CONNECTED → {key}")

    auth_service = get_upstox_auth_service()

    # START GLOBAL FEED
    ws_feed = await ws_feed_manager.get_feed()
    if not ws_feed:
        try:
            ws_feed = await ws_feed_manager.start_feed()

        except HTTPException as e:

            pass

        except Exception as e:

            logger.error(f"WS INTERNAL ERROR → {str(e)}")

            await websocket.send_json({
                "status": "error",
                "message": "Internal server error",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

            await websocket.close(code=1011)
            return

    if not ws_feed:

        await websocket.send_json({
            "status": "error",
            "message": "Market feed unavailable",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        return

    builder = None
    builder_bg_task = None
    builder_task = None

    try:

        token = websocket.query_params.get("token")

        if not token:
            logger.warning("WS CLIENT CONNECT WITHOUT TOKEN")
            await websocket.close(code=1008)
            return

        registry = get_instrument_registry()
        await registry.wait_until_ready()

        symbol_upper = symbol

        valid_expiries = registry.options.get(symbol_upper, {}).keys()

        if expiry not in valid_expiries:

            await websocket.send_json({
                "type": "error",
                "message": "Invalid expiry"
            })

            await websocket.close(code=1008)
            return

        logger.info(f"Expiry validated → {symbol_upper}:{expiry}")

        expiry_date = datetime.strptime(expiry, "%Y-%m-%d").date()

        builder_task = asyncio.create_task(
            chain_manager.get_builder(symbol_upper, expiry_date)
        )

        await manager.connect(key, websocket)
        logger.info(f"WS REGISTERED → {key}")

        async def handle_builder_ready():

            try:

                builder = await builder_task

                if builder:

                    await builder.start()

                    chain_state = builder.get_latest_option_chain()

                    if chain_state:

                        chain_data = chain_state.build_final_chain()

                        await websocket.send_json({
                            "type": "chain_update",
                            "data": chain_data
                        })

                        logger.info(
                            f"INITIAL CHAIN SENT → {symbol_upper}"
                        )

                    else:

                        await websocket.send_json({
                            "type": "waiting",
                            "message": "Waiting for market data...",
                            "symbol": symbol_upper,
                            "expiry": expiry
                        })

            except Exception as e:

                logger.error(f"Builder init failed → {e}")

        builder_bg_task = asyncio.create_task(handle_builder_ready())

        # Passive keepalive loop
        while True:
            await asyncio.sleep(60)

    except WebSocketDisconnect:

        logger.info(f"WS DISCONNECTED → {key}")

    except Exception as e:

        logger.error(f"WS ERROR → {key}: {e}")

    finally:

        # cancel builder background task
        if builder_bg_task and not builder_bg_task.done():
            builder_bg_task.cancel()

        # stop builder safely
        if builder_task:

            try:

                builder = await builder_task

                if builder:
                    await builder.stop_tasks()

            except Exception:
                pass

        try:
            await manager.disconnect(websocket)
        except Exception:
            pass

        try:
            await websocket.close()
        except Exception:
            pass


# =========================================================
# SYMBOL SOCKET
# =========================================================

@router.websocket("/market/{symbol}")
async def websocket_symbol(websocket: WebSocket, symbol: str):

    expiry = websocket.query_params.get("expiry")

    if expiry in [None, "null", "None", "", "undefined"]:
        await websocket.close(code=1008)
        return

    key = f"{symbol}:{expiry}"

    await websocket.accept()
    logger.info(f"WS CONNECTED → {key}")

    auth_service = get_upstox_auth_service()

    ws_feed = await ws_feed_manager.get_feed()

    if not ws_feed:

        try:
            ws_feed = await ws_feed_manager.start_feed()

        except HTTPException as e:

            pass

    builder = None
    builder_task = None
    builder_bg_task = None

    try:

        token = websocket.query_params.get("token")

        if not token:
            logger.warning("WS CLIENT CONNECT WITHOUT TOKEN")
            await websocket.close(code=1008)
            return

        registry = get_instrument_registry()
        await registry.wait_until_ready()

        symbol_upper = symbol.upper()

        valid_expiries = registry.options.get(symbol_upper, {}).keys()

        if expiry not in valid_expiries:

            await websocket.send_json({
                "type": "error",
                "message": "Invalid expiry"
            })

            await websocket.close(code=1008)
            return

        logger.info(f"Expiry validated → {symbol_upper}:{expiry}")

        expiry_date = datetime.strptime(expiry, "%Y-%m-%d").date()

        builder_task = asyncio.create_task(
            chain_manager.get_builder(symbol_upper, expiry_date)
        )

        await manager.connect(key, websocket)

        async def handle_builder_ready():

            try:

                builder = await builder_task

                if builder:

                    await builder.start()

                    chain_state = builder.get_latest_option_chain()

                    if chain_state:

                        chain_data = chain_state.build_final_chain()

                        await websocket.send_json({
                            "type": "chain_update",
                            "data": chain_data
                        })

                    else:

                        await websocket.send_json({
                            "type": "waiting",
                            "message": "Waiting for market data...",
                            "symbol": symbol_upper,
                            "expiry": expiry
                        })

            except Exception as e:

                logger.error(f"Builder init failed → {e}")

        builder_bg_task = asyncio.create_task(handle_builder_ready())

        while True:
            await asyncio.sleep(60)

    except WebSocketDisconnect:

        logger.info(f"WS DISCONNECTED → {key}")

    except Exception as e:

        logger.error(f"WS ERROR → {key}: {e}")

    finally:

        if builder_bg_task and not builder_bg_task.done():
            builder_bg_task.cancel()

        if builder_task:

            try:

                builder = await builder_task

                if builder:
                    await builder.stop_tasks()

            except Exception:
                pass

        try:
            await manager.disconnect(websocket)
        except Exception:
            pass

        try:
            await websocket.close()
        except Exception:
            pass