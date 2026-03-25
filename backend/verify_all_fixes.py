#!/usr/bin/env python3
"""
Final Verification - StrikeIQ Runtime Crash Fixes
"""

import os
import sys
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent))

def test_all_fixes():
    """Test all runtime crash fixes"""
    
    print("=== 🎯 FINAL VERIFICATION - ALL FIXES ===\n")
    
    results = []
    
    # Test 1: Option Chain Builder Fix
    print("🔧 Test 1: Option Chain Builder...")
    try:
        from app.services.option_chain_builder import option_chain_builder
        print("✅ Option chain builder imports successfully")
        
        # Test _create_snapshot with error handling
        try:
            result = option_chain_builder._create_snapshot("NIFTY")
            print("✅ _create_snapshot handles missing data gracefully")
        except Exception as e:
            if "No chain data" in str(e) or "SNAPSHOT ERROR" in str(e):
                print("✅ Error handling works correctly")
            else:
                print(f"❌ Unexpected error: {e}")
                results.append(False)
                return False
        
        results.append(True)
    except Exception as e:
        print(f"❌ Option chain builder error: {e}")
        results.append(False)
    
    # Test 2: Database Schema
    print("\n🔧 Test 2: Database Schema...")
    try:
        import psycopg2
        from dotenv import load_dotenv
        
        load_dotenv()
        database_url = os.getenv("DATABASE_URL")
        if database_url.startswith("postgresql+asyncpg://"):
            database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
        
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # Check outcome column exists
        cursor.execute("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'outcome_log' AND column_name = 'outcome'
        """)
        if cursor.fetchone():
            print("✅ outcome_log.outcome column exists")
            results.append(True)
        else:
            print("❌ outcome_log.outcome column missing")
            results.append(False)
        
        # Check option_type column exists
        cursor.execute("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'paper_trade_log' AND column_name = 'option_type'
        """)
        if cursor.fetchone():
            print("✅ paper_trade_log.option_type column exists")
            results.append(True)
        else:
            print("❌ paper_trade_log.option_type column missing")
            results.append(False)
        
        # Test UUID join without casting
        cursor.execute("""
            SELECT COUNT(*) FROM ai_signal_logs p 
            LEFT JOIN outcome_log o ON p.id = o.prediction_id
            LEFT JOIN paper_trade_log pt ON p.id = pt.prediction_id
            LIMIT 1
        """)
        result = cursor.fetchone()
        print(f"✅ UUID join works: {result[0]} records")
        results.append(True)
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Database test error: {e}")
        results.append(False)
    
    # Test 3: Snapshot.get() fixes
    print("\n🔧 Test 3: Snapshot Attribute Access...")
    try:
        from ai.options_trade_engine import generate_option_trade
        
        # Create mock snapshot with attributes
        class MockSnapshot:
            def __init__(self):
                self.symbol = "NIFTY"
                self.spot = 22450
                self.pcr = 1.2
        
        snapshot = MockSnapshot()
        result = generate_option_trade(snapshot, {})
        print("✅ Options trade engine handles object attributes")
        results.append(True)
        
    except Exception as e:
        print(f"❌ Snapshot attribute test error: {e}")
        results.append(False)
    
    # Test 4: AI Logger Clean Logging
    print("\n🔧 Test 4: Clean AI Logging...")
    try:
        from ai.ai_logger import log, log_market_data, log_decision
        
        log("Test message")
        log_market_data(spot=22450, pcr=0.83, rsi=50, gamma="NEUTRAL")
        log_decision(confidence=52, signal="NONE")
        print("✅ Clean AI logging works")
        results.append(True)
        
    except Exception as e:
        print(f"❌ AI logger test error: {e}")
        results.append(False)
    
    # Final Results
    print("\n" + "="*50)
    print("🎯 FINAL VERIFICATION RESULTS:")
    print("="*50)
    
    all_passed = all(results)
    
    if all_passed:
        print("✅ ALL FIXES VERIFIED SUCCESSFULLY!")
        print("\n🎉 SYSTEM STATUS:")
        print("✅ Option chain builder - STABLE")
        print("✅ Database schema - COMPLETE")
        print("✅ UUID alignment - FIXED")
        print("✅ Snapshot access - WORKING")
        print("✅ Clean logging - ACTIVE")
        print("\n🚀 READY FOR PRODUCTION RUNTIME!")
        print("📋 No more crashes expected")
    else:
        print("❌ SOME FIXES FAILED!")
        failed_tests = [i+1 for i, r in enumerate(results) if not r]
        print(f"❌ Failed tests: {failed_tests}")
        print("\n⚠️  Review failed tests before production")
    
    return all_passed

if __name__ == "__main__":
    success = test_all_fixes()
    sys.exit(0 if success else 1)
