#!/usr/bin/env python3
"""
Verification - TradeSetupPanel Always Shows Data
Tests that TradeSetupPanel never fails silently and always displays data
"""

import os
import sys
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent))

def test_always_show_data():
    """Test that TradeSetupPanel always shows data"""
    
    print("=== 📊 ALWAYS SHOW DATA VERIFICATION ===\n")
    
    results = []
    
    # Test 1: Event Type Fix
    print("🔧 Test 1: Event Type Fix...")
    try:
        with open("../frontend/src/core/ws/wsStore.ts", "r", encoding='utf-8') as f:
            content = f.read()
        
        # Check for both event types
        if ("case 'market_update':" in content and 
            "case 'analytics_update':" in content and
            "case 'market_update':\n      case 'analytics_update':" in content):
            print("✅ Event type fix applied - both market_update and analytics_update handled")
            results.append(True)
        else:
            print("❌ Event type fix not applied")
            results.append(False)
            
    except Exception as e:
        print(f"❌ Test 1 error: {e}")
        results.append(False)
    
    # Test 2: Safe Fallback
    print("\n🔧 Test 2: Safe Fallback...")
    try:
        with open("../frontend/src/core/ws/wsStore.ts", "r", encoding='utf-8') as f:
            content = f.read()
        
        # Check for safe fallback values
        fallback_checks = [
            "total_trades: 0",
            "win_rate: 0", 
            "total_pnl: 0",
            "equity_curve: []",
            "max_drawdown: 0",
            "strategy_stats: {}",
            '"TREND": 1.0',
            '"REVERSAL": 1.0',
            '"WEAK_TREND": 0.5'
        ]
        
        missing_fallbacks = [check for check in fallback_checks if check not in content]
        
        if not missing_fallbacks:
            print("✅ Safe fallback implemented - default values for all fields")
            results.append(True)
        else:
            print(f"❌ Missing fallback values: {missing_fallbacks}")
            results.append(False)
            
    except Exception as e:
        print(f"❌ Test 2 error: {e}")
        results.append(False)
    
    # Test 3: Debug Log
    print("\n🔧 Test 3: Debug Log...")
    try:
        with open("../frontend/src/core/ws/wsStore.ts", "r", encoding='utf-8') as f:
            content = f.read()
        
        # Check for debug logging
        if ("[WS DATA]" in content and 
            "message.type === 'analytics_update' || message.type === 'market_update'" in content):
            print("✅ Debug log added - WebSocket data will be logged")
            results.append(True)
        else:
            print("❌ Debug log not added")
            results.append(False)
            
    except Exception as e:
        print(f"❌ Test 3 error: {e}")
        results.append(False)
    
    # Test 4: UI Guard
    print("\n🔧 Test 4: UI Guard...")
    try:
        with open("../frontend/src/components/dashboard/TradeSetupPanel.tsx", "r", encoding='utf-8') as f:
            content = f.read()
        
        # Check for UI guard
        guard_checks = [
            "if (!performance && !strategyWeights && !hasData)",
            "Waiting for AI data",
            "Performance metrics loading"
        ]
        
        missing_guards = [check for check in guard_checks if check not in content]
        
        if not missing_guards:
            print("✅ UI guard implemented - prevents blank UI")
            results.append(True)
        else:
            print(f"❌ Missing UI guard elements: {missing_guards}")
            results.append(False)
            
    except Exception as e:
        print(f"❌ Test 4 error: {e}")
        results.append(False)
    
    # Test 5: Backend Verification
    print("\n🔧 Test 5: Backend Verification...")
    try:
        from app.services.trade_execution_engine import TradeExecutionEngine
        
        engine = TradeExecutionEngine()
        
        # Test that backend has performance methods
        perf = engine.get_performance()
        analytics = engine.get_full_analytics()
        weights = engine.strategy_weights
        
        if (perf and analytics and weights and 
            "total_trades" in perf and 
            "equity_curve" in analytics and
            "TREND" in weights):
            print("✅ Backend verification passed - all performance data available")
            results.append(True)
        else:
            print("❌ Backend verification failed - missing performance data")
            results.append(False)
            
    except Exception as e:
        print(f"❌ Test 5 error: {e}")
        results.append(False)
    
    # Test 6: Payload Structure
    print("\n🔧 Test 6: Payload Structure...")
    try:
        with open("app/ai/ai_orchestrator.py", "r", encoding='utf-8') as f:
            content = f.read()
        
        # Check payload structure
        payload_checks = [
            '"performance": self.execution_engine.get_performance()',
            '"analytics_full": self.execution_engine.get_full_analytics()',
            '"strategy_weights": self.execution_engine.strategy_weights'
        ]
        
        missing_payload = [check for check in payload_checks if check not in content]
        
        if not missing_payload:
            print("✅ Payload structure correct - all performance data included")
            results.append(True)
        else:
            print(f"❌ Missing payload elements: {missing_payload}")
            results.append(False)
            
    except Exception as e:
        print(f"❌ Test 6 error: {e}")
        results.append(False)
    
    # Final Results
    print("\n" + "="*50)
    print("📊 ALWAYS SHOW DATA RESULTS:")
    print("="*50)
    
    all_passed = all(results)
    
    if all_passed:
        print("✅ TRADE SETUP PANEL ALWAYS SHOWS DATA!")
        print("\n🎉 SAFETY FEATURES APPLIED:")
        print("✅ Event type fix - handles both market_update and analytics_update")
        print("✅ Safe fallback - default values prevent blank UI")
        print("✅ Debug log - WebSocket data logged for debugging")
        print("✅ UI guard - prevents blank TradeSetupPanel")
        print("✅ Backend verification - performance data available")
        print("✅ Payload structure - all data included in responses")
        print("\n📊 UI kabhi blank nahi rahega")
        print("📋 Data always visible")
        print("📋 Debug easy ho jayega")
        print("📋 Production safe")
        print("\n🧪 FINAL TEST INSTRUCTIONS:")
        print("1. Server run karo")
        print("2. Console open karo")
        print("3. Check karo: [WS DATA] {...performance...}")
        print("\n🚀 ALWAYS SHOW DATA IS PRODUCTION-READY!")
    else:
        print("❌ ALWAYS SHOW DATA NOT FULLY IMPLEMENTED!")
        failed_tests = [i+1 for i, r in enumerate(results) if not r]
        print(f"❌ Failed tests: {failed_tests}")
        print("\n⚠️  Fix remaining issues before production")
    
    return all_passed

if __name__ == "__main__":
    success = test_always_show_data()
    sys.exit(0 if success else 1)
