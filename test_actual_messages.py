#!/usr/bin/env python3
"""
Simple WebSocket test to see actual messages
"""

import asyncio
import websockets
import json
import logging

logging.basicConfig(level=logging.INFO)

async def test_actual_messages():
    """Test actual WebSocket messages"""
    
    uri = "ws://localhost:8000/ws/market"
    
    try:
        print("🔌 Connecting to WebSocket...")
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to WebSocket")
            
            # Send subscription
            subscription = {
                "type": "subscribe",
                "symbol": "NIFTY",
                "expiry": "current"
            }
            await websocket.send(json.dumps(subscription))
            print("📤 Sent subscription")
            
            # Listen for 5 messages
            for i in range(5):
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    data = json.loads(message)
                    
                    print(f"\n{'='*60}")
                    print(f"Message {i+1}: {data.get('type', 'unknown')}")
                    
                    if data.get('type') == 'chart_analysis':
                        print("🎯 CHART_ANALYSIS DETAILED VIEW:")
                        for key, value in data.items():
                            if isinstance(value, dict):
                                print(f"  {key}:")
                                for subkey, subvalue in value.items():
                                    print(f"    {subkey}: {subvalue}")
                            else:
                                print(f"  {key}: {value}")
                    elif data.get('type') == 'market_update':
                        print("📊 MARKET_UPDATE:")
                        if 'market_analysis' in data:
                            ma = data['market_analysis']
                            print(f"  regime: {ma.get('regime')}")
                            print(f"  bias: {ma.get('bias')}")
                            print(f"  bias_strength: {ma.get('bias_strength')}")
                    
                except asyncio.TimeoutError:
                    print("⏰ Timeout waiting for message")
                    break
                except json.JSONDecodeError as e:
                    print(f"❌ JSON error: {e}")
                except Exception as e:
                    print(f"❌ Error: {e}")
                    
    except websockets.exceptions.ConnectionRefused:
        print("❌ Connection refused")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_actual_messages())
