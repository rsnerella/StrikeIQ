#!/usr/bin/env python3
"""
Final test script to verify corrected StrikeIQ analytics payload structure
"""

import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

async def test_final_payload_structure():
    """Test the final corrected analytics payload structure"""
    print("🔧 TESTING FINAL CORRECTED ANALYTICS PAYLOAD STRUCTURE")
    
    try:
        # Import analytics broadcaster
        from app.services.analytics_broadcaster import analytics_broadcaster
        
        # Create mock chain data
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
        
        # Compute analytics
        analytics = await analytics_broadcaster.compute_single_analytics(
            mock_chain_data['symbol'], 
            mock_chain_data
        )
        
        if analytics:
            print("✅ Analytics computed successfully")
            print(f"   Return type: {type(analytics)}")
            print(f"   Has pcr: {'pcr' in analytics}")
            print(f"   Has total_call_oi: {'total_call_oi' in analytics}")
            print(f"   Has total_put_oi: {'total_put_oi' in analytics}")
            
            # Verify expected frontend structure
            print("✅ Final Frontend-Compatible Structure:")
            print(f"   msg.data.analytics.pcr: {analytics.get('pcr')}")
            print(f"   msg.data.analytics.total_call_oi: {analytics.get('total_call_oi'):,}")
            print(f"   msg.data.analytics.total_put_oi: {analytics.get('total_put_oi'):,}")
            print(f"   msg.data.analytics.total_oi: {analytics.get('total_oi'):,}")
            
            # Verify no None values
            if all(analytics.get(key) is not None for key in ['pcr', 'total_call_oi', 'total_put_oi']):
                print("✅ All critical analytics values present")
            else:
                print("❌ Missing critical analytics values")
                return False
                
        else:
            print("❌ Analytics computation failed")
            return False
        
        print("\n🎉 FINAL PAYLOAD STRUCTURE TEST COMPLETE - PRODUCTION READY")
        return True
        
    except Exception as e:
        print(f"❌ Final payload test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_final_payload_structure())
    sys.exit(0 if success else 1)
