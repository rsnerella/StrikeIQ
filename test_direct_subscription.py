#!/usr/bin/env python3
"""
Direct test of Upstox subscription mode
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

try:
    # Direct import to avoid cache issues
    import importlib
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), 'backend', 'app', 'services'))
    
    # Reload module to get latest changes
    import upstox_market_feed
    importlib.reload(upstox_market_feed)
    
    from upstox_market_feed import FeedConfig
    
    config = FeedConfig(
        symbol="NIFTY",
        spot_instrument_key="NSE_INDEX|Nifty 50",
        mode="full"  # This should read the updated value
    )
    
    print("🔧 DIRECT Upstox Subscription Test")
    print("✅ Feed Configuration:")
    print(f"   Symbol: {config.symbol}")
    print(f"   Mode: {config.mode}")
    print(f"   Strike Range: {config.strike_range}")
    
    if config.mode == "option_chain":
        print("✅ Subscription mode is option_chain - SHOULD RECEIVE OI DATA")
    elif config.mode == "full":
        print("⚠️  Subscription mode is full - LTPC feed (NO OI)")
    else:
        print(f"❌ Unknown subscription mode: {config.mode}")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
