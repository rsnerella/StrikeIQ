#!/usr/bin/env python3
"""
WebSocket client to test liquidity vacuum data flow
"""

import asyncio
import websockets
import json
import logging

logging.basicConfig(level=logging.INFO)

async def test_liquidity_vacuum_websocket():
    """Test liquidity vacuum data via WebSocket"""
    
    uri = "ws://localhost:8000/ws/market"
    
    try:
        print("🔌 Connecting to WebSocket...")
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to WebSocket")
            
            # Send subscription message
            subscription = {
                "type": "subscribe",
                "symbol": "NIFTY",
                "expiry": "current"
            }
            await websocket.send(json.dumps(subscription))
            print("📤 Sent subscription message")
            
            # Listen for messages
            message_count = 0
            chart_analysis_received = False
            
            while message_count < 10:  # Listen for 10 messages
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    data = json.loads(message)
                    
                    message_count += 1
                    print(f"\n📨 Message {message_count}: {data.get('type', 'unknown')}")
                    
                    # Check for chart_analysis messages
                    if data.get('type') == 'chart_analysis':
                        chart_analysis_received = True
                        print("🎯 CHART_ANALYSIS MESSAGE RECEIVED!")
                        
                        if 'liquidity_analysis' in data:
                            liq = data['liquidity_analysis']
                            print("💧 LIQUIDITY VACUUM DATA:")
                            print(f"   - Vacuum zone: ₹{liq.get('vacuum_start', 'N/A')} - ₹{liq.get('vacuum_end', 'N/A')}")
                            print(f"   - Book depth: {liq.get('book_depth', 'N/A')}")
                            print(f"   - Expansion probability: {liq.get('expansion_probability', 'N/A')}")
                            print(f"   - Vacuum signal: {liq.get('vacuum_signal', 'N/A')}")
                            print(f"   - Vacuum direction: {liq.get('vacuum_direction', 'N/A')}")
                            print("✅ LIQUIDITY VACUUM DATA VISIBLE!")
                        else:
                            print("❌ No liquidity_analysis field found")
                    
                    # Check for market_update messages
                    elif data.get('type') == 'market_update':
                        print("📈 Market update received")
                        if data.get('ai_ready'):
                            print("✅ AI ready flag set")
                    
                except asyncio.TimeoutError:
                    print("⏰ Timeout waiting for message")
                    break
                except json.JSONDecodeError as e:
                    print(f"❌ JSON decode error: {e}")
                except Exception as e:
                    print(f"❌ Error receiving message: {e}")
            
            if chart_analysis_received:
                print("\n🎉 SUCCESS: Liquidity vacuum data is flowing via WebSocket!")
                print("📱 The frontend LiquidityVacuumPanel should now display the data")
            else:
                print("\n⚠️  No chart_analysis messages received")
                print("🔧 Check if the analytics broadcaster is running correctly")
                
    except websockets.exceptions.ConnectionRefused:
        print("❌ Connection refused - is the backend server running?")
    except Exception as e:
        print(f"❌ WebSocket error: {e}")

if __name__ == "__main__":
    asyncio.run(test_liquidity_vacuum_websocket())
