"""
Upstox V3 Raw Feed Converter
Converts protobuf messages to exact Upstox V3 JSON format
"""

import json
import time
import logging
from typing import Dict, Any, List
from google.protobuf.json_format import MessageToJson
from app.proto.MarketDataFeedV3_pb2 import FeedResponse
from app.services.options_data_enricher import options_enricher

logger = logging.getLogger(__name__)


async def convert_protobuf_to_upstox_v3_format(message: bytes) -> Dict[str, Any]:
    """
    Convert protobuf message to exact Upstox V3 JSON format
    
    Args:
        message: Raw protobuf binary message
        
    Returns:
        Dictionary in exact Upstox V3 format
    """
    try:
        # Parse protobuf message
        feed_response = FeedResponse()
        feed_response.ParseFromString(message)
        
        # Get current timestamp in milliseconds
        current_ts = str(int(time.time() * 1000))
        
        # Build the response structure
        result = {
            "type": "live_feed",
            "feeds": {},
            "currentTs": current_ts
        }
        
        # Process each feed
        if feed_response.feeds:
            for feed_entry in feed_response.feeds:
                feed_key = feed_entry.key
                feed_value = feed_entry.value
                
                feed_dict = {}
                
                # Convert feed to dictionary using protobuf's JSON converter
                try:
                    feed_json = MessageToJson(feed_value)
                    feed_data = json.loads(feed_json)
                    
                    # Build the fullFeed structure based on actual data
                    full_feed = {"fullFeed": {}}
                    
                    # Handle different feed types
                    if "ff" in feed_data:
                        ff_data = feed_data["ff"]
                        
                        # Market feed (complete data) - PASS THROUGH DIRECTLY
                        if "marketFF" in ff_data:
                            market_ff = ff_data["marketFF"]
                            full_feed["fullFeed"]["marketFF"] = market_ff
                            logger.info(f"RAW CONVERTER: PASSING THROUGH REAL MARKETFF DATA for {feed_key}")
                        
                        # Index feed (limited data) - PASS THROUGH DIRECTLY
                        elif "indexFF" in ff_data:
                            index_ff = ff_data["indexFF"]
                            full_feed["fullFeed"]["indexFF"] = index_ff
                            logger.info(f"RAW CONVERTER: PASSING THROUGH REAL INDEXFF DATA for {feed_key}")
                        
                        else:
                            logger.warning(f"RAW CONVERTER: Unknown feed type in {feed_key}: {list(ff_data.keys())}")
                            full_feed["fullFeed"] = ff_data
                            
                    # Direct LTPC feed
                    elif "ltpc" in feed_data:
                        full_feed["fullFeed"]["marketFF"] = {
                            "ltpc": feed_data["ltpc"]
                        }
                    
                    feed_dict = full_feed
                    
                except Exception as e:
                    logger.error(f"Failed to convert feed {feed_key} to JSON: {e}")
                    continue
                
                # Add to feeds
                result["feeds"][feed_key] = feed_dict
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to convert protobuf to Upstox V3 format: {e}")
        # Return empty structure on error
        return {
            "type": "live_feed",
            "feeds": {},
            "currentTs": str(int(time.time() * 1000))
        }


def extract_market_data_from_upstox_v3(upstox_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract market data from Upstox V3 format for internal processing
    
    Args:
        upstox_data: Upstox V3 format data
        
    Returns:
        List of normalized market data ticks
    """
    ticks = []
    
    try:
        feeds = upstox_data.get("feeds", {})
        
        for instrument_key, feed_data in feeds.items():
            full_feed = feed_data.get("fullFeed", {})
            
            # Handle marketFF (options/equities)
            if "marketFF" in full_feed:
                market_ff = full_feed["marketFF"]
                tick = _extract_tick_from_market_ff(instrument_key, market_ff)
                if tick:
                    ticks.append(tick)
            
            # Handle indexFF (indices)
            elif "indexFF" in full_feed:
                index_ff = full_feed["indexFF"]
                tick = _extract_tick_from_index_ff(instrument_key, index_ff)
                if tick:
                    ticks.append(tick)
    
    except Exception as e:
        logger.error(f"Failed to extract market data from Upstox V3 format: {e}")
    
    return ticks


def _extract_tick_from_market_ff(instrument_key: str, market_ff: Dict[str, Any]) -> Dict[str, Any]:
    """Extract tick data from marketFF structure"""
    
    tick = {
        "instrument_key": instrument_key,
        "type": "option" if "NSE_FO" in instrument_key else "equity",
        "data": {}
    }
    
    # Extract LTPC data
    ltpc = market_ff.get("ltpc", {})
    if ltpc:
        tick["data"].update({
            "ltp": float(ltpc.get("ltp", 0)),
            "ltt": ltpc.get("ltt"),
            "ltq": ltpc.get("ltq"),
            "cp": float(ltpc.get("cp", 0))
        })
    
    # Extract OI data
    tick["data"]["oi"] = int(market_ff.get("oi", 0))
    
    # Extract volume from marketOHLC
    market_ohlc = market_ff.get("marketOHLC", {})
    if market_ohlc and "ohlc" in market_ohlc:
        ohlc_data = market_ohlc["ohlc"]
        if ohlc_data and len(ohlc_data) > 0:
            tick["data"]["volume"] = int(ohlc_data[0].get("vol", 0))
    
    # Extract bid/ask from marketLevel
    market_level = market_ff.get("marketLevel", {})
    if "bidAskQuote" in market_level:
        bid_ask_quotes = market_level["bidAskQuote"]
        if bid_ask_quotes and len(bid_ask_quotes) > 0:
            first_quote = bid_ask_quotes[0]
            tick["data"].update({
                "bid": float(first_quote.get("bidP", 0)),
                "ask": float(first_quote.get("askP", 0)),
                "bid_qty": int(first_quote.get("bidQ", 0)),
                "ask_qty": int(first_quote.get("askQ", 0))
            })
    
    # Extract Greeks
    option_greeks = market_ff.get("optionGreeks", {})
    if option_greeks:
        tick["data"].update({
            "delta": float(option_greeks.get("delta", 0)),
            "theta": float(option_greeks.get("theta", 0)),
            "gamma": float(option_greeks.get("gamma", 0)),
            "vega": float(option_greeks.get("vega", 0)),
            "rho": float(option_greeks.get("rho", 0))
        })
    
    # Extract additional fields
    tick["data"].update({
        "atp": float(market_ff.get("atp", 0)),
        "vtt": int(market_ff.get("vtt", 0)),
        "iv": float(market_ff.get("iv", 0)),
        "tbq": int(market_ff.get("tbq", 0)),
        "tsq": int(market_ff.get("tsq", 0))
    })
    
    return tick


def _extract_tick_from_index_ff(instrument_key: str, index_ff: Dict[str, Any]) -> Dict[str, Any]:
    """Extract tick data from indexFF structure"""
    
    tick = {
        "instrument_key": instrument_key,
        "type": "index",
        "data": {}
    }
    
    # Extract LTPC data
    ltpc = index_ff.get("ltpc", {})
    if ltpc:
        tick["data"].update({
            "ltp": float(ltpc.get("ltp", 0)),
            "ltt": ltpc.get("ltt"),
            "ltq": ltpc.get("ltq"),
            "cp": float(ltpc.get("cp", 0))
        })
    
    return tick
