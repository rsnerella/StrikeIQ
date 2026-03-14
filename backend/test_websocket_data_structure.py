#!/usr/bin/env python3
"""
Test WebSocket Data Structure
Analyze what data is actually available in Upstox WebSocket feeds
"""

import asyncio
import json
import logging
from google.protobuf.json_format import MessageToJson

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_websocket_data_structure():
    """Test and analyze WebSocket data structure"""
    
    print("🔍 WEBSOCKET DATA STRUCTURE ANALYSIS")
    print("=" * 50)
    
    print("\n📋 PROTOBUF DEFINITION ANALYSIS:")
    print("MarketFF fields that SHOULD contain complete options data:")
    print("- ltpc: LTP and change price")
    print("- marketLevel: BidAskQuote array (bid/ask with quantities)")
    print("- optionGreeks: delta, theta, gamma, vega, rho")
    print("- marketOHLC: OHLC array with volume")
    print("- atp: Average trade price")
    print("- vtt: Volume traded today")
    print("- oi: Open interest")
    print("- iv: Implied volatility")
    print("- tbq: Total bid quantity")
    print("- tsq: Total sell quantity")
    
    print("\n📊 CURRENT ISSUE:")
    print("- Options coming as IndexFF instead of MarketFF")
    print("- IndexFF only contains ltpc field")
    print("- Missing bid/ask/OI/volume/greeks from WebSocket")
    
    print("\n🔧 POSSIBLE SOLUTIONS:")
    print("1. Check if Upstox subscription mode needs to be changed")
    print("2. See if there are additional fields in IndexFF we're missing")
    print("3. Check if options should be subscribed differently")
    print("4. Verify if MarketFF data is available but not being parsed")
    
    print("\n📝 EXPECTED LOGS TO LOOK FOR:")
    print("DEBUG INDEX ALL FIELDS: [list of available fields]")
    print("DEBUG INDEX FIELD ltpc: {ltp: 143.55, cp: 234.9, ltt: '1000', ltq: '500'}")
    print("DEBUG LTPC DATA: {ltp: 143.55, cp: 234.9, ltt: '1000', ltq: '500'}")
    
    print("\n🎯 IF WE FIND ADDITIONAL FIELDS:")
    print("- ltt: Last trade time (could contain volume)")
    print("- ltq: Last trade quantity (could contain volume)")
    print("- cp: Change price (could contain OI change)")
    print("- Any other fields with market data")
    
    print("\n⚡ NEXT STEPS:")
    print("1. Run the system and check the debug logs")
    print("2. Look for 'DEBUG INDEX ALL FIELDS' output")
    print("3. Analyze if any fields contain bid/ask/OI/volume")
    print("4. Update parser to extract available data")
    print("5. If no additional data, consider subscription changes")

if __name__ == "__main__":
    asyncio.run(test_websocket_data_structure())
