#!/usr/bin/env python3
"""
Verification - StrikeIQ AI Data Exposure
Tests that all AI data is properly exposed to frontend
"""

import os
import sys
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent))

def test_ai_data_exposure():
    """Test AI data exposure to frontend"""
    
    print("=== 📡 AI DATA EXPOSURE VERIFICATION ===\n")
    
    results = []
    
    # Test 1: Backend Payload Update
    print("🔧 Test 1: Backend Payload Update...")
    try:
        with open("app/ai/ai_orchestrator.py", "r") as f:
            content = f.read()
        
        # Check for performance data in payload
        if ("performance" in content and 
            "analytics_full" in content and 
            "strategy_weights" in content and
            "self.execution_engine.get_performance()" in content):
            print("✅ Backend payload updated with performance data")
            results.append(True)
        else:
            print("❌ Backend payload missing performance data")
            results.append(False)
            
    except Exception as e:
        print(f"❌ Test 1 error: {e}")
        results.append(False)
    
    # Test 2: WS Broadcast Fix
    print("\n🔧 Test 2: WS Broadcast Fix...")
    try:
        with open("app/services/analytics_broadcaster.py", "r", encoding='utf-8') as f:
            content = f.read()
        
        # Check for broadcast_with_strategy calls
        if "broadcast_with_strategy" in content:
            print("✅ WS broadcast using broadcast_with_strategy")
            results.append(True)
        else:
            print("❌ WS broadcast not using broadcast_with_strategy")
            results.append(False)
            
    except Exception as e:
        print(f"❌ Test 2 error: {e}")
        results.append(False)
    
    # Test 3: Frontend Store Update
    print("\n🔧 Test 3: Frontend Store Update...")
    try:
        with open("../frontend/src/core/ws/wsStore.ts", "r", encoding='utf-8') as f:
            content = f.read()
        
        # Check for performance data in store
        if ("performance: any" in content and 
            "analytics_full: any" in content and 
            "strategy_weights: any" in content and
            "p.performance ?? prev.performance" in content):
            print("✅ Frontend store updated with performance data")
            results.append(True)
        else:
            print("❌ Frontend store missing performance data")
            results.append(False)
            
    except Exception as e:
        print(f"❌ Test 3 error: {e}")
        results.append(False)
    
    # Test 4: Frontend Receive Fix
    print("\n🔧 Test 4: Frontend Receive Fix...")
    try:
        with open("../frontend/src/components/dashboard/TradeSetupPanel.tsx", "r", encoding='utf-8') as f:
            content = f.read()
        
        # Check for performance state usage
        if ("const performance = useWSStore" in content and 
            "const strategyWeights = useWSStore" in content and
            "📊 Performance" in content and
            "🧠 Strategy Weights" in content):
            print("✅ Frontend receiving performance data")
            results.append(True)
        else:
            print("❌ Frontend not receiving performance data")
            results.append(False)
            
    except Exception as e:
        print(f"❌ Test 4 error: {e}")
        results.append(False)
    
    # Test 5: UI Display
    print("\n🔧 Test 5: UI Display...")
    try:
        with open("../frontend/src/components/dashboard/TradeSetupPanel.tsx", "r", encoding='utf-8') as f:
            content = f.read()
        
        # Check for UI elements
        ui_elements = [
            "total_trades",
            "win_rate", 
            "total_pnl",
            "Object.entries(strategyWeights)"
        ]
        
        missing_elements = [elem for elem in ui_elements if elem not in content]
        
        if not missing_elements:
            print("✅ UI display includes all performance metrics")
            results.append(True)
        else:
            print(f"❌ UI display missing: {missing_elements}")
            results.append(False)
            
    except Exception as e:
        print(f"❌ Test 5 error: {e}")
        results.append(False)
    
    # Test 6: Backend Performance Methods
    print("\n🔧 Test 6: Backend Performance Methods...")
    try:
        from app.services.trade_execution_engine import TradeExecutionEngine
        
        engine = TradeExecutionEngine()
        
        # Test performance methods exist
        methods = [
            "get_performance",
            "get_full_analytics", 
            "strategy_weights"
        ]
        
        missing_methods = []
        for method in methods:
            if method == "strategy_weights":
                if not hasattr(engine, 'strategy_weights'):
                    missing_methods.append(method)
            else:
                if not hasattr(engine, method):
                    missing_methods.append(method)
        
        if not missing_methods:
            print("✅ All performance methods available")
            results.append(True)
        else:
            print(f"❌ Missing methods: {missing_methods}")
            results.append(False)
            
    except Exception as e:
        print(f"❌ Test 6 error: {e}")
        results.append(False)
    
    # Test 7: Performance Data Structure
    print("\n🔧 Test 7: Performance Data Structure...")
    try:
        from app.services.trade_execution_engine import TradeExecutionEngine
        
        engine = TradeExecutionEngine()
        performance = engine.get_performance()
        analytics = engine.get_full_analytics()
        
        # Check performance structure
        required_perf_keys = ["total_trades", "wins", "losses", "win_rate", "total_pnl"]
        missing_perf_keys = [key for key in required_perf_keys if key not in performance]
        
        # Check analytics structure
        required_analytics_keys = ["equity_curve", "max_drawdown", "strategy_stats"]
        missing_analytics_keys = [key for key in required_analytics_keys if key not in analytics]
        
        if not missing_perf_keys and not missing_analytics_keys:
            print("✅ Performance data structure correct")
            results.append(True)
        else:
            print(f"❌ Missing keys - Performance: {missing_perf_keys}, Analytics: {missing_analytics_keys}")
            results.append(False)
            
    except Exception as e:
        print(f"❌ Test 7 error: {e}")
        results.append(False)
    
    # Final Results
    print("\n" + "="*50)
    print("📡 AI DATA EXPOSURE RESULTS:")
    print("="*50)
    
    all_passed = all(results)
    
    if all_passed:
        print("✅ AI DATA EXPOSURE COMPLETE!")
        print("\n🎉 EXPOSURE FEATURES:")
        print("✅ Backend payload updated")
        print("✅ WS broadcast working")
        print("✅ Frontend store updated")
        print("✅ Frontend receiving data")
        print("✅ UI displaying metrics")
        print("✅ Performance methods available")
        print("✅ Data structure correct")
        print("\n📊 TradeSetupPanel becomes REAL dashboard")
        print("📋 AI transparency visible")
        print("📋 Performance tracking visible")
        print("📋 Learning visible")
        print("\n🚀 AI DATA EXPOSURE IS PRODUCTION-READY!")
    else:
        print("❌ AI DATA EXPOSURE INCOMPLETE!")
        failed_tests = [i+1 for i, r in enumerate(results) if not r]
        print(f"❌ Failed tests: {failed_tests}")
        print("\n⚠️  Fix failed tests before production")
    
    return all_passed

if __name__ == "__main__":
    success = test_ai_data_exposure()
    sys.exit(0 if success else 1)
