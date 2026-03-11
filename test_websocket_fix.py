#!/usr/bin/env python3
"""
Test script to verify the protobuf parser fixes
"""

import asyncio
import websockets
import json
import time

async def test_websocket_connection():
    """Test WebSocket connection and verify expected log patterns"""
    
    try:
        # Connect to WebSocket
        uri = "ws://localhost:8000/ws/market"
        print(f"Connecting to {uri}...")
        
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket connected")
            
            # Send subscription message
            subscribe_msg = {
                "type": "subscribe",
                "symbol": "NIFTY",
                "expiry": "current"
            }
            
            await websocket.send(json.dumps(subscribe_msg))
            print("✅ Subscription sent")
            
            # Listen for messages
            timeout = 30  # 30 seconds timeout
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    data = json.loads(message)
                    
                    print(f"📨 Received: {data.get('type', 'unknown')} - {data}")
                    
                    # Check for expected patterns
                    if data.get('type') == 'market_status':
                        print("✅ Market status received")
                    
                    elif data.get('type') == 'index_tick':
                        print("✅ Index tick received - FIX 1 working!")
                        return True
                        
                except asyncio.TimeoutError:
                    print("⏳ Waiting for messages...")
                    continue
                except Exception as e:
                    print(f"❌ Error receiving message: {e}")
                    break
            
            print("⚠️ Timeout reached - no index ticks received")
            return False
            
    except Exception as e:
        print(f"❌ WebSocket connection failed: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_websocket_connection())
