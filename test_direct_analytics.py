#!/usr/bin/env python3
"""
Direct test of analytics broadcaster without WebSocket
"""

import asyncio
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from app.services.analytics_broadcaster import analytics_broadcaster
from app.core.ws_manager import manager

async def test_direct_analytics():
    """Test analytics broadcaster directly"""
    
    print("🧪 Direct Analytics Broadcaster Test")
    print("=" * 50)
    
    try:
        # Check WebSocket manager connections
        print(f"🔌 Active WebSocket connections: {len(manager.active_connections)}")
        
        # Mock a WebSocket connection to trigger the broadcaster
        print("🎭 Creating mock WebSocket connection...")
        
        # Simulate the broadcaster loop manually
        print("🔄 Manually running analytics computation...")
        
        # Set dirty flag for NIFTY
        analytics_broadcaster._dirty["NIFTY"] = True
        analytics_broadcaster._last_broadcast_time["NIFTY"] = 0
        
        # Manually call compute and broadcast
        await analytics_broadcaster._compute_and_broadcast("NIFTY")
        
        print("✅ Direct test completed")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_direct_analytics())
