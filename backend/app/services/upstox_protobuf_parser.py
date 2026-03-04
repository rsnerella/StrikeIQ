import logging
from typing import List, Dict
from app.proto import MarketDataFeed_pb2

logger = logging.getLogger(__name__)


def decode_protobuf_message(message):

    try:

        decoded = MarketDataFeed_pb2.FeedResponse()
        decoded.ParseFromString(message)

        ticks = []

        if not decoded.feeds:
            logger.debug("UPSTOX HEARTBEAT RECEIVED")
            return []

        logger.info(f"PROTOBUF FEEDS RECEIVED = {len(decoded.feeds)}")

        for instrument_key, feed in decoded.feeds.items():

            logger.info(f"FEED KEY = {instrument_key}")

            tick = {
                "type": "option_tick",
                "instrument": instrument_key,
                "ltp": 0,
                "oi": 0,
                "volume": 0
            }

            # DEBUG: Log the feed structure
            logger.info(f"FEED STRUCTURE: {type(feed)}")
            logger.info(f"FEED HAS FF: {hasattr(feed, 'ff')}")
            if hasattr(feed, 'ff') and feed.ff:
                logger.info(f"FF STRUCTURE: {type(feed.ff)}")
                logger.info(f"FF HAS INDEXFF: {hasattr(feed.ff, 'indexFF')}")
                if hasattr(feed.ff, 'indexFF') and feed.ff.indexFF:
                    logger.info(f"INDEXFF STRUCTURE: {type(feed.ff.indexFF)}")
                    logger.info(f"INDEXFF HAS LTPC: {hasattr(feed.ff.indexFF, 'ltpc')}")
                    if hasattr(feed.ff.indexFF, 'ltpc') and feed.ff.indexFF.ltpc:
                        logger.info(f"LTPC STRUCTURE: {type(feed.ff.indexFF.ltpc)}")
                        logger.info(f"LTPC HAS LTP: {hasattr(feed.ff.indexFF.ltpc, 'ltp')}")
                        logger.info(f"LTPC LTP VALUE: {feed.ff.indexFF.ltpc.ltp}")

            # V2 format: Feed -> ff -> indexFF -> ltpc
            if hasattr(feed, "ff") and feed.ff and hasattr(feed.ff, "indexFF") and feed.ff.indexFF:
                index = feed.ff.indexFF
                if hasattr(index, "ltpc") and index.ltpc:
                    tick["ltp"] = float(index.ltpc.ltp)

            # Only add if valid LTP
            if tick["ltp"] > 0:
                logger.info(f"VALID TICK: {instrument_key} LTP={tick['ltp']}")
                ticks.append(tick)
            else:
                logger.warning(f"INVALID TICK: {instrument_key} LTP={tick['ltp']}")

        logger.info(f"TICKS EXTRACTED = {len(ticks)}")

        return ticks

    except Exception as e:

        logger.error(f"PROTOBUF DECODE ERROR: {e}")
        import traceback
        logger.error(f"TRACEBACK: {traceback.format_exc()}")
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