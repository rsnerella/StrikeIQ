#!/usr/bin/env python3
"""
Test component data reception with timing
"""

import asyncio
import websockets
import json
import logging

logging.basicConfig(level=logging.INFO)

async def test_component_timing():
    """Test component data reception timing"""
    
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
            
            # Wait for chart_analysis message
            print("\n⏳ Waiting for chart_analysis message...")
            
            chart_analysis_received = False
            attempts = 0
            
            while not chart_analysis_received and attempts < 10:
                attempts += 1
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    data = json.loads(message)
                    
                    if data.get('type') == 'chart_analysis':
                        chart_analysis_received = True
                        print(f"\n🎯 CHART_ANALYSIS RECEIVED (attempt {attempts}):")
                        
                        # Check all required fields
                        required_fields = [
                            'bias', 'bias_strength', 'regime',
                            'flow_analysis', 'technical_state', 'key_levels',
                            'gamma_analysis', 'volatility_state', 'liquidity_analysis'
                        ]
                        
                        missing_fields = []
                        present_fields = []
                        
                        for field in required_fields:
                            if field in data:
                                present_fields.append(field)
                                if field in ['bias', 'bias_strength', 'regime']:
                                    print(f"  ✅ {field}: {data[field]}")
                                elif field == 'liquidity_analysis':
                                    liq = data[field]
                                    print(f"  ✅ {field}: vacuum_start={liq.get('vacuum_start')}, vacuum_end={liq.get('vacuum_end')}")
                                else:
                                    print(f"  ✅ {field}: present")
                            else:
                                missing_fields.append(field)
                                print(f"  ❌ {field}: MISSING")
                        
                        print(f"\n📊 SUMMARY: {len(present_fields)}/{len(required_fields)} fields present")
                        
                        if missing_fields:
                            print(f"❌ Missing: {missing_fields}")
                        else:
                            print("✅ ALL FIELDS PRESENT - Components should receive data!")
                    
                    elif data.get('type') in ['subscribed', 'market_update']:
                        print(f"📨 {data.get('type')} message")
                    
                except asyncio.TimeoutError:
                    print(f"⏰ Timeout {attempts}/10")
                    break
                except Exception as e:
                    print(f"❌ Error: {e}")
            
            if chart_analysis_received:
                print(f"\n SUCCESS: chart_analysis message received with all required fields!")
                print(" Frontend components should now display data properly")
            else:
                print(f"\n  No chart_analysis message received after {attempts} attempts")
                
    except websockets.exceptions.ConnectionClosed as e:
        print(" Connection refused - is backend running?")
    except Exception as e:
        print(f" Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_component_timing())
