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

        if not hasattr(response, "feeds"):
            return []

        feeds = getattr(response, "feeds", None)
        
        if not feeds:
            return []
        
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

        for instrument_key, feed in feed_items:

            logger.info(f"DEBUG FEED LOOP → {instrument_key}")

            if not instrument_key:
                continue

            logger.info("DEBUG PROCESSING TICK → %s", instrument_key)

            if not instrument_key:
                continue

            # STEP 1: Detect instrument type
            instrument_key = instrument_key.upper()
            is_index = instrument_key.startswith("NSE_INDEX")

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
                # STEP 2: Fix feed type routing using WhichOneof
                ff = getattr(feed, "ff", None)
                
                if ff:
                    # Determine feed type using WhichOneof
                    feed_type = ff.WhichOneof("feedUnion")
                    
                    if feed_type == "marketFF":
                        market_ff = ff.marketFF
                        index_ff = None
                        
                    elif feed_type == "indexFF":
                        index_ff = ff.indexFF
                        market_ff = None
                    else:
                        # Unknown feed type, skip
                        continue

                    if market_ff:
                        # STEP 2: Handle marketFF safely with instrument type detection
                        if market_ff.ltpc:
                            ltp = market_ff.ltpc.ltp

                            logger.info(f"TICK PARSED → {instrument_key} LTP={ltp}")

                        # Only options/equities contain OI
                        if not is_index and market_ff.optionGreeks:
                            oi = market_ff.optionGreeks.oi

                        if not is_index and market_ff.marketOHLC:
                            volume = market_ff.marketOHLC.volume

                        # MARKETFF INDEX TICK HANDLING - SAFE EXTRACTION
                        if is_index and hasattr(feed, "ff") and feed.ff:
                            market_ff = getattr(feed.ff, "marketFF", None)

                            if market_ff and market_ff.ltpc and market_ff.ltpc.ltp:
                                ltp = market_ff.ltpc.ltp

                                tick = {
                                    "instrument_key": instrument_key,
                                    "ltp": float(ltp),
                                    "oi": 0,
                                    "volume": 0,
                                    "timestamp": time.time()
                                }

                                ticks.append(tick)

                    elif index_ff:
                        # STEP 3: Keep indexFF support for compatibility
                        logger.info(f"DEBUG INDEX BLOCK ENTERED → {instrument_key}")
                        
                        if index_ff.ltpc:
                            ltp = index_ff.ltpc.ltp
                            logger.info(f"TICK PARSED → {instrument_key} LTP={ltp}")
                            logger.info(f"DEBUG LTP EXTRACTED → {instrument_key} {ltp}")


            except Exception:
                pass

            # =================================================
            # ROUTE INDEX TICKS IMMEDIATELY AFTER LTP EXTRACTION
            # =================================================

            if ltp is not None:
                logger.info(f"TICK PARSED → {instrument_key} LTP={ltp}")

                logger.info(f"DEBUG ROUTING CHECK → {instrument_key}")


            # =================================================
            # DROP INVALID TICKS
            # =================================================

            if ltp is None or ltp <= 0:
                continue

            # STEP 5: Output structure with safe float conversion
            tick = {
                "instrument_key": instrument_key,
                "ltp": float(ltp) if ltp else None,
                "oi": oi,
                "volume": volume,
                "timestamp": time.time()
            }

            ticks.append(tick)

            # -------------------------------------------------
            # LOGGING - STEP 6: Add unified debug logging
            # -------------------------------------------------

            logger.info(
                f"TICK PARSED → {instrument_key} LTP={ltp} OI={oi} VOL={volume}"
            )

            # -------------------------------------------------
            # INDEX TICK ROUTING
            # -------------------------------------------------


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
            # Use WhichOneof for feed type determination
            feed_type = ff.WhichOneof("feedUnion")
            
            if feed_type == "indexFF":
                index_ff = ff.indexFF
                if hasattr(index_ff, "ltpc") and index_ff.ltpc:
                    return float(index_ff.ltpc.ltp)
                    
            elif feed_type == "marketFF":
                market_ff = ff.marketFF
                if hasattr(market_ff, "ltpc") and market_ff.ltpc:
                    return float(market_ff.ltpc.ltp)

    except Exception:
        pass

    return None