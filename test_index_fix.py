#!/usr/bin/env python3
"""
Test script to verify index update broadcast format
"""
import asyncio
import websockets
import json

async def test_websocket():
    uri = "ws://localhost:8000/ws/market"
    
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
            print(f"📤 Sent: {subscribe_msg}")
            
            # Listen for messages
            while True:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=10)
                    data = json.loads(message)
                    
                    print(f"📥 Received: {data}")
                    
                    # Check for our expected format
                    if data.get("type") == "index_update":
                        print(f"🎯 SUCCESS! Got index_update: {data}")
                        if "ltp" in data and "symbol" in data:
                            print(f"✅ Format correct: symbol={data['symbol']}, ltp={data['ltp']}")
                        else:
                            print(f"❌ Format incorrect: missing ltp or symbol")
                    
                except asyncio.TimeoutError:
                    print("⏰ No message received in 10 seconds...")
                    
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket())
