#!/usr/bin/env python3
"""
Test script to capture and analyze raw protobuf data from Upstox
"""

import asyncio
import logging
import json
from google.protobuf.json_format import MessageToJson
from app.proto.MarketDataFeedV3_pb2 import FeedResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def analyze_protobuf_structure(raw_data: bytes):
    """Analyze the raw protobuf data structure"""
    
    try:
        # Parse with current proto definition
        feed_response = FeedResponse()
        feed_response.ParseFromString(raw_data)
        
        # Convert to JSON to see structure
        feed_json = MessageToJson(feed_response)
        
        print("=== PROTOBUF STRUCTURE ANALYSIS ===")
        print(f"Feed Type: {feed_response.type}")
        print(f"Number of feeds: {len(feed_response.feeds)}")
        
        for i, feed_entry in enumerate(feed_response.feeds):
            print(f"\n--- Feed {i+1} ---")
            print(f"Instrument Key: {feed_entry.key}")
            
            # Convert individual feed to JSON
            feed_json = MessageToJson(feed_entry.value)
            print(f"Feed Data: {feed_json}")
            
            # Try to access different data types
            feed_value = feed_entry.value
            
            if feed_value.HasField("ltpc"):
                print(f"LTPC available: ltp={feed_value.ltpc.ltp}")
            
            if feed_value.HasField("ff"):
                ff = feed_value.ff
                ff_type = ff.WhichOneof("data")
                print(f"FF Type: {ff_type}")
                
                if ff_type == "marketFF":
                    market = ff.marketFF
                    print(f"MarketFF fields available: {[field.name for field in market.DESCRIPTOR.fields]}")
                    
                    # Check what fields actually have data
                    if market.HasField("marketLevel"):
                        level = market.marketLevel
                        print(f"MarketLevel: bid={level.bid}, ask={level.ask}")
                    
                    if market.HasField("eFeedDetails"):
                        details = market.eFeedDetails
                        print(f"EFeedDetails: oi={details.openInterest}, volume={details.volume}")
                        
                elif ff_type == "indexFF":
                    index = ff.indexFF
                    if index.HasField("ltpc"):
                        print(f"Index LTP: {index.ltpc.ltp}")
        
        print("=== END ANALYSIS ===")
        
    except Exception as e:
        print(f"Error analyzing protobuf: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("Protobuf Structure Analyzer Ready")
    print("This will analyze raw protobuf data when available")
    print("Use this to understand the actual data structure from Upstox")
