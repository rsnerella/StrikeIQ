#!/usr/bin/env python3
"""
WebSocket client that connects first, then tests liquidity vacuum
"""

import asyncio
import websockets
import json
import logging

logging.basicConfig(level=logging.INFO)

async def test_with_active_connection():
    """Test liquidity vacuum with active WebSocket connection"""
    
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
            
            # Now trigger analytics computation
            print("\n🔄 Manually triggering analytics computation...")
            
            # Send a mock market_update to trigger analytics
            mock_update = {
                "type": "market_update",
                "symbol": "NIFTY",
                "timestamp": 1640995200,
                "spot": 20000,
                "spotPrice": 20000,
                "liveSpot": 20000,
                "currentSpot": 20000,
                "atm": 20000,
                "ai_ready": True,
                "market_analysis": {
                    "regime": "RANGING",
                    "bias": "NEUTRAL",
                    "bias_strength": 0.3,
                    "key_levels": {
                        "call_wall": 20100,
                        "put_wall": 19900,
                        "max_pain": 0,
                        "gex_flip": 0,
                        "vwap": 19950,
                        "ema20": 0,
                        "ema50": 0,
                    },
                    "gamma_analysis": {
                        "net_gex": 0,
                        "regime": "LONG_GAMMA",
                        "flip_level": 0,
                        "implication": "Dealer positioning from OI structure",
                    },
                    "volatility_state": {
                        "iv_atm": 15.5,
                        "iv_percentile": 0,
                        "state": "NORMAL",
                        "compression": False,
                    },
                    "technical_state": {
                        "rsi": 0,
                        "macd_hist": 0,
                        "adx": 0,
                        "momentum_15m": 0,
                        "pattern": "NONE",
                    },
                    "summary": "NIFTY | PCR=0.95 | Bias=NEUTRAL | Call wall=20100 | Put wall=19900 | IV=15.50%"
                },
                "option_chain": {
                    "pcr": 0.95,
                    "call_wall": 20100,
                    "put_wall": 19900,
                    "max_pain": 0,
                    "gex_flip": 0,
                    "net_gex": 0,
                    "iv_atm": 15.5,
                    "iv_percentile": 0,
                    "straddle_pct": 0,
                    "calls": {
                        "19900": {"ltp": 150.0, "oi": 100000, "iv": 16.0},
                        "20000": {"ltp": 100.0, "oi": 120000, "iv": 15.5},
                        "20100": {"ltp": 60.0, "oi": 90000, "iv": 15.0}
                    },
                    "puts": {
                        "19900": {"ltp": 50.0, "oi": 110000, "iv": 16.0},
                        "20000": {"ltp": 80.0, "oi": 130000, "iv": 15.5},
                        "20100": {"ltp": 120.0, "oi": 80000, "iv": 15.0}
                    }
                }
            }
            
            await websocket.send(json.dumps(mock_update))
            print("📤 Sent mock market_update")
            
            # Listen for messages
            message_count = 0
            chart_analysis_received = False
            
            while message_count < 5:  # Listen for 5 messages
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
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
                            break
                        else:
                            print("❌ No liquidity_analysis field found")
                    
                    # Print other message types
                    elif data.get('type') == 'subscribed':
                        print("✅ Subscription confirmed")
                    elif data.get('type') == 'market_update':
                        print("📈 Market update received")
                    
                except asyncio.TimeoutError:
                    print("⏰ Timeout waiting for message")
                    break
                except json.JSONDecodeError as e:
                    print(f"❌ JSON decode error: {e}")
                except Exception as e:
                    print(f"❌ Error receiving message: {e}")
            
            if chart_analysis_received:
                print("\n🎉 SUCCESS: Liquidity vacuum data is flowing!")
                print("📱 The frontend LiquidityVacuumPanel should now display the data")
            else:
                print("\n⚠️  No chart_analysis messages received")
                print("🔧 The analytics broadcaster may not be generating chart_analysis messages")
                
    except websockets.exceptions.ConnectionRefused:
        print("❌ Connection refused - is the backend server running?")
    except Exception as e:
        print(f"❌ WebSocket error: {e}")

if __name__ == "__main__":
    asyncio.run(test_with_active_connection())
