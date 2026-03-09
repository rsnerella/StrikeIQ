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
        logger.info("DEBUG PARSED MESSAGE → %s", response)

        feeds = response.feeds
        
        # Handle feeds as a map (standard for Upstox V3) or fallback to list
        if hasattr(feeds, "items"):
            feed_items = feeds.items()
            feed_keys = list(feeds.keys())
        else:
            # Fallback for unexpected repeated field structure
            feed_items = []
            for entry in feeds:
                k = getattr(entry, "key", None)
                v = getattr(entry, "value", entry)
                if k:
                    feed_items.append((k, v))
            feed_keys = [k for k, v in feed_items]

        logger.info("PROTOBUF FEEDS STATUS → count=%d keys=%s", len(feed_items), feed_keys)
        
        if not feed_items:
            # logger.warning("DEBUG PARSED MESSAGE HAS NO FEEDS OR EMPTY LIST")
            return None

        for instrument_key, feed in feed_items:

            if not instrument_key:
                continue

            logger.info("DEBUG PROCESSING TICK → %s", instrument_key)

            if not instrument_key:
                continue

            segment = instrument_key.split("|")[0]

            ltp: Optional[float] = None
            oi: int = 0
            volume: int = 0

            # =================================================
            # PRIMARY LTP EXTRACTION
            # =================================================

            try:
                if feed.HasField("ltpc"):
                    val = getattr(feed.ltpc, "ltp", None)
                    if val:
                        ltp = float(val)
            except Exception:
                pass

            # =================================================
            # FALLBACK EXTRACTION FROM ff
            # =================================================

            try:
                ff = getattr(feed, "ff", None)

                if ff:

                    # index feed
                    index_ff = getattr(ff, "indexFF", None)
                    if index_ff and index_ff.HasField("ltpc"):
                        val = getattr(index_ff.ltpc, "ltp", None)
                        if val:
                            ltp = float(val)

                    # market feed
                    market_ff = getattr(ff, "marketFF", None)

                    if market_ff:

                        if market_ff.HasField("ltpc"):
                            val = getattr(market_ff.ltpc, "ltp", None)
                            if val:
                                ltp = float(val)

                        # nested fullFeed structure
                        full = getattr(market_ff, "fullFeed", None)
                        if full and full.HasField("ltpc"):
                            val = getattr(full.ltpc, "ltp", None)
                            if val:
                                ltp = float(val)

                        # volume and OI extraction from eFeedDetails
                        try:
                            if market_ff.HasField("eFeedDetails"):

                                details = market_ff.eFeedDetails

                                if hasattr(details, "vtt"):
                                    volume = int(details.vtt)

                                if hasattr(details, "oi"):
                                    oi = int(details.oi)
                        except Exception:
                            pass

            except Exception:
                pass

            # =================================================
            # OI EXTRACTION
            # =================================================

            try:
                if feed.HasField("optionGreeks"):
                    oi = int(feed.optionGreeks.oi)
            except Exception:
                pass

            # =================================================
            # DROP INVALID TICKS
            # =================================================

            if ltp is None or ltp <= 0:
                continue

            # Normalized Tick Logging
            logger.info("[%s] LTP DETECTED → %s OI=%s", segment, ltp, oi)

            tick = {
                "instrument_key": instrument_key,
                "ltp": float(ltp),
                "oi": oi,
                "volume": volume,
                "timestamp": time.time()
            }

            ticks.append(tick)

            # -------------------------------------------------
            # LOGGING
            # -------------------------------------------------

            if segment == "NSE_FO":
                logger.info(
                    f"OPTION TICK PARSED → {instrument_key} LTP={ltp} OI={oi} VOL={volume}"
                )
            else:
                logger.debug(
                    f"INDEX TICK → {instrument_key} LTP={ltp}"
                )

            # -------------------------------------------------
            # QUEUE PUSH
            # -------------------------------------------------

            if tick_queue:
                try:
                    await tick_queue.put(tick)
                except Exception as e:
                    logger.warning(f"Queue push failed: {e}")

        return ticks

    except Exception as e:

        logger.error(f"PROTOBUF DECODE ERROR: {e}", exc_info=True)
        return []


# ---------------------------------------------------------
# INDEX PRICE EXTRACTOR
# ---------------------------------------------------------

def extract_index_price(feed) -> Optional[float]:

    try:

        if feed.HasField("ltpc"):
            return float(feed.ltpc.ltp)

        ff = getattr(feed, "ff", None)

        if ff:

            index_ff = getattr(ff, "indexFF", None)
            if index_ff and index_ff.HasField("ltpc"):
                val = getattr(index_ff.ltpc, "ltp", None)
                if val:
                    return float(val)

            market_ff = getattr(ff, "marketFF", None)
            if market_ff and market_ff.HasField("ltpc"):
                val = getattr(market_ff.ltpc, "ltp", None)
                if val:
                    return float(val)

    except Exception:
        pass

    return None