import httpx
from datetime import datetime, time
import pytz
import logging
from app.services.token_manager import token_manager
from app.core.redis_client import redis_client

logger = logging.getLogger(__name__)

UPSTOX_STATUS_URL = "https://api.upstox.com/v2/market/status"
CACHE_KEY = "market_status"
CACHE_TTL = 30  # 30 seconds

async def get_market_status():
    """
    Get market status with Redis caching and Upstox API fallback
    Returns: OPEN, PREOPEN, CLOSED, or UNKNOWN
    """
    try:
        # Try Redis cache first
        cached_status = await redis_client.get(CACHE_KEY)
        if cached_status:
            logger.info(f"Market status from cache: {cached_status}")
            return cached_status
    except Exception as e:
        logger.warning(f"Redis cache read failed: {e}")

    # Get fresh status from Upstox API
    status = await _fetch_from_upstox()

    # Cache the result
    try:
        await redis_client.setex(CACHE_KEY, CACHE_TTL, status)
        logger.info(f"Cached market status: {status}")
    except Exception as e:
        logger.warning(f"Redis cache write failed: {e}")

    return status

async def _fetch_from_upstox():
    """
    Fetch market status from Upstox API with fallback
    """
    try:
        # Get token
        token = await token_manager.get_token()
        if not token:
            logger.warning("No Upstox token available, using time fallback")
            return _fallback_time_logic()

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        }

        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(UPSTOX_STATUS_URL, headers=headers)

            if response.status_code != 200:
                logger.warning(f"Upstox API error {response.status_code}, using time fallback")
                return _fallback_time_logic()

            data = response.json()

            # Extract NSE status
            nse_data = data.get("data", {}).get("NSE", {})
            exchange_status = nse_data.get("status", "UNKNOWN")

            # Map to our status values
            if exchange_status == "NORMAL_OPEN":
                return "OPEN"
            elif exchange_status.startswith("PRE_OPEN"):
                return "PREOPEN"
            else:
                return "CLOSED"

    except Exception as e:
        logger.error(f"Upstox API call failed: {e}, using time fallback")
        return _fallback_time_logic()

def _fallback_time_logic():
    """
    Fallback logic using IST time calculation
    """
    try:
        ist = pytz.timezone("Asia/Kolkata")
        now = datetime.now(ist)

        # Check weekday (Monday=0 to Friday=4)
        if now.weekday() > 4:
            return "CLOSED"

        # Check time range: 9:15 AM - 3:30 PM IST
        current_time = now.time()
        market_open = time(9, 15)
        market_close = time(15, 30)

        if market_open <= current_time <= market_close:
            return "OPEN"
        else:
            return "CLOSED"

    except Exception as e:
        logger.error(f"Time fallback failed: {e}")
        return "UNKNOWN"
