from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.ws_manager import manager
from app.core.redis_client import redis_client
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/market")
async def market_ws(websocket: WebSocket):

    await manager.connect(websocket)

    try:

        # Send initial market status
        await websocket.send_json({
            "type": "market_status",
            "data": {
                "market_open": False
            }
        })

        while True:

            # keep connection alive
            await websocket.receive()

    except WebSocketDisconnect:

        # normal client disconnect
        pass

    except RuntimeError:

        # websocket already closed
        pass

    except Exception as e:

        logger.error(f"WebSocket error: {e}")

    finally:

        # guaranteed cleanup
        await manager.disconnect(websocket)