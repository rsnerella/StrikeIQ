import logging
from typing import List, Dict
from app.services.MarketDataFeedV3_pb2 import FeedResponse, FeedData

logger = logging.getLogger(__name__)


def decode_protobuf_message_v3(message):

    try:

        decoded = FeedResponse()
        decoded.ParseFromString(message)

        logger.info(f"PROTOBUF FEEDS COUNT = {len(decoded.feeds)}")

        if not decoded.feeds:
            logger.debug("UPSTOX HEARTBEAT RECEIVED")
            return []

        ticks = []

        for feed_data in decoded.feeds:

            logger.info(f"FEED KEY = {feed_data.instrumentKey}")
            logger.info(f"FEED OBJECT = {feed_data}")

            # Check feed structure
            if hasattr(feed_data, 'ltpc') and feed_data.ltpc:
                logger.info("LTPC FEED DETECTED")
                ltp = feed_data.ltpc.ltp
            elif hasattr(feed_data, 'ff') and feed_data.ff:
                if hasattr(feed_data.ff, 'indexFF') and feed_data.ff.indexFF:
                    logger.info("INDEX FEED DETECTED")
                    ltp = feed_data.ff.indexFF.ltpc.ltp
                elif hasattr(feed_data.ff, 'marketFF') and feed_data.ff.marketFF:
                    logger.info("OPTION FEED DETECTED")
                    ltp = feed_data.ff.marketFF.ltpc.ltp
                else:
                    logger.info("UNKNOWN FEED STRUCTURE")
                    continue
            else:
                logger.info("❌ NO RECOGNIZED STRUCTURE (NEITHER LTPC NOR FULL)")
                continue

            # Only process feeds with valid LTP
            if ltp <= 0:
                logger.info(f"INVALID LTP = {ltp}, SKIPPING")
                continue

            # Create tick based on instrument type
            if "NSE_INDEX" in feed_data.instrumentKey:
                # Index tick
                tick = {
                    "type": "index_tick",
                    "instrument": feed_data.instrumentKey,
                    "ltp": float(ltp),
                    "oi": int(feed_data.oi) if hasattr(feed_data, 'oi') else 0,
                    "volume": int(feed_data.volume) if hasattr(feed_data, 'volume') else 0
                }
            else:
                # Option tick
                tick = {
                    "type": "option_tick",
                    "instrument": feed_data.instrumentKey,
                    "ltp": float(ltp),
                    "oi": int(feed_data.oi) if hasattr(feed_data, 'oi') else 0,
                    "volume": int(feed_data.volume) if hasattr(feed_data, 'volume') else 0
                }

            ticks.append(tick)

        logger.info(f"TICKS EXTRACTED = {len(ticks)}")

        return ticks

    except Exception as e:

        logger.error(f"PROTOBUF V3 DECODE ERROR: {e}")
        return []


