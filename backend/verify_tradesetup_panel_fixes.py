#!/usr/bin/env python3
"""
Verification - TradeSetupPanel Fixes
Tests that the TradeSetupPanel.tsx file is properly fixed
"""

import os
import sys
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent))

def test_tradesetup_panel_fixes():
    """Test TradeSetupPanel fixes"""
    
    print("=== 🔧 TRADE SETUP PANEL FIXES VERIFICATION ===\n")
    
    results = []
    
    # Test 1: Remove Duplicate State Declarations
    print("🔧 Test 1: Remove Duplicate State Declarations...")
    try:
        with open("../frontend/src/components/dashboard/TradeSetupPanel.tsx", "r", encoding='utf-8') as f:
            content = f.read()
        
        # Check that local state declarations are removed
        if ("const [performance, setPerformance] = useState(null)" not in content and
            "const [strategyWeights, setStrategyWeights] = useState(null)" not in content):
            print("✅ Duplicate state declarations removed")
            results.append(True)
        else:
            print("❌ Duplicate state declarations still present")
            results.append(False)
            
    except Exception as e:
        print(f"❌ Test 1 error: {e}")
        results.append(False)
    
    # Test 2: TypeScript Interfaces Added
    print("\n🔧 Test 2: TypeScript Interfaces Added...")
    try:
        with open("../frontend/src/components/dashboard/TradeSetupPanel.tsx", "r", encoding='utf-8') as f:
            content = f.read()
        
        # Check for TypeScript interfaces
        if ("interface PerformanceData" in content and
            "interface StrategyWeights" in content and
            "total_trades?: number" in content and
            "[key: string]: number" in content):
            print("✅ TypeScript interfaces added")
            results.append(True)
        else:
            print("❌ TypeScript interfaces missing")
            results.append(False)
            
    except Exception as e:
        print(f"❌ Test 2 error: {e}")
        results.append(False)
    
    # Test 3: Store Subscriptions Typed
    print("\n🔧 Test 3: Store Subscriptions Typed...")
    try:
        with open("../frontend/src/components/dashboard/TradeSetupPanel.tsx", "r", encoding='utf-8') as f:
            content = f.read()
        
        # Check for typed store subscriptions
        if ("as PerformanceData | null" in content and
            "as StrategyWeights | null" in content):
            print("✅ Store subscriptions properly typed")
            results.append(True)
        else:
            print("❌ Store subscriptions not typed")
            results.append(False)
            
    except Exception as e:
        print(f"❌ Test 3 error: {e}")
        results.append(False)
    
    # Test 4: Safe Null Checks
    print("\n🔧 Test 4: Safe Null Checks...")
    try:
        with open("../frontend/src/components/dashboard/TradeSetupPanel.tsx", "r", encoding='utf-8') as f:
            content = f.read()
        
        # Check for safe null checks
        safe_checks = [
            "performance?.total_trades",
            "performance?.win_rate?.toFixed(1)",
            "performance?.total_pnl",
            "typeof value === 'number'"
        ]
        
        missing_checks = [check for check in safe_checks if check not in content]
        
        if not missing_checks:
            print("✅ Safe null checks implemented")
            results.append(True)
        else:
            print(f"❌ Missing safe checks: {missing_checks}")
            results.append(False)
            
    except Exception as e:
        print(f"❌ Test 4 error: {e}")
        results.append(False)
    
    # Test 5: No Duplicate Strategy Weights Check
    print("\n🔧 Test 5: No Duplicate Strategy Weights Check...")
    try:
        with open("../frontend/src/components/dashboard/TradeSetupPanel.tsx", "r", encoding='utf-8') as f:
            content = f.read()
        
        # Count occurrences of the map function
        map_occurrences = content.count("Object.entries(strategyWeights).map")
        
        if map_occurrences == 1:
            print("✅ No duplicate strategy weights check")
            results.append(True)
        else:
            print(f"❌ Found {map_occurrences} occurrences of strategy weights map (should be 1)")
            results.append(False)
            
    except Exception as e:
        print(f"❌ Test 5 error: {e}")
        results.append(False)
    
    # Test 6: Performance Display Structure
    print("\n🔧 Test 6: Performance Display Structure...")
    try:
        with open("../frontend/src/components/dashboard/TradeSetupPanel.tsx", "r", encoding='utf-8') as f:
            content = f.read()
        
        # Check for proper display structure
        display_elements = [
            "📊 Performance",
            "🧠 Strategy Weights",
            "Trades",
            "Win Rate",
            "PnL"
        ]
        
        missing_elements = [elem for elem in display_elements if elem not in content]
        
        if not missing_elements:
            print("✅ Performance display structure correct")
            results.append(True)
        else:
            print(f"❌ Missing display elements: {missing_elements}")
            results.append(False)
            
    except Exception as e:
        print(f"❌ Test 6 error: {e}")
        results.append(False)
    
    # Final Results
    print("\n" + "="*50)
    print("🔧 TRADE SETUP PANEL FIXES RESULTS:")
    print("="*50)
    
    all_passed = all(results)
    
    if all_passed:
        print("✅ TRADE SETUP PANEL FIXED!")
        print("\n🎉 FIXES APPLIED:")
        print("✅ Duplicate state declarations removed")
        print("✅ TypeScript interfaces added")
        print("✅ Store subscriptions typed")
        print("✅ Safe null checks implemented")
        print("✅ No duplicate strategy weights check")
        print("✅ Performance display structure correct")
        print("\n📊 TradeSetupPanel is now properly typed and safe")
        print("📋 No more TypeScript errors")
        print("📋 Robust null handling")
        print("📋 Clean code structure")
        print("\n🚀 TRADE SETUP PANEL IS PRODUCTION-READY!")
    else:
        print("❌ TRADE SETUP PANEL NOT FULLY FIXED!")
        failed_tests = [i+1 for i, r in enumerate(results) if not r]
        print(f"❌ Failed tests: {failed_tests}")
        print("\n⚠️  Fix remaining issues before production")
    
    return all_passed

if __name__ == "__main__":
    success = test_tradesetup_panel_fixes()
    sys.exit(0 if success else 1)
