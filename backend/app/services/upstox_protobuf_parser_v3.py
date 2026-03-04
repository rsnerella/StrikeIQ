import logging
from typing import List, Dict
from app.services.MarketDataFeedV3_pb2 import FeedResponse, FeedData

logger = logging.getLogger(__name__)


def decode_protobuf_message_v3(message):

    try:

        decoded = FeedResponse()
        decoded.ParseFromString(message)

        ticks = []

        if not decoded.feeds:
            logger.debug("UPSTOX HEARTBEAT RECEIVED")
            return []

        logger.info(f"PROTOBUF FEEDS RECEIVED = {len(decoded.feeds)}")

        for feed_data in decoded.feeds:

            logger.info(f"FEED KEY = {feed_data.instrumentKey}")

            # Only process feeds with valid LTP
            if feed_data.ltp <= 0:
                continue

            # Create tick based on instrument type
            if "NSE_INDEX" in feed_data.instrumentKey:
                # Index tick
                tick = {
                    "type": "index_tick",
                    "instrument": feed_data.instrumentKey,
                    "ltp": float(feed_data.ltp),
                    "oi": int(feed_data.oi),
                    "volume": int(feed_data.volume)
                }
            else:
                # Option tick
                tick = {
                    "type": "option_tick",
                    "instrument": feed_data.instrumentKey,
                    "ltp": float(feed_data.ltp),
                    "oi": int(feed_data.oi),
                    "volume": int(feed_data.volume)
                }

            ticks.append(tick)

        logger.info(f"TICKS EXTRACTED = {len(ticks)}")

        return ticks

    except Exception as e:

        logger.error(f"PROTOBUF V3 DECODE ERROR: {e}")
        return []


def decode_protobuf_message(message):
    """
    Try both V2 and V3 protobuf formats
    """
    
    # First try V3 format (newer)
    try:
        ticks = decode_protobuf_message_v3(message)
        if ticks:
            return ticks
    except Exception as e:
        logger.debug(f"V3 format failed: {e}")
    
    # Fallback to V2 format (older)
    try:
        from app.proto import MarketDataFeed_pb2
        decoded = MarketDataFeed_pb2.FeedResponse()
        decoded.ParseFromString(message)

        ticks = []

        if not decoded.feeds:
            logger.debug("UPSTOX HEARTBEAT RECEIVED")
            return []

        logger.info(f"PROTOBUF V2 FEEDS RECEIVED = {len(decoded.feeds)}")

        for instrument_key, feed in decoded.feeds.items():

            logger.info(f"V2 FEED KEY = {instrument_key}")

            tick = {
                "type": "option_tick",
                "instrument": instrument_key,
                "ltp": 0,
                "oi": 0,
                "volume": 0
            }

            # V2 format: Feed -> ff -> indexFF -> ltpc
            if hasattr(feed, "ff") and feed.ff and hasattr(feed.ff, "indexFF") and feed.ff.indexFF:
                index = feed.ff.indexFF
                if hasattr(index, "ltpc") and index.ltpc:
                    tick["ltp"] = float(index.ltpc.ltp)

            # Only add if valid LTP
            if tick["ltp"] > 0:
                ticks.append(tick)

        logger.info(f"V2 TICKS EXTRACTED = {len(ticks)}")
        return ticks

    except Exception as e:
        logger.error(f"PROTOBUF V2 DECODE ERROR: {e}")
        return []


def extract_index_price(feed):

    try:

        if hasattr(feed, "ltpc") and feed.ltpc:
            return float(feed.ltpc.ltp)

        if hasattr(feed, "ff") and feed.ff and hasattr(feed.ff, "indexFF") and feed.ff.indexFF:
            index = feed.ff.indexFF
            if hasattr(index, "ltpc") and index.ltpc:
                return float(index.ltpc.ltp)

    except Exception:
        pass

    return None
