#!/usr/bin/env python3
"""
Simple Schema Check - No complex queries
Just checks basic schema consistency
"""
import asyncio
from ai.ai_db import ai_db

async def simple_schema_check():
    try:
        print("🔍 Simple Schema Check")
        
        # Test 1: Check paper_trade_log columns exist
        print("\n1️⃣ Checking paper_trade_log columns...")
        try:
            columns_result = await ai_db.fetch_query("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'paper_trade_log' 
                ORDER BY column_name
            """)
            columns = [row[0] for row in columns_result]
            print(f"✅ Found columns: {columns}")
            
            # Check for expected columns
            expected = ['id', 'prediction_id', 'symbol', 'strike_price', 'entry_price', 
                      'exit_price', 'quantity', 'pnl', 'trade_type', 'timestamp']
            missing = [col for col in expected if col not in columns]
            if missing:
                print(f"❌ MISSING: {missing}")
                return False
            else:
                print("✅ All expected columns present")
        except Exception as e:
            print(f"❌ ERROR: {e}")
            return False
        
        # Test 2: Test simple paper_trade_log query
        print("\n2️⃣ Testing paper_trade_log query...")
        try:
            test_result = await ai_db.fetch_query("""
                SELECT COUNT(*) as count
                FROM paper_trade_log
                WHERE timestamp >= NOW() - INTERVAL '7 days'
            """)
            print(f"✅ Query works: {test_result[0][0]} trades in last 7 days")
        except Exception as e:
            print(f"❌ ERROR: {e}")
            return False
        
        # Test 3: Test text casting JOIN
        print("\n3️⃣ Testing text casting JOIN...")
        try:
            join_result = await ai_db.fetch_one("""
                SELECT COUNT(*) as count
                FROM ai_signal_logs p 
                LEFT JOIN outcome_log o ON p.id::text = o.prediction_id::text
                LIMIT 1
            """)
            print(f"✅ Text casting JOIN works: {join_result[0]} rows")
        except Exception as e:
            print(f"❌ ERROR: {e}")
            return False
        
        print("\n🎉 SIMPLE SCHEMA CHECK PASSED")
        print("✅ Basic queries work")
        print("✅ Expected columns exist")
        print("✅ Text casting JOIN works")
        print("✅ Ready for current state")
        return True
        
    except Exception as e:
        print(f"❌ CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(simple_schema_check())
    exit(0 if success else 1)
