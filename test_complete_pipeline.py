#!/usr/bin/env python3
"""
Complete test with mock option chain data
"""

import asyncio
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from app.services.analytics_broadcaster import analytics_broadcaster
from app.services.option_chain_builder import option_chain_builder

async def test_complete_pipeline():
    """Test complete pipeline with mock data"""
    
    print("🧪 Complete Pipeline Test with Mock Data")
    print("=" * 50)
    
    try:
        # 1. Create mock option chain data
        print("📊 Creating mock option chain data...")
        
        # Mock option data class
        class MockOptionData:
            def __init__(self, ltp, oi, iv, bid=None, ask=None):
                self.ltp = ltp
                self.oi = oi
                self.iv = iv
                self.bid = bid or ltp * 0.95
                self.ask = ask or ltp * 1.05
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
        
        # 2. Add mock data to option chain builder
        print("📦 Adding mock data to option chain builder...")
        
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
        
        # 3. Test analytics computation
        print("\n🔄 Testing analytics computation...")
        
        # Set dirty flag to trigger computation
        analytics_broadcaster._dirty["NIFTY"] = True
        analytics_broadcaster._last_broadcast_time["NIFTY"] = 0
        
        # Mock WebSocket manager to capture messages
        captured_messages = []
        
        class MockWebSocket:
            async def send_text(self, message):
                captured_messages.append(message)
                print(f"📨 Captured message: {len(message)} chars")
        
        # Add mock WebSocket connection
        mock_ws = MockWebSocket()
        manager.active_connections.append(mock_ws)
        
        print(f"🔌 Mock WebSocket connection added (total: {len(manager.active_connections)})")
        
        # Run analytics computation
        await analytics_broadcaster._compute_and_broadcast("NIFTY")
        
        # 4. Analyze captured messages
        print(f"\n📊 Analysis: Captured {len(captured_messages)} messages")
        
        chart_analysis_found = False
        for i, message in enumerate(captured_messages):
            try:
                data = json.loads(message)
                print(f"Message {i+1}: {data.get('type', 'unknown')}")
                
                if data.get('type') == 'chart_analysis':
                    chart_analysis_found = True
                    print("🎯 CHART_ANALYSIS MESSAGE FOUND!")
                    
                    if 'liquidity_analysis' in data:
                        liq = data['liquidity_analysis']
                        print("💧 LIQUIDITY VACUUM DATA:")
                        print(f"   - Vacuum zone: ₹{liq.get('vacuum_start', 'N/A')} - ₹{liq.get('vacuum_end', 'N/A')}")
                        print(f"   - Book depth: {liq.get('book_depth', 'N/A')}")
                        print(f"   - Expansion probability: {liq.get('expansion_probability', 'N/A')}")
                        print(f"   - Vacuum signal: {liq.get('vacuum_signal', 'N/A')}")
                        print(f"   - Vacuum direction: {liq.get('vacuum_direction', 'N/A')}")
                        
            except Exception as e:
                print(f"Error parsing message {i+1}: {e}")
        
        if chart_analysis_found:
            print("\n🎉 SUCCESS: Liquidity vacuum pipeline is working!")
            print("📱 The frontend LiquidityVacuumPanel should display the data")
        else:
            print("\n❌ No chart_analysis messages found")
        
        # Cleanup
        manager.active_connections.clear()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import json
    from app.core.ws_manager import manager
    asyncio.run(test_complete_pipeline())
