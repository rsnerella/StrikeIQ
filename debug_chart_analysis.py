#!/usr/bin/env python3
"""
Debug chart_analysis payload
"""

import asyncio
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from app.services.analytics_broadcaster import analytics_broadcaster
from app.services.option_chain_builder import option_chain_builder

async def debug_chart_analysis():
    """Debug chart_analysis payload generation"""
    
    print("🔍 Debugging chart_analysis payload generation...")
    
    # Set up mock data
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
    
    # Add mock data
    mock_snap = MockSnapshot()
    chain_data = {}
    for strike_str, call_data in mock_snap.calls_data.items():
        chain_data[strike_str] = {
            "CE": MockOptionData(call_data["ltp"], call_data["oi"], call_data["iv"]),
            "PE": MockOptionData(mock_snap.puts_data[strike_str]["ltp"], 
                                mock_snap.puts_data[strike_str]["oi"], 
                                mock_snap.puts_data[strike_str]["iv"])
        }
    
    option_chain_builder.chains["NIFTY"] = chain_data
    option_chain_builder.snapshots = {"NIFTY": mock_snap}
    
    # Trigger analytics computation
    analytics_broadcaster._dirty["NIFTY"] = True
    analytics_broadcaster._last_broadcast_time["NIFTY"] = 0
    
    print("🔄 Running analytics computation...")
    
    try:
        # Capture the chart_analysis payload
        import json
        from unittest.mock import patch
        
        # Mock the broadcast to capture the message
        captured_messages = []
        
        def mock_broadcast(message):
            try:
                data = json.loads(message)
                if data.get('type') == 'chart_analysis':
                    captured_messages.append(data)
                    print("📨 Captured chart_analysis message:")
                    print(f"   - Type: {data.get('type')}")
                    print(f"   - Symbol: {data.get('symbol')}")
                    print(f"   - Bias: {data.get('bias')}")
                    print(f"   - Bias Strength: {data.get('bias_strength')}")
                    print(f"   - Regime: {data.get('regime')}")
                    print(f"   - Flow Analysis: {'present' if 'flow_analysis' in data else 'MISSING'}")
                    print(f"   - Technical State: {'present' if 'technical_state' in data else 'MISSING'}")
                    print(f"   - Key Levels: {'present' if 'key_levels' in data else 'MISSING'}")
                    print(f"   - Gamma Analysis: {'present' if 'gamma_analysis' in data else 'MISSING'}")
                    print(f"   - Volatility State: {'present' if 'volatility_state' in data else 'MISSING'}")
                    print(f"   - Liquidity Analysis: {'present' if 'liquidity_analysis' in data else 'MISSING'}")
            except:
                captured_messages.append(message)  # Raw message
        
        # Patch the broadcast method
        with patch('app.services.analytics_broadcaster.manager.broadcast', mock_broadcast):
            await analytics_broadcaster._compute_and_broadcast("NIFTY")
        
        if captured_messages:
            chart_data = captured_messages[0]
            print(f"\n📊 CHART_ANALYSIS PAYLOAD ANALYSIS:")
            print(f"   Total keys: {len(chart_data)}")
            print(f"   Keys: {list(chart_data.keys())}")
            
            # Check required keys for components
            required_keys = [
                'bias', 'bias_strength', 'regime',
                'flow_analysis', 'technical_state', 'key_levels',
                'gamma_analysis', 'volatility_state', 'liquidity_analysis'
            ]
            
            missing_keys = []
            for key in required_keys:
                if key not in chart_data:
                    missing_keys.append(key)
            
            if missing_keys:
                print(f"\n❌ MISSING KEYS: {missing_keys}")
            else:
                print(f"\n✅ ALL REQUIRED KEYS PRESENT")
                
        else:
            print("❌ No chart_analysis message captured")
            
    except Exception as e:
        print(f"❌ Debug error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_chart_analysis())
