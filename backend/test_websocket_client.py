#!/usr/bin/env python3
"""
Simple WebSocket client to test analytics_update messages
"""

import asyncio
import websockets
import json

async def test_websocket_client():
    """Connect to WebSocket and listen for analytics_update messages"""
    
    uri = "ws://localhost:8000/ws/market"
    
    try:
        print("🔌 Connecting to WebSocket...")
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to WebSocket")
            
            # Send subscription message
            subscribe_msg = {
                "type": "subscribe",
                "symbol": "NIFTY",
                "expiry": "current"
            }
            await websocket.send(json.dumps(subscribe_msg))
            print("📡 Sent subscription message")
            
            # Listen for messages
            print("👂 Listening for messages...")
            message_count = 0
            
            async for message in websocket:
                message_count += 1
                data = json.loads(message)
                
                print(f"\n📨 Message #{message_count}:")
                print(f"Type: {data.get('type')}")
                
                # Check for analytics_update messages
                if data.get('type') == 'analytics_update':
                    analytics = data.get('analytics', {})
                    print(f"🎯 ANALYTICS_UPDATE RECEIVED!")
                    print(f"Strategy: {analytics.get('strategy')}")
                    print(f"Confidence: {analytics.get('confidence')}")
                    print(f"Bias: {analytics.get('bias')}")
                    
                    # Check if our debug injection worked
                    if analytics.get('strategy') == 'DEBUG_SELL' and analytics.get('confidence') == 0.99:
                        print("✅ SUCCESS: Wrapper injection working!")
                        break
                    else:
                        print("❌ ISSUE: Strategy/confidence not injected correctly")
                
                # Stop after 20 messages if no analytics_update found
                if message_count >= 20:
                    print("⏰ Timeout: No analytics_update received in 20 messages")
                    break
                    
    except Exception as e:
        print(f"❌ WebSocket error: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket_client())
