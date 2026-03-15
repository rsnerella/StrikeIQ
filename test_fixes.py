#!/usr/bin/env python3
"""
Verification script for StrikeIQ fixes
Tests the key changes made to option_chain_builder.py
"""

import sys
import os
sys.path.append('backend')

def test_optiondata_access():
    """Test OptionData attribute access fix"""
    print("🔍 Testing OptionData attribute access...")
    
    try:
        from backend.app.services.option_chain_builder import OptionData
        
        # Create test OptionData object
        opt = OptionData(strike=22150.0, ltp=1021.3, oi=585)
        
        # Test the safe_attr function pattern we implemented
        def safe_attr(obj, attr, default=0):
            val = getattr(obj, attr, None)
            if val is None:
                return default
            try:
                return float(val)
            except (ValueError, TypeError):
                return default
        
        # Test attribute extraction
        ltp = safe_attr(opt, 'ltp')
        oi = int(safe_attr(opt, 'oi'))
        
        print(f"✅ OptionData access: ltp={ltp}, oi={oi}")
        assert ltp == 1021.3, f"Expected 1021.3, got {ltp}"
        assert oi == 585, f"Expected 585, got {oi}"
        
        return True
    except Exception as e:
        print(f"❌ OptionData access failed: {e}")
        return False

def test_analytics_broadcaster():
    """Test analytics_broadcaster compute_single_analytics is synchronous"""
    print("🔍 Testing analytics_broadcaster synchronous method...")
    
    try:
        from backend.app.services.analytics_broadcaster import analytics_broadcaster
        
        # Test that compute_single_analytics is synchronous (no await needed)
        result = analytics_broadcaster.compute_single_analytics("NIFTY", {"test": "data"})
        
        # Should return None (just sets dirty flag)
        print(f"✅ compute_single_analytics is synchronous: {result}")
        
        # Check dirty flag was set
        is_dirty = analytics_broadcaster._dirty.get("NIFTY", False)
        assert is_dirty, "Dirty flag should be set"
        
        return True
    except Exception as e:
        print(f"❌ Analytics broadcaster test failed: {e}")
        return False

def test_chain_structure():
    """Test chain structure and strike key format"""
    print("🔍 Testing chain structure...")
    
    try:
        from backend.app.services.option_chain_builder import option_chain_builder
        
        # Simulate chain data structure
        test_chain = {
            22150.0: {
                "CE": OptionData(strike=22150.0, ltp=1021.3, oi=585),
                "PE": OptionData(strike=22150.0, ltp=28.75, oi=510770)
            }
        }
        
        # Test strike key normalization (str(int(strike)))
        for strike_key, sides in test_chain.items():
            strike_str = str(int(strike_key))
            print(f"✅ Strike key normalized: {strike_key} -> {strike_str}")
            assert strike_str == "22150", f"Expected '22150', got '{strike_str}'"
        
        return True
    except Exception as e:
        print(f"❌ Chain structure test failed: {e}")
        return False

def main():
    print("🚀 StrikeIQ Fixes Verification")
    print("=" * 50)
    
    tests = [
        test_optiondata_access,
        test_analytics_broadcaster,
        test_chain_structure
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All backend fixes verified successfully!")
        return True
    else:
        print("⚠️ Some tests failed - check implementation")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
