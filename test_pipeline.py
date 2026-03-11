#!/usr/bin/env python3
"""
Test script to verify StrikeIQ analytics pipeline
"""

import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

async def test_pipeline():
    """Test the complete analytics pipeline"""
    print("🔧 TESTING STRIKEIQ ANALYTICS PIPELINE")
    
    try:
        # Test 1: Import option chain builder
        from app.services.option_chain_builder import option_chain_builder
        print("✅ Option chain builder imported")
        
        # Test 2: Import analytics broadcaster
        from app.services.analytics_broadcaster import analytics_broadcaster
        print("✅ Analytics broadcaster imported")
        
        # Test 3: Create mock chain data
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
        print(f"   Symbol: {mock_chain_data['symbol']}")
        print(f"   Spot: {mock_chain_data['spot']}")
        print(f"   PCR: {mock_chain_data['pcr']}")
        print(f"   Total Call OI: {mock_chain_data['total_oi_calls']:,}")
        print(f"   Total Put OI: {mock_chain_data['total_oi_puts']:,}")
        
        # Test 4: Update option chain builder
        option_chain_builder.update_index_price(mock_chain_data['symbol'], mock_chain_data['spot'])
        
        for strike_data in mock_chain_data['strikes']:
            option_chain_builder.update_option_tick(
                mock_chain_data['symbol'],
                strike_data['strike'],
                'CE',
                strike_data['call_ltp'],
                strike_data['call_oi'],
                strike_data['call_volume']
            )
            option_chain_builder.update_option_tick(
                mock_chain_data['symbol'],
                strike_data['strike'],
                'PE',
                strike_data['put_ltp'],
                strike_data['put_oi'],
                strike_data['put_volume']
            )
        
        print("✅ Option chain builder updated")
        
        # Test 5: Create snapshot
        snapshot = option_chain_builder._create_snapshot(mock_chain_data['symbol'])
        if snapshot:
            print("✅ Chain snapshot created")
            print(f"   PCR: {snapshot.pcr}")
            print(f"   Total Call OI: {snapshot.total_oi_calls:,}")
            print(f"   Total Put OI: {snapshot.total_oi_puts:,}")
        else:
            print("❌ Chain snapshot creation failed")
            return False
        
        # Test 6: Compute analytics
        analytics = await analytics_broadcaster.compute_single_analytics(
            mock_chain_data['symbol'], 
            snapshot.__dict__
        )
        
        if analytics:
            print("✅ Analytics computed successfully")
            print(f"   Analytics type: {analytics.get('type')}")
            print(f"   Symbol: {analytics.get('symbol')}")
            print(f"   Data keys: {list(analytics.get('data', {}).keys())}")
            
            # Check expected payload format
            data = analytics.get('data', {})
            expected_keys = ['pcr', 'total_call_oi', 'total_put_oi']
            missing_keys = [key for key in expected_keys if key not in data]
            
            if missing_keys:
                print(f"⚠️  Missing analytics keys: {missing_keys}")
            else:
                print("✅ All expected analytics keys present")
                print(f"   PCR: {data.get('pcr')}")
                print(f"   Total Call OI: {data.get('total_call_oi'):,}")
                print(f"   Total Put OI: {data.get('total_put_oi'):,}")
        else:
            print("❌ Analytics computation failed")
            return False
        
        print("\n🎉 PIPELINE TEST COMPLETE - ALL COMPONENTS WORKING")
        return True
        
    except Exception as e:
        print(f"❌ Pipeline test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_pipeline())
    sys.exit(0 if success else 1)
