#!/usr/bin/env python3
"""
Continuous analytics_update test to trigger UI updates
"""

import asyncio
import sys
import os
import time

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.ws_manager import broadcast_with_strategy

async def continuous_analytics_test():
    """Send continuous analytics_update messages to test UI"""
    
    count = 0
    while count < 5:  # Send 5 messages
        count += 1
        
        # Create test analytics_update payload
        test_payload = {
            "type": "analytics_update",
            "symbol": "NIFTY",
            "timestamp": int(time.time() * 1000),
            "analytics": {
                "bias": "BULLISH" if count % 2 == 0 else "BEARISH",
                "bias_strength": 0.65 + (count * 0.05),
                "regime": "RANGING",
                "strategy": f"TEST_STRATEGY_{count}",
                "confidence": 0.80 + (count * 0.02)
            }
        }
        
        print(f"🧪 SENDING ANALYTICS_UPDATE #{count}")
        print("=" * 50)
        print("PAYLOAD:", test_payload)
        print()
        
        # Send through wrapper
        await broadcast_with_strategy(test_payload)
        
        print(f"✅ SENT MESSAGE #{count}")
        print("Waiting 2 seconds...")
        print()
        
        await asyncio.sleep(2)
    
    print("🎯 TEST COMPLETE - Check browser UI for strategy updates")

if __name__ == "__main__":
    asyncio.run(continuous_analytics_test())
