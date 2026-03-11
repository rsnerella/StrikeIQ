#!/usr/bin/env python3
"""
Simple WebSocket test for StrikeIQ debugging
"""

import asyncio
import websockets
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_websocket():
    uri = "ws://localhost:8000/ws/market"
    
    try:
        async with websockets.connect(uri) as websocket:
            logger.info(f"Connected to {uri}")
            
            # Send subscription message
            subscribe_msg = {
                "type": "subscribe",
                "symbol": "NIFTY", 
                "expiry": "2026-03-12"
            }
            await websocket.send(json.dumps(subscribe_msg))
            logger.info(f"Sent subscription: {subscribe_msg}")
            
            # Listen for messages
            async for message in websocket:
                data = json.loads(message)
                msg_type = data.get("type")
                symbol = data.get("symbol")
                
                logger.info(f"Received: {msg_type} for {symbol}")
                
                if msg_type in ["option_chain_update", "analytics_update", "index_tick"]:
                    logger.info(f"✅ SUCCESS: Got {msg_type}")
                    if msg_type == "option_chain_update":
                        strikes = data.get("data", {}).get("strikes", [])
                        logger.info(f"   Strikes count: {len(strikes)}")
                    elif msg_type == "analytics_update":
                        analytics_keys = data.get("data", {}).keys()
                        logger.info(f"   Analytics keys: {list(analytics_keys)}")
                    elif msg_type == "index_tick":
                        ltp = data.get("data", {}).get("ltp")
                        logger.info(f"   LTP: {ltp}")
                        
    except Exception as e:
        logger.error(f"WebSocket test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket())
