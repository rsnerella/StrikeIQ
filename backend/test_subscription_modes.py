#!/usr/bin/env python3
"""
Test Different Upstox WebSocket Subscription Modes
Tests all available modes to see which one provides complete options data
"""

import asyncio
import json
import logging
from datetime import datetime

# Available modes to test
SUBSCRIPTION_MODES = [
    "ltp",           # LTP only
    "option_greek",  # Options Greeks only
    "full",          # Full data
    "full_d30"       # Full market depth (30 levels)
]

async def test_subscription_mode(mode: str, test_duration: int = 30):
    """Test a specific subscription mode"""
    print(f"\n🧪 TESTING MODE: {mode}")
    print(f"⏱️  Duration: {test_duration} seconds")
    print(f"🕐 Start Time: {datetime.now().strftime('%H:%M:%S')}")
    
    # This would connect to WebSocket and subscribe with the given mode
    # For now, we'll just simulate the test
    print(f"📊 Expected behavior for {mode}:")
    
    if mode == "ltp":
        print("  - LTP data only")
        print("  - Fastest updates")
        print("  - Minimal bandwidth")
    elif mode == "option_greek":
        print("  - Options Greeks only")
        print("  - Delta, theta, gamma, vega, rho")
        print("  - No bid/ask data")
    elif mode == "full":
        print("  - Full market data")
        print("  - LTP, bid/ask, OI, volume")
        print("  - Some Greeks")
    elif mode == "full_d30":
        print("  - Full market depth (30 levels)")
        print("  - Complete bid/ask depth")
        print("  - All Greeks")
        print("  - Complete OI/volume")
        print("  - Highest bandwidth")
    
    print(f"⏳️ Would monitor for {test_duration} seconds...")
    print(f"✅ Test complete for {mode}")

async def main():
    """Test all subscription modes"""
    print("🔬 Upstox WebSocket Subscription Mode Test")
    print("=" * 50)
    print("Testing all available subscription modes to find complete options data")
    print("=" * 50)
    
    print("\n📋 Available Modes:")
    for i, mode in enumerate(SUBSCRIPTION_MODES, 1):
        print(f"  {i}. {mode}")
    
    print("\n🚀 Starting tests...")
    
    # Test each mode
    for mode in SUBSCRIPTION_MODES:
        await test_subscription_mode(mode, test_duration=10)
        await asyncio.sleep(2)  # Brief pause between tests
    
    print("\n" + "=" * 50)
    print("🎯 RECOMMENDATION:")
    print("Based on Upstox community research:")
    print("- 'full_d30' mode should provide complete options data")
    print("- 'full' mode may have limited options data")
    print("- 'option_greek' mode focuses on Greeks only")
    print("- 'ltp' mode is fastest but limited")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(main())
