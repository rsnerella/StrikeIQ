import json
import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.ws_manager import manager
from app.services.instrument_registry import get_instrument_registry

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/market")
async def market_ws(websocket: WebSocket):

    logger.info("🔌 FRONTEND WS CONNECTION ATTEMPT")

    await websocket.accept()

    logger.info("✅ WEBSOCKET ACCEPTED")
    logger.info("FRONTEND MARKET WS CONNECTED")

    await manager.connect(websocket)

    logger.info("✅ CLIENT REGISTERED")

    try:
        while True:
            try:
                message = await websocket.receive_text()

                data = json.loads(message)

                if data.get("type") == "subscribe":

                    symbol = data.get("symbol")
                    expiry = data.get("expiry")

                    instrument_registry = get_instrument_registry()
                    expiries = instrument_registry.get_expiries(symbol)

                    if not expiries:
                        logger.warning(f"No expiries found for symbol: {symbol}")
                        continue

                    if expiry not in expiries:

                        logger.warning(
                            f"Invalid expiry received: {expiry}, using default"
                        )

                        expiry = expiries[0]

                    logger.info(f"SUBSCRIPTION → {symbol} {expiry}")

                    await manager.register_subscription(websocket, symbol, expiry)

                    await websocket.send_json({
                        "type": "subscribed",
                        "symbol": symbol,
                        "expiry": expiry
                    })

            except WebSocketDisconnect:

                logger.info("🔌 CLIENT DISCONNECTED")

                await manager.disconnect(websocket)

                break

            except Exception as e:

                logger.error(f"WS MESSAGE ERROR: {e}")

    except WebSocketDisconnect:

        logger.info("🔌 CLIENT DISCONNECTED")

    except Exception as e:

        logger.error(f"WS ERROR: {e}")

    finally:

        await manager.disconnect(websocket)