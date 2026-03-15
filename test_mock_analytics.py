#!/usr/bin/env python3
"""
Test to simulate option chain data and trigger analytics
"""

import asyncio
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from app.services.analytics_broadcaster import analytics_broadcaster
from app.services.option_chain_builder import option_chain_builder

async def test_with_mock_data():
    """Test analytics broadcaster with mock option chain data"""
    
    print("🧪 Testing Analytics Broadcaster with Mock Data")
    print("=" * 50)
    
    try:
        # Create mock option chain snapshot
        print("📊 Creating mock option chain data...")
        
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
                self.calls_data = {
                    "19900": {"ltp": 150.0, "oi": 100000, "iv": 16.0},
                    "20000": {"ltp": 100.0, "oi": 120000, "iv": 15.5},
                    "20100": {"ltp": 60.0, "oi": 90000, "iv": 15.0}
                }
                self.puts_data = {
                    "19900": {"ltp": 50.0, "oi": 110000, "iv": 16.0},
                    "20000": {"ltp": 80.0, "oi": 130000, "iv": 15.5},
                    "20100": {"ltp": 120.0, "oi": 80000, "iv": 15.0}
                }
        
        # Add mock snapshot to option chain builder
        mock_snap = MockSnapshot()
        option_chain_builder.chains["NIFTY"] = {
            "19900": {"CE": type('CE', (), mock_snap.calls_data["19900"])(), 
                     "PE": type('PE', (), mock_snap.puts_data["19900"])()},
            "20000": {"CE": type('CE', (), mock_snap.calls_data["20000"])(), 
                     "PE": type('PE', (), mock_snap.puts_data["20000"])()},
            "20100": {"CE": type('CE', (), mock_snap.calls_data["20100"])(), 
                     "PE": type('PE', (), mock_snap.puts_data["20100"])()}
        }
        
        # Store the mock snapshot
        option_chain_builder.snapshots = {"NIFTY": mock_snap}
        
        print("✅ Mock data created")
        print(f"   - Symbol: {mock_snap.symbol}")
        print(f"   - Spot: {mock_snap.spot}")
        print(f"   - PCR: {mock_snap.pcr}")
        print(f"   - Call strikes: {len(mock_snap.calls_data)}")
        print(f"   - Put strikes: {len(mock_snap.puts_data)}")
        
        # Trigger analytics computation
        print("\n🔄 Triggering analytics computation...")
        analytics_broadcaster.compute_single_analytics("NIFTY")
        
        # Start broadcaster briefly
        print("🚀 Starting broadcaster for 3 seconds...")
        await analytics_broadcaster.start()
        await asyncio.sleep(3)
        await analytics_broadcaster.stop()
        
        print("✅ Test completed")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_with_mock_data())
