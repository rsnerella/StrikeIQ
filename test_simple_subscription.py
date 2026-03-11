#!/usr/bin/env python3
"""
Simple test to check Upstox subscription mode
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

try:
    from app.services.upstox_market_feed import FeedConfig
    
    config = FeedConfig(
        symbol="NIFTY",
        spot_instrument_key="NSE_INDEX|Nifty 50",
        mode="full"
    )
    
    print("✅ Upstox Feed Configuration:")
    print(f"   Symbol: {config.symbol}")
    print(f"   Mode: {config.mode}")
    print(f"   Strike Range: {config.strike_range}")
    
    if config.mode == "full":
        print("✅ Subscription mode is CORRECT - should receive OI data")
    else:
        print(f"❌ Subscription mode is WRONG: {config.mode}")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
