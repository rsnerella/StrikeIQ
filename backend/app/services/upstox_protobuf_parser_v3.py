from app.proto.MarketDataFeedV3_pb2 import FeedResponse
import logging

logger = logging.getLogger(__name__)


def decode_protobuf_message(message: bytes):
    """
    Decode Upstox V3 Market Data Feed protobuf messages.

    Handles:
    - Index ticks
    - Option ticks
    - Futures ticks

    Output format:
    {
        "instrument_key": "...",
        "ltp": float
    }
    """

    ticks = []

    try:
        response = FeedResponse()
        response.ParseFromString(message)

        feeds = response.feeds

        logger.info(f"FEEDS COUNT = {len(feeds)}")

        for entry in feeds:

            instrument_key = entry.key
            feed = entry.value

            # Safety checks
            if not feed.HasField("ff"):
                continue

            if not feed.ff.HasField("marketFF"):
                continue

            market = feed.ff.marketFF

            ltp = None

            # INDEX / BASIC LTPC
            if market.HasField("ltpc"):
                ltp = market.ltpc.ltp

            # OPTIONS / FUTURES (FULL MODE)
            elif market.HasField("fullFeed"):

                full = market.fullFeed

                if full.HasField("ltpc"):
                    ltp = full.ltpc.ltp

            if ltp is None:
                continue

            tick = {
                "instrument_key": instrument_key,
                "ltp": float(ltp)
            }

            ticks.append(tick)

            logger.info(f"TICK → {instrument_key}")
            logger.info(f"LTP → {ltp}")

        return ticks

    except Exception as e:
        logger.error(f"PROTOBUF DECODE ERROR: {e}")
        return []


def extract_index_price(feed):
    """
    Extract index price safely from feed.
    Used for ATM detection.
    """

    try:

        # Direct LTPC
        if hasattr(feed, "ltpc") and feed.ltpc:
            return float(feed.ltpc.ltp)

        # Index feed format
        if hasattr(feed, "ff") and feed.ff:

            if hasattr(feed.ff, "indexFF") and feed.ff.indexFF:

                index = feed.ff.indexFF

                if hasattr(index, "ltpc") and index.ltpc:
                    return float(index.ltpc.ltp)

    except Exception:
        pass

    return None