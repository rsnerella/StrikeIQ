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
            oi: int = 0
            volume: int = 0

            # =================================================
            # PRIMARY LTP EXTRACTION
            # =================================================

            try:
                if feed.HasField("ltpc"):
                    ltp = float(feed.ltpc.ltp)
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
                        ltp = float(index_ff.ltpc.ltp)

                    # market feed
                    market_ff = getattr(ff, "marketFF", None)

                    if market_ff:

                        if market_ff.HasField("ltpc"):
                            ltp = float(market_ff.ltpc.ltp)

                        # nested fullFeed structure
                        full = getattr(market_ff, "fullFeed", None)
                        if full and full.HasField("ltpc"):
                            ltp = float(full.ltpc.ltp)

                        # volume and OI extraction from eFeedDetails
                        try:
                            if hasattr(market_ff, "eFeedDetails"):
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
                logger.debug(
                    f"OPTION TICK → {instrument_key} LTP={ltp} OI={oi} VOL={volume}"
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
                return float(index_ff.ltpc.ltp)

            market_ff = getattr(ff, "marketFF", None)
            if market_ff and market_ff.HasField("ltpc"):
                return float(market_ff.ltpc.ltp)

    except Exception:
        pass

    return None