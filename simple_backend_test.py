#!/usr/bin/env python3
"""
Simple test to check backend status
"""

import asyncio
import websockets
import json
import logging

logging.basicConfig(level=logging.INFO)

async def simple_test():
    """Simple backend connection test"""
    
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
            
            # Send a simple message to trigger analytics
            print("\n📤 Sending simple market_update to trigger analytics...")
            
            simple_update = {
                "type": "market_update",
                "symbol": "NIFTY",
                "spot": 20000,
                "spotPrice": 20000,
                "liveSpot": 20000,
                "currentSpot": 20000,
                "atm": 20000,
                "ai_ready": True,
                "market_analysis": {
                    "regime": "RANGING",
                    "bias": "BULLISH",
                    "bias_strength": 0.7,
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
                        "regime": "SHORT_GAMMA",
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
                    "summary": "NIFTY | PCR=1.35 | Bias=BULLISH | Call wall=20100 | Put wall=19900 | IV=15.50%"
                },
                "early_warnings": [],
                "trade_plan": {
                    "plan_id": "PLAN-NIFTY-1640995200",
                    "instrument": "NIFTY",
                    "direction": "BULLISH",
                    "strike": 20000,
                    "entry": 150.0,
                    "stop_loss": 145.0,
                    "target": 180.0,
                    "confidence": 0.7,
                    "time_horizon": "1W",
                    "risk_reward": 2.0,
                    "reason": ["Strong bullish bias detected"],
                    "signals_used": {
                        "pcr": 1.35,
                        "bias": "BULLISH",
                        "regime": "RANGING",
                        "call_wall": 20100,
                        "put_wall": 19900,
                    },
                },
                "option_chain": {
                    "pcr": 1.35,
                    "call_wall": 20100,
                    "put_wall": 19900,
                    "max_pain": 0,
                    "gex_flip": 0,
                    "net_gex": 0,
                    "iv_atm": 15.5,
                    "iv_percentile": 0,
                    "straddle_pct": 0,
                    "calls": {
                        "20000": {"ltp": 150.0, "oi": 120000, "iv": 16.0}
                    },
                    "puts": {
                        "20000": {"ltp": 80.0, "oi": 130000, "iv": 16.0}
                    }
                }
            }
            
            await websocket.send(json.dumps(simple_update))
            print("📤 Sent simple market_update")
            
            # Wait for responses
            message_count = 0
            chart_analysis_count = 0
            
            while message_count < 8:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                    data = json.loads(message)
                    
                    message_count += 1
                    msg_type = data.get('type', 'unknown')
                    print(f"\n📨 Message {message_count}: {msg_type}")
                    
                    if msg_type == 'chart_analysis':
                        chart_analysis_count += 1
                        print("🎯 CHART_ANALYSIS RECEIVED!")
                        print(f"   ✅ Fields: {len(data)} keys present")
                        
                        # Check key fields
                        key_fields = ['bias', 'bias_strength', 'regime', 'flow_analysis', 
                                     'technical_state', 'key_levels', 'gamma_analysis', 
                                     'volatility_state', 'liquidity_analysis']
                        
                        for field in key_fields:
                            if field in data:
                                print(f"   ✅ {field}")
                            else:
                                print(f"   ❌ {field}: MISSING")
                        
                        if chart_analysis_count >= 1:
                            print("\n🎉 SUCCESS: Components should now display data!")
                            break
                    
                    elif msg_type in ['subscribed', 'market_update']:
                        print(f"📊 {msg_type} received")
                    
                except asyncio.TimeoutError:
                    print("⏰ Timeout waiting for message")
                    break
                except Exception as e:
                    print(f"❌ Error: {e}")
            
            if chart_analysis_count == 0:
                print("\n⚠️  No chart_analysis messages received")
                print("🔧 Check if analytics broadcaster is running")
                
    except Exception as e:
        print(f"❌ Connection error: {e}")

if __name__ == "__main__":
    asyncio.run(simple_test())
