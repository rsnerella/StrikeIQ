#!/usr/bin/env python3
"""
Complete WebSocket test with proper data setup
"""

import asyncio
import websockets
import json
import logging
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from app.services.option_chain_builder import option_chain_builder

logging.basicConfig(level=logging.INFO)

async def test_complete_websocket():
    """Test complete WebSocket pipeline with proper data setup"""
    
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
            
            # First, set up the option chain builder with mock data
            print("\n📊 Setting up option chain builder with mock data...")
            
            # Mock option data class
            class MockOptionData:
                def __init__(self, ltp, oi, iv):
                    self.ltp = ltp
                    self.oi = oi
                    self.iv = iv
                    self.bid = ltp * 0.95
                    self.ask = ltp * 1.05
                    self.delta = 0.5
                    self.gamma = 0.1
                    self.theta = -0.05
                    self.vega = 0.2
                    self.volume = oi // 10
            
            # Mock snapshot class
            class MockSnapshot:
                def __init__(self):
                    self.symbol = "NIFTY"
                    self.spot = 20000.0
                    self.atm_strike = 20000
                    self.pcr = 0.95
                    self.max_call_oi_strike = 20100
                    self.max_put_oi_strike = 19900
                    self.total_call_oi = 500000
                    self.total_put_oi = 550000
                    self.atm_iv = 15.5
                    self.vwap = 19950
                    
                    # Create mock calls and puts data
                    self.calls_data = {}
                    self.puts_data = {}
                    
                    strikes = [19800, 19900, 20000, 20100, 20200]
                    for strike in strikes:
                        self.calls_data[str(strike)] = {
                            "ltp": max(10, 200 - abs(strike - 20000) * 2),
                            "oi": 100000 - abs(strike - 20000) * 500,
                            "iv": 15.5 + abs(strike - 20000) * 0.01
                        }
                        self.puts_data[str(strike)] = {
                            "ltp": max(10, 200 - abs(strike - 20000) * 2),
                            "oi": 100000 - abs(strike - 20000) * 400,
                            "iv": 15.5 + abs(strike - 20000) * 0.01
                        }
            
            # Add mock data to option chain builder
            mock_snap = MockSnapshot()
            
            # Create chain data
            chain_data = {}
            for strike_str, call_data in mock_snap.calls_data.items():
                chain_data[strike_str] = {
                    "CE": MockOptionData(
                        call_data["ltp"], 
                        call_data["oi"], 
                        call_data["iv"]
                    ),
                    "PE": MockOptionData(
                        mock_snap.puts_data[strike_str]["ltp"],
                        mock_snap.puts_data[strike_str]["oi"], 
                        mock_snap.puts_data[strike_str]["iv"]
                    )
                }
            
            # Add to option chain builder
            option_chain_builder.chains["NIFTY"] = chain_data
            option_chain_builder.snapshots = {"NIFTY": mock_snap}
            
            print(f"✅ Mock data added:")
            print(f"   - Symbol: {mock_snap.symbol}")
            print(f"   - Spot: {mock_snap.spot}")
            print(f"   - Strikes: {len(chain_data)}")
            print(f"   - PCR: {mock_snap.pcr}")
            
            # Now send option chain update to trigger analytics
            print("\n📤 Sending option_chain_update message...")
            
            option_update = {
                "type": "option_chain_update",
                "symbol": "NIFTY",
                "timestamp": 1640995200,
                "spot": mock_snap.spot,
                "atm": mock_snap.atm_strike,
                "pcr": mock_snap.pcr,
                "calls": mock_snap.calls_data,
                "puts": mock_snap.puts_data,
                "strikesCount": len(chain_data)
            }
            
            await websocket.send(json.dumps(option_update))
            print("📤 Sent option_chain_update")
            
            # Wait for analytics broadcaster to process
            print("\n⏳ Waiting 2 seconds for analytics broadcaster to process...")
            await asyncio.sleep(2)
            
            # Manually trigger analytics computation by setting dirty flag
            print("🔄 Manually triggering analytics computation...")
            from app.services.analytics_broadcaster import analytics_broadcaster
            analytics_broadcaster.compute_single_analytics("NIFTY")
            
            # Wait another second for processing
            await asyncio.sleep(1)
            
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
                            print("✅ LIQUIDITY VACUUM DATA VISIBLE IN WEBSOCKET!")
                            break
                        else:
                            print("❌ No liquidity_analysis field found")
                    
                    # Print other message types
                    elif data.get('type') == 'subscribed':
                        print("✅ Subscription confirmed")
                    elif data.get('type') == 'option_chain_update':
                        print("📈 Option chain update received")
                    elif data.get('type') == 'market_update':
                        print("📊 Market update received")
                    
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
                print("🌐 Open http://localhost:3000 to see the liquidity vacuum panel")
            else:
                print("\n⚠️  No chart_analysis messages received")
                print("🔧 The analytics broadcaster may need more time or different triggers")
                
    except websockets.exceptions.ConnectionRefused:
        print("❌ Connection refused - is the backend server running?")
    except Exception as e:
        print(f"❌ WebSocket error: {e}")

if __name__ == "__main__":
    asyncio.run(test_complete_websocket())
