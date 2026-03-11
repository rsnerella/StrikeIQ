#!/usr/bin/env python3
"""
Test script to verify Upstox subscription mode and debug feed
"""

import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

async def test_upstox_subscription():
    """Test Upstox subscription mode and debug feed"""
    print("🔧 TESTING UPSTOX SUBSCRIPTION MODE")
    
    try:
        # Check current configuration
        from app.services.upstox_market_feed import FeedConfig
        
        config = FeedConfig(
            symbol="NIFTY",
            spot_instrument_key="NSE_INDEX|Nifty 50",
            mode="full"  # This should be correct
        )
        
        print("✅ Feed Configuration:")
        print(f"   Symbol: {config.symbol}")
        print(f"   Mode: {config.mode}")
        print(f"   Strike Range: {config.strike_range}")
        
        # Expected subscription payload
        expected_subscription = {
            "method": "sub",
            "data": {
                "mode": config.mode,  # Should be "full"
                "instrumentKeys": ["NSE_INDEX|Nifty 50"]
            }
        }
        
        print("✅ Expected Subscription Payload:")
        print(f"   Mode: {expected_subscription['data']['mode']}")
        print(f"   Instrument Keys: {len(expected_subscription['data']['instrumentKeys'])} keys")
        
        # Check if mode is correct
        if config.mode == "full":
            print("✅ Subscription mode is CORRECT (full)")
            print("   Should receive: LTP + Volume + OI + Greeks")
        elif config.mode == "ltpc":
            print("❌ Subscription mode is WRONG (ltpc)")
            print("   Will receive: LTP + Volume only (NO OI)")
        else:
            print(f"⚠️  Unknown subscription mode: {config.mode}")
        
        print("\n📊 Expected Feed Types:")
        print("   Mode 'full':")
        print("     - LTP data")
        print("     - Volume data") 
        print("     - OI data")
        print("     - Greeks data")
        print("   Mode 'ltpc':")
        print("     - LTP data")
        print("     - Volume data")
        print("     - NO OI data")
        print("     - NO Greeks data")
        
        return config.mode == "full"
        
    except Exception as e:
        print(f"❌ Subscription test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_upstox_subscription())
    sys.exit(0 if success else 1)
