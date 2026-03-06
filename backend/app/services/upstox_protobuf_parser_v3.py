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

        if not response.feeds:
            logger.warning("PROTOBUF MESSAGE HAS NO FEEDS - IGNORING FRAME")
            return []

        feeds = response.feeds

        logger.info(f"VALID FEED FRAME RECEIVED count={len(feeds)}")

        for entry in feeds:

            instrument_key = entry.key
            feed = entry.value

            if not instrument_key:
                continue

            segment = instrument_key.split("|")[0]

            ltp: Optional[float] = None
            oi: Optional[int] = None
            volume: Optional[int] = None

            # =================================================
            # OPTION / FUTURES PARSING
            # =================================================

            if segment == "NSE_FO":

                ff = getattr(feed, "ff", None)

                if ff:

                    market_ff = getattr(ff, "marketFF", None)

                    if market_ff:

                        # ---- fullFeed ----
                        full = getattr(market_ff, "fullFeed", None)

                        if full:

                            ltpc = getattr(full, "ltpc", None)

                            if ltpc:
                                ltp = getattr(ltpc, "ltp", None)

                            e_details = getattr(full, "eFeedDetails", None)

                            if e_details:
                                oi = getattr(e_details, "oi", None)
                                volume = getattr(e_details, "volume", None)

                        # ---- fallback ltpc ----
                        if ltp is None:

                            ltpc = getattr(market_ff, "ltpc", None)

                            if ltpc:
                                ltp = getattr(ltpc, "ltp", None)

                # ---- feed fallback ----
                if ltp is None:

                    ltpc = getattr(feed, "ltpc", None)

                    if ltpc:
                        ltp = getattr(ltpc, "ltp", None)

                if ltp is None:
                    continue

                tick = {
                    "instrument_key": instrument_key,
                    "ltp": float(ltp),
                    "oi": int(oi) if oi is not None else 0,
                    "volume": int(volume) if volume is not None else 0,
                    "timestamp": time.time()
                }

                ticks.append(tick)

                logger.debug(
                    f"OPTION TICK → {instrument_key} LTP={ltp} OI={oi} VOL={volume}"
                )

                if tick_queue:
                    try:
                        await tick_queue.put(tick)
                    except Exception as e:
                        logger.warning(f"Queue push failed: {e}")

                continue

            # =================================================
            # INDEX PARSING
            # =================================================

            ff = getattr(feed, "ff", None)

            if not ff:
                continue

            # ---- PRIMARY: indexFF ----
            index_ff = getattr(ff, "indexFF", None)

            if index_ff:

                ltpc = getattr(index_ff, "ltpc", None)

                if ltpc:
                    ltp = getattr(ltpc, "ltp", None)

            # ---- SECONDARY: marketFF ----
            if ltp is None:

                market_ff = getattr(ff, "marketFF", None)

                if market_ff:

                    ltpc = getattr(market_ff, "ltpc", None)

                    if ltpc:
                        ltp = getattr(ltpc, "ltp", None)

                    else:

                        full = getattr(market_ff, "fullFeed", None)

                        if full:

                            ltpc = getattr(full, "ltpc", None)

                            if ltpc:
                                ltp = getattr(ltpc, "ltp", None)

            if ltp is None:
                continue

            tick = {
                "instrument_key": instrument_key,
                "ltp": float(ltp),
                "timestamp": time.time()
            }

            ticks.append(tick)

            logger.debug(f"INDEX TICK → {instrument_key} LTP={ltp}")

        return ticks

    except Exception as e:

        logger.error(f"PROTOBUF DECODE ERROR: {e}", exc_info=True)

        return []


# ---------------------------------------------------------
# INDEX PRICE EXTRACTOR
# ---------------------------------------------------------

def extract_index_price(feed) -> Optional[float]:

    try:

        if hasattr(feed, "ltpc") and feed.ltpc:
            return float(feed.ltpc.ltp)

        ff = getattr(feed, "ff", None)

        if ff:

            index_ff = getattr(ff, "indexFF", None)

            if index_ff:

                ltpc = getattr(index_ff, "ltpc", None)

                if ltpc:
                    return float(ltpc.ltp)

    except Exception:
        pass

    return None