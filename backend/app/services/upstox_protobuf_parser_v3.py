"""
Upstox V3 Protobuf Parser for StrikeIQ
Parses websocket binary frames into normalized tick dictionaries
"""

import logging
import time
from typing import List, Dict, Optional

from app.proto.MarketDataFeedV3_pb2 import FeedResponse

logger = logging.getLogger(__name__)


# ---------------------------------------------------------
# MAIN DECODER
# ---------------------------------------------------------

async def decode_protobuf_message(message: bytes, tick_queue=None) -> List[Dict]:

    ticks: List[Dict] = []

    try:

        response = FeedResponse()
        response.ParseFromString(message)

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("PROTOBUF FRAME RECEIVED size=%d", len(message))

        feeds = getattr(response, "feeds", None)

        if not feeds:
            return []

        # feeds is a protobuf map
        if hasattr(feeds, "items"):
            feed_items = feeds.items()
        else:
            feed_items = []
            for entry in feeds:
                k = getattr(entry, "key", None)
                v = getattr(entry, "value", entry)
                if k:
                    feed_items.append((k, v))

        for instrument_key, feed in feed_items:

            if not instrument_key:
                continue

            is_index = instrument_key.startswith("NSE_INDEX")

            ltp: Optional[float] = None
            oi: int = 0
            volume: int = 0

            # =================================================
            # PRIMARY LTPC (FAST PATH)
            # =================================================

            try:
                if feed.HasField("ltpc"):
                    val = getattr(feed.ltpc, "ltp", None)
                    if val:
                        ltp = float(val)
            except Exception:
                pass

            # =================================================
            # FALLBACK: FEED UNION SAFE ACCESS
            # =================================================

            try:

                ff = getattr(feed, "ff", None)

                if ff:

                    market_ff = getattr(ff, "marketFF", None)
                    index_ff = getattr(ff, "indexFF", None)

                    # -----------------------------------------
                    # MARKET FF (options / equities)
                    # -----------------------------------------

                    if market_ff:

                        if getattr(market_ff, "ltpc", None) and getattr(market_ff.ltpc, "ltp", None):
                            ltp = float(market_ff.ltpc.ltp)

                        if not is_index:
                            # CRITICAL FIX: Extract OI with production-safe fallback logic
                            try:
                                oi = (
                                    getattr(market_ff.optionGreeks, "oi", 0) if getattr(market_ff, "optionGreeks", None) else 0
                                )
                                
                                # openInterest (camelCase)
                                oi = oi or getattr(market_ff, "openInterest", 0)
                                
                                # open_interest (snake_case fallback)
                                oi = oi or getattr(market_ff, "open_interest", 0)
                                
                                # marketOHLC.oi fallback
                                if not oi and getattr(market_ff, "marketOHLC", None):
                                    oi = getattr(market_ff.marketOHLC, "oi", 0)
                            except Exception:
                                oi = 0

                            if getattr(market_ff, "marketOHLC", None):
                                volume = getattr(market_ff.marketOHLC, "volume", 0)

                    # -----------------------------------------
                    # INDEX FF
                    # -----------------------------------------

                    if index_ff:

                        if getattr(index_ff, "ltpc", None) and getattr(index_ff.ltpc, "ltp", None):
                            ltp = float(index_ff.ltpc.ltp)

            except Exception:
                pass

            # =================================================
            # DROP INVALID TICKS
            # =================================================

            if ltp is None or ltp <= 0:
                continue

            # =================================================
            # BUILD NORMALIZED TICK
            # =================================================

            tick = {
                "instrument_key": instrument_key,
                "ltp": float(ltp),
                "oi": oi,
                "volume": volume,
                "timestamp": time.time()
            }

            ticks.append(tick)

            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(
                    "TICK PARSED → %s LTP=%s OI=%s VOL=%s",
                    instrument_key,
                    ltp,
                    oi,
                    volume
                )

            # -------------------------------------------------
            # OPTIONAL QUEUE PUSH
            # -------------------------------------------------

            if tick_queue:
                try:
                    await tick_queue.put(tick)
                except Exception as e:
                    logger.warning("Queue push failed: %s", e)

    except Exception as e:
        logger.error("PROTOBUF DECODE ERROR: %s", e, exc_info=True)
        return []

    # Tick throughput counter for observability
    if not hasattr(decode_protobuf_message, 'tick_counter'):
        decode_protobuf_message.tick_counter = 0
    decode_protobuf_message.tick_counter += len(ticks)
    
    # Log throughput every 1000 ticks
    if decode_protobuf_message.tick_counter % 1000 == 0:
        logger.info(f"[PIPELINE] ticks_processed={decode_protobuf_message.tick_counter}")

    return ticks


# ---------------------------------------------------------
# INDEX PRICE EXTRACTOR
# ---------------------------------------------------------

def extract_index_price(feed) -> Optional[float]:

    try:

        if feed.HasField("ltpc"):
            return float(feed.ltpc.ltp)

        ff = getattr(feed, "ff", None)

        if ff:

            market_ff = getattr(ff, "marketFF", None)
            index_ff = getattr(ff, "indexFF", None)

            if index_ff and getattr(index_ff, "ltpc", None):
                return float(index_ff.ltpc.ltp)

            if market_ff and getattr(market_ff, "ltpc", None):
                return float(market_ff.ltpc.ltp)

    except Exception:
        pass

    return None