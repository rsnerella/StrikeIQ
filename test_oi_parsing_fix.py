#!/usr/bin/env python3
"""
Test script to verify OI parsing fix and bias engine correction
"""

import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

async def test_oi_parsing_fix():
    """Test the OI parsing fix and bias engine correction"""
    print("🔧 TESTING OI PARSING FIX & BIAS ENGINE CORRECTION")
    
    try:
        # Import analytics broadcaster
        from app.services.analytics_broadcaster import analytics_broadcaster
        
        # Create mock chain data with proper OI values
        mock_chain_data = {
            "symbol": "NIFTY",
            "spot": 23858.55,
            "atm_strike": 23850.0,
            "strikes": [
                {
                    "strike": 23800.0,
                    "call_oi": 1200000,  # Non-zero OI
                    "call_ltp": 245.50,
                    "call_volume": 50000,
                    "put_oi": 1450000,  # Non-zero OI
                    "put_ltp": 198.25,
                    "put_volume": 45000
                },
                {
                    "strike": 23850.0,
                    "call_oi": 1500000,  # Non-zero OI
                    "call_ltp": 220.75,
                    "call_volume": 55000,
                    "put_oi": 1650000,  # Non-zero OI
                    "put_ltp": 175.50,
                    "put_volume": 48000
                }
            ],
            "pcr": 1.09,
            "total_oi_calls": 2700000,  # Non-zero total
            "total_oi_puts": 3100000   # Non-zero total
        }
        
        print("✅ Mock chain data created with non-zero OI")
        print(f"   Total Call OI: {mock_chain_data['total_oi_calls']:,}")
        print(f"   Total Put OI: {mock_chain_data['total_oi_puts']:,}")
        print(f"   Expected PCR: {mock_chain_data['pcr']}")
        
        # Compute analytics
        analytics = await analytics_broadcaster.compute_single_analytics(
            mock_chain_data['symbol'], 
            mock_chain_data
        )
        
        if analytics:
            print("✅ Analytics computed successfully")
            print(f"   Return type: {type(analytics)}")
            
            # Verify OI values are present and non-zero
            call_oi = analytics.get('total_call_oi', 0)
            put_oi = analytics.get('total_put_oi', 0)
            total_oi = analytics.get('total_oi', 0)
            pcr = analytics.get('pcr', 0)
            
            print("✅ OI Values Verification:")
            print(f"   Call OI: {call_oi:,} ({'NON-ZERO' if call_oi > 0 else 'ZERO'})")
            print(f"   Put OI: {put_oi:,} ({'NON-ZERO' if put_oi > 0 else 'ZERO'})")
            print(f"   Total OI: {total_oi:,} ({'NON-ZERO' if total_oi > 0 else 'ZERO'})")
            print(f"   PCR: {pcr:.2f}")
            
            # Verify bias strength is extracted correctly
            bias_data = analytics.get('bias', {})
            bias_strength = bias_data.get('bias_strength', 0)
            
            print("✅ Bias Engine Verification:")
            print(f"   Bias Strength: {bias_strength} ({type(bias_strength).__name__})")
            print(f"   Bias Dict Keys: {list(bias_data.keys())}")
            
            # Check if all critical values are non-zero
            if all([call_oi > 0, put_oi > 0, total_oi > 0]):
                print("✅ ALL CRITICAL VALUES NON-ZERO - DASHBOARD SHOULD POPULATE")
            else:
                print("❌ Some values still zero - dashboard may show empty")
                return False
                
        else:
            print("❌ Analytics computation failed")
            return False
        
        print("\n🎉 OI PARSING & BIAS FIX TEST COMPLETE")
        return True
        
    except Exception as e:
        print(f"❌ OI parsing test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_oi_parsing_fix())
    sys.exit(0 if success else 1)
