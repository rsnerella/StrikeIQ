#!/usr/bin/env python3
"""
Simple WebSocket client to test message reception
"""

import asyncio
import websockets
import json

async def test_websocket():
    uri = "ws://localhost:8000/ws"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to WebSocket")
            
            # Send subscription message
            subscribe_msg = {
                "type": "subscribe",
                "symbol": "NIFTY",
                "expiry": "current"
            }
            await websocket.send(json.dumps(subscribe_msg))
            print(f"📤 Sent subscription: {subscribe_msg}")
            
            # Wait for messages
            print("⏳ Waiting for messages...")
            try:
                while True:
                    message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    data = json.loads(message)
                    print(f"📥 Received: {data}")
                    
                    # Check if it's the tick message we expect
                    if data.get("type") == "tick" and "ltp" in data:
                        print(f"✅ SUCCESS: Received tick message with LTP={data['ltp']}")
                        break
                        
            except asyncio.TimeoutError:
                print("⏰ Timeout - no messages received")
                
    except Exception as e:
        print(f"❌ WebSocket error: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket())