def decode_protobuf_message(message):
    """
    Decode Upstox V3 protobuf format following official documentation
    FeedResponse -> feeds -> Feed -> ff -> indexFF/marketFF -> ltpc -> ltp
    """
    
    try:
        from app.proto.MarketDataFeed_pb2 import FeedResponse
        decoded = FeedResponse()
        decoded.ParseFromString(message)

        logger.info(f"=== PROTOBUF V3 PARSING ===")
        logger.info(f"RAW PACKET SIZE = {len(message)}")
        logger.info(f"MESSAGE TYPE = {type(message)}")
        logger.info(f"FEEDS COUNT = {len(decoded.feeds)}")
        
        # Log FeedResponse type for debugging
        if hasattr(decoded, 'type') and decoded.type:
            logger.info(f"FEEDRESPONSE TYPE = {decoded.type}")
        
        # Log timestamp if available
        if hasattr(decoded, 'timestamp') and decoded.timestamp:
            logger.info(f"TIMESTAMP = {decoded.timestamp}")

        # Detect heartbeat packets (STEP 6)
        if (hasattr(decoded, 'type') and decoded.type == 2) or (len(decoded.feeds) == 0 and len(message) < 200):
            logger.debug("Heartbeat packet")
            return []

        ticks = []

        for instrument_key, feed in decoded.feeds.items():
            
            logger.info(f"--- PROCESSING FEED ---")
            logger.info(f"INSTRUMENT KEY = {instrument_key}")
            logger.info(f"FEED TYPE = {type(feed)}")
            
            # Create base tick
            tick = {
                "type": "option_tick",
                "instrument": instrument_key,
                "ltp": 0,
                "oi": 0,
                "volume": 0
            }

            # Support BOTH ltpc mode and full mode structures
            
            # LTPC MODE: Direct access to ltpc
            if feed.HasField("ltpc") and feed.ltpc:
                logger.info("")
                ltpc = feed.ltpc
                if hasattr(ltpc, "ltp"):
                    tick["ltp"] = float(ltpc.ltp)
                    tick["type"] = "index_tick" if "INDEX" in instrument_key else "option_tick"
                    logger.info(f" LTPC MODE LTP EXTRACTED = {tick['ltp']}")
                else:
                    logger.info(" NO LTP IN DIRECT LTPC")
            
            # FULL MODE: Access through ff wrapper
            elif feed.HasField("ff") and feed.ff:
                ff = feed.ff
                logger.info("")
                
                # Index feed for indices (NSE_INDEX)
                if ff.HasField("indexFF") and ff.indexFF:
                    logger.info("")
                    index_ff = ff.indexFF
                    
                    if hasattr(index_ff, "ltpc") and index_ff.ltpc:
                        ltpc = index_ff.ltpc
                        if hasattr(ltpc, "ltp"):
                            tick["ltp"] = float(ltpc.ltp)
                            tick["type"] = "index_tick"
                            logger.info(f" FULL MODE INDEX LTP EXTRACTED = {tick['ltp']}")
                        else:
                            logger.info(" NO LTP IN INDEX LTPC")
                    else:
                        logger.info(" NO LTPC IN INDEX FF")
                
                # Market feed for options (NSE_FO)
                elif ff.HasField("marketFF") and ff.marketFF:
                    logger.info("")
                    market_ff = ff.marketFF
                    
                    if hasattr(market_ff, "ltpc") and market_ff.ltpc:
                        ltpc = market_ff.ltpc
                        if hasattr(ltpc, "ltp"):
                            tick["ltp"] = float(ltpc.ltp)
                            tick["type"] = "option_tick"
                            logger.info(f" FULL MODE MARKET LTP EXTRACTED = {tick['ltp']}")
                        else:
                            logger.info(" NO LTP IN MARKET LTPC")
                    else:
                        logger.info(" NO LTPC IN MARKET FF")
                
                else:
                    logger.info(" NO INDEXFF OR MARKETFF IN FF")
            
            else:
                logger.info(" NO RECOGNIZED STRUCTURE (NEITHER LTPC NOR FULL)")
                # Log all available attributes for debugging
                logger.info(f"AVAILABLE ATTRIBUTES: {[attr for attr in dir(feed) if not attr.startswith('_')]}")

            # Only add if valid LTP
            if tick["ltp"] > 0:
                logger.info(f"TICK RECEIVED → {instrument_key} : {tick['ltp']}")
                ticks.append(tick)
                logger.info(f"🎯 VALID TICK ADDED: {instrument_key} = {tick['ltp']}")
            else:
                logger.info(f"❌ INVALID LTP = {tick['ltp']}, SKIPPING {instrument_key}")

        logger.info(f"=== FINAL RESULTS ===")
        logger.info(f"TICKS EXTRACTED = {len(ticks)}")
        
        for tick in ticks:
            logger.info(f"📊 TICK: {tick['instrument']} = {tick['ltp']} ({tick['type']})")

        return ticks

    except Exception as e:
        logger.error(f"❌ PROTOBUF V3 DECODE ERROR: {e}")
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
