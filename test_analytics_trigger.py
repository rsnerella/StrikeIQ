#!/usr/bin/env python3
"""
Test to trigger analytics broadcaster manually
"""

import asyncio
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from app.services.analytics_broadcaster import analytics_broadcaster

async def test_manual_trigger():
    """Manually trigger the analytics broadcaster"""
    
    print("🧪 Testing Analytics Broadcaster Manual Trigger")
    print("=" * 50)
    
    try:
        # Start the broadcaster
        print("🚀 Starting analytics broadcaster...")
        await analytics_broadcaster.start()
        
        # Wait a bit to see if it processes
        print("⏳ Waiting 5 seconds for processing...")
        await asyncio.sleep(5)
        
        # Stop the broadcaster
        print("🛑 Stopping analytics broadcaster...")
        await analytics_broadcaster.stop()
        
        print("✅ Test completed")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_manual_trigger())
