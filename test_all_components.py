#!/usr/bin/env python3
"""
Test all component data flow
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

async def test_all_components():
    """Test all component data flow"""
    
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
            
            # Set up option chain builder with mock data
            print("\n📊 Setting up comprehensive mock data...")
            
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
                    self.pcr = 1.35  # Strong bullish bias
                    self.max_call_oi_strike = 20100
                    self.max_put_oi_strike = 19900
                    self.total_call_oi = 600000  # More calls than puts
                    self.total_put_oi = 400000
                    self.atm_iv = 18.5  # Elevated IV
                    self.vwap = 19950
                    
                    # Create mock calls and puts data
                    self.calls_data = {}
                    self.puts_data = {}
                    
                    strikes = [19800, 19900, 20000, 20100, 20200]
                    for strike in strikes:
                        self.calls_data[str(strike)] = {
                            "ltp": max(10, 250 - abs(strike - 20000) * 2),
                            "oi": 120000 - abs(strike - 20000) * 500,
                            "iv": 18.5 + abs(strike - 20000) * 0.01
                        }
                        self.puts_data[str(strike)] = {
                            "ltp": max(10, 250 - abs(strike - 20000) * 2),
                            "oi": 80000 - abs(strike - 20000) * 400,
                            "iv": 18.5 + abs(strike - 20000) * 0.01
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
            print(f"   - PCR: {mock_snap.pcr} (BULLISH bias)")
            print(f"   - Call OI: {mock_snap.total_call_oi}")
            print(f"   - Put OI: {mock_snap.total_put_oi}")
            print(f"   - Strikes: {len(chain_data)}")
            
            # Send option chain update
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
            
            # Listen for messages
            message_count = 0
            component_data = {
                "liquidity_vacuum": False,
                "bias_data": False,
                "flow_analysis": False,
                "technical_analysis": False,
                "trade_plan": False
            }
            
            while message_count < 10 and not all(component_data.values()):
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                    data = json.loads(message)
                    
                    message_count += 1
                    print(f"\n📨 Message {message_count}: {data.get('type', 'unknown')}")
                    
                    if data.get('type') == 'chart_analysis':
                        print("🎯 CHART_ANALYSIS MESSAGE RECEIVED!")
                        
                        # Check for all required data
                        if 'liquidity_analysis' in data:
                            component_data["liquidity_vacuum"] = True
                            print("   ✅ liquidity_analysis present")
                        
                        if 'bias' in data and 'bias_strength' in data:
                            component_data["bias_data"] = True
                            print(f"   ✅ bias data: {data['bias']} (strength: {data['bias_strength']})")
                        
                        if 'flow_analysis' in data:
                            component_data["flow_analysis"] = True
                            flow = data['flow_analysis']
                            print(f"   ✅ flow_analysis: direction={flow.get('direction')}, imbalance={flow.get('imbalance')}")
                        
                        if 'technical_state' in data:
                            component_data["technical_analysis"] = True
                            print("   ✅ technical_state present")
                        
                        if 'key_levels' in data:
                            print("   ✅ key_levels present")
                        
                        if 'gamma_analysis' in data:
                            print("   ✅ gamma_analysis present")
                        
                        if 'volatility_state' in data:
                            print("   ✅ volatility_state present")
                    
                    elif data.get('type') == 'market_update':
                        print("📊 Market update received")
                        if data.get('trade_plan'):
                            component_data["trade_plan"] = True
                            print("   ✅ trade_plan present")
                    
                    elif data.get('type') == 'subscribed':
                        print("✅ Subscription confirmed")
                    
                except asyncio.TimeoutError:
                    print("⏰ Timeout waiting for message")
                    break
                except json.JSONDecodeError as e:
                    print(f"❌ JSON decode error: {e}")
                except Exception as e:
                    print(f"❌ Error receiving message: {e}")
            
            print(f"\n📊 COMPONENT DATA STATUS:")
            for component, status in component_data.items():
                status_icon = "✅" if status else "❌"
                print(f"   {status_icon} {component.replace('_', ' ').title()}: {'RECEIVING' if status else 'MISSING'}")
            
            if all(component_data.values()):
                print(f"\n🎉 SUCCESS: All components are receiving data!")
                print(f"📱 Open http://localhost:3000 to see all dashboard panels populated")
            else:
                print(f"\n⚠️  Some components missing data")
                print(f"🔧 Check backend payload structure")
                
    except websockets.exceptions.ConnectionRefused:
        print("❌ Connection refused - is backend server running?")
    except Exception as e:
        print(f"❌ WebSocket error: {e}")

if __name__ == "__main__":
    asyncio.run(test_all_components())
