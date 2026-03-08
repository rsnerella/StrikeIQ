from datetime import datetime
import pytz
import logging

logger = logging.getLogger(__name__)

async def get_market_status():
    """
    Get market status using time-based logic only
    Returns: OPEN, PREOPEN, CLOSED, or UNKNOWN
    """
    try:
        ist = pytz.timezone("Asia/Kolkata")
        now = datetime.now(ist)

        # Weekends are always closed
        if now.weekday() >= 5:
            return "CLOSED"

        hour, minute = now.hour, now.minute

        # Pre-market hours (before 9:00)
        if hour < 9:
            return "CLOSED"

        # Pre-open session: 9:00 – 9:14 AM IST
        if hour == 9 and minute < 15:
            return "PREOPEN"

        # After-market hours (after 3:30 PM)
        if hour > 15 or (hour == 15 and minute > 30):
            return "CLOSED"

        return "OPEN"

    except Exception as e:
        logger.error(f"Time logic failed: {e}")
        return "UNKNOWN"
