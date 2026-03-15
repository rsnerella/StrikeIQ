from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
import logging
import asyncio

from app.services.upstox_auth_service import get_upstox_auth_service
from app.services.token_manager import token_manager
from core.logger import auth_logger, start_trace, clear_trace

logger = logging.getLogger(__name__)

router = APIRouter(tags=["authentication"])


class RefreshTokenRequest(BaseModel):
    refresh_token: str


# ================= AUTH STATUS =================

@router.get("/status")
async def auth_status():
    """
    Check if Upstox token exists in Redis
    """

    try:
        auth_state = token_manager.get_auth_state()

        if auth_state["token_available"]:
            return {
                "authenticated": True,
                "login_url": None
            }

        auth_service = get_upstox_auth_service()
        login_url = auth_service.get_authorization_url()

        return {
            "authenticated": False,
            "login_url": login_url
        }

    except Exception as e:
        logger.error(f"Auth status failed: {e}")

        auth_service = get_upstox_auth_service()
        login_url = auth_service.get_authorization_url()

        return {
            "authenticated": False,
            "login_url": login_url
        }


# ================= LOGIN =================

@router.get("/upstox")
def login():

    auth_service = get_upstox_auth_service()
    auth_url = auth_service.get_authorization_url()

    return RedirectResponse(auth_url)


# ================= CALLBACK =================

@router.get("/upstox/callback")
async def callback(code: str = Query(None), request: Request = None):

    trace_id = start_trace()

    auth_logger.info(
        "OAUTH CALLBACK HIT",
        {
            "trace_id": trace_id,
            "url": str(request.url) if request else None,
            "method": request.method if request else None
        }
    )

    if not code:
        clear_trace()
        raise HTTPException(status_code=400, detail="Authorization code missing")

    try:

        # Exchange code → access token
        token_data = await token_manager.login(code)

        auth_logger.info(
            "OAUTH TOKEN EXCHANGE SUCCESS",
            {
                "trace_id": trace_id,
                "access_token_len": len(token_data.get("access_token", "")),
                "expires_in": token_data.get("expires_in")
            }
        )

        logger.info("Upstox authentication successful")

        try:
            from app.services.websocket_market_feed import get_market_feed
            feed = get_market_feed()
            if feed:
                if not feed._is_connected:
                    logger.info("POST-AUTH: Reconnecting WebSocket feed...")
                    asyncio.create_task(feed.ensure_connection())
                    # Wait briefly for connection to establish
                    await asyncio.sleep(2)

                # Trigger the subscription that was deferred due to 401
                logger.info("POST-AUTH: Triggering pending subscription...")
                asyncio.create_task(feed.trigger_pending_subscription())
            else:
                logger.warning("POST-AUTH: Market feed not initialized yet")
        except Exception as e:
            logger.error(f"POST-AUTH subscription trigger failed: {e}")

        clear_trace()

        # STRICT redirect (user never sees callback URL)
        return RedirectResponse(
            url="http://localhost:3000?upstox=success",
            status_code=302
        )

    except Exception as e:

        logger.error(f"Upstox auth failed: {e}")

        clear_trace()

        return RedirectResponse(
            url="http://localhost:3000?upstox=failed",
            status_code=302
        )


# ================= REFRESH TOKEN =================

@router.post("/refresh")
async def refresh_token(request: RefreshTokenRequest):

    logger.warning("Token refresh requested but Upstox does not support it")

    raise HTTPException(
        status_code=400,
        detail="Token refresh not supported by Upstox. Please login again."
    )