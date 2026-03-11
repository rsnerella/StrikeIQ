#!/usr/bin/env python3
"""
Test script to verify updated analytics payload structure
"""

import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

async def test_payload_structure():
    """Test the updated analytics payload structure"""
    print("🔧 TESTING UPDATED ANALYTICS PAYLOAD STRUCTURE")
    
    try:
        # Import analytics broadcaster
        from app.services.analytics_broadcaster import analytics_broadcaster
        
        # Create mock chain data with correct structure
        mock_chain_data = {
            "symbol": "NIFTY",
            "spot": 23944.0,
            "atm_strike": 23950.0,
            "strikes": [
                {
                    "strike": 23900.0,
                    "call_oi": 1500000,
                    "call_ltp": 245.50,
                    "call_volume": 50000,
                    "put_oi": 1200000,
                    "put_ltp": 198.25,
                    "put_volume": 45000
                },
                {
                    "strike": 23950.0,
                    "call_oi": 1800000,
                    "call_ltp": 220.75,
                    "call_volume": 55000,
                    "put_oi": 1650000,
                    "put_ltp": 175.50,
                    "put_volume": 48000
                }
            ],
            "pcr": 1.12,
            "total_oi_calls": 3300000,
            "total_oi_puts": 2850000
        }
        
        print("✅ Mock chain data created")
        print(f"   Strikes: {len(mock_chain_data['strikes'])}")
        
        # Compute analytics
        analytics = await analytics_broadcaster.compute_single_analytics(
            mock_chain_data['symbol'], 
            mock_chain_data
        )
        
        if analytics:
            print("✅ Analytics computed successfully")
            
            # Check payload structure
            print(f"   Payload type: {analytics.get('type')}")
            print(f"   Symbol: {analytics.get('symbol')}")
            print(f"   Has data.analytics: {'analytics' in analytics.get('data', {})}")
            
            # Check frontend expected structure
            data = analytics.get('data', {})
            analytics_data = data.get('analytics', {})
            
            print("✅ Frontend-compatible structure verified:")
            print(f"   msg.data.analytics.pcr: {analytics_data.get('pcr')}")
            print(f"   msg.data.analytics.total_call_oi: {analytics_data.get('total_call_oi'):,}")
            print(f"   msg.data.analytics.total_put_oi: {analytics_data.get('total_put_oi'):,}")
            print(f"   msg.data.analytics.total_oi: {analytics_data.get('total_oi'):,}")
            
            # Verify frontend can access data correctly
            if analytics_data.get('pcr') and analytics_data.get('total_call_oi'):
                print("✅ Frontend mapping will work correctly")
                print("   data?.analytics?.pcr →", analytics_data.get('pcr'))
                print("   data?.analytics?.total_call_oi →", analytics_data.get('total_call_oi'))
            else:
                print("❌ Frontend mapping may fail")
                return False
                
        else:
            print("❌ Analytics computation failed")
            return False
        
        print("\n🎉 PAYLOAD STRUCTURE TEST COMPLETE - FRONTEND COMPATIBLE")
        return True
        
    except Exception as e:
        print(f"❌ Payload structure test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_payload_structure())
    sys.exit(0 if success else 1)
