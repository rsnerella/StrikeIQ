import asyncio
import websockets
import json
import os
import httpx
import sys

# Add the app path to import protobuf
sys.path.append('.')
sys.path.append('app')
from proto.marketdata_pb2 import FeedResponse

UPSTOX_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN")

async def test_feed():
    """
    Independent test for Upstox WebSocket market feed with protobuf decoding
    """
    if not UPSTOX_TOKEN:
        raise Exception("UPSTOX_ACCESS_TOKEN not found in environment variables")

    # Try V3 API first - requires authorization
    try:
        print("Trying Upstox V3 API...")
        
        headers = {
            "Authorization": f"Bearer {UPSTOX_TOKEN}",
            "Accept": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.upstox.com/v3/feed/market-data-feed/authorize",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                ws_url = data.get("data", {}).get("authorizedRedirectUri")
                if ws_url:
                    print(f"Got V3 WebSocket URL: {ws_url}")
                    await test_websocket(ws_url)
                    return
            else:
                print(f"V3 API failed: {response.status_code}")
                
    except Exception as e:
        print(f"V3 API error: {e}")
    
    # Fallback to V2 API
    print("Falling back to Upstox V2 API...")
    v2_url = f"wss://api.upstox.com/v2/feed/market-data?access_token={UPSTOX_TOKEN}"
    await test_websocket(v2_url)

async def test_websocket(url):
    """Test WebSocket connection with protobuf decoding"""
    print(f"Connecting to WebSocket: {url}")
    
    try:
        async with websockets.connect(url) as ws:
            print("CONNECTED")

            payload = {
                "guid": "strikeiq-test",
                "method": "sub",
                "data": {
                    "mode": "ltpc",
                    "instrumentKeys": [
                        "NSE_INDEX|Nifty 50",
                        "NSE_INDEX|Nifty Bank"
                    ]
                }
            }

            await ws.send(json.dumps(payload))
            print("SUBSCRIBED TO NIFTY / BANKNIFTY")

            # Listen for first few messages with protobuf decoding
            for i in range(5):
                try:
                    message = await asyncio.wait_for(ws.recv(), timeout=10)
                    
                    if isinstance(message, bytes):
                        # Parse protobuf message
                        feed = FeedResponse()
                        feed.ParseFromString(message)
                        
                        data = {
                            "instrument": feed.instrumentKey,
                            "ltp": feed.ltpc.ltp if feed.ltpc else None,
                            "timestamp": int(asyncio.get_event_loop().time() * 1000)
                        }
                        
                        print(f"TICK {i+1}: LTP={feed.ltpc.ltp if feed.ltpc else 'None'}")
                    else:
                        # Handle JSON messages
                        data = json.loads(message)
                        print(f"JSON {i+1}: Type={data.get('type', 'unknown')}")
                        
                except asyncio.TimeoutError:
                    print("Timeout waiting for message")
                    break
                    
    except Exception as e:
        print(f"WebSocket ERROR: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(test_feed())
