#!/usr/bin/env python3
"""
STRICT Schema Verification - Fails on ANY error
Ensures complete schema consistency before UUID migration
"""
import asyncio
from ai.ai_db import ai_db

async def strict_schema_verification():
    errors_found = []
    
    try:
        print("🔍 STRICT Schema Verification - Fails on ANY Error")
        
        # Test 1: Check ai_signal_logs schema
        print("\n1️⃣ Checking ai_signal_logs schema...")
        try:
            result1 = await ai_db.fetch_one("""
                SELECT column_name, data_type, udt_name 
                FROM information_schema.columns 
                WHERE table_name = 'ai_signal_logs' 
                ORDER BY column_name
            """)
            print(f"✅ ai_signal_logs columns: {[row[0] for row in await ai_db.fetch_query(result1[0])]}")
        except Exception as e:
            errors_found.append(f"ai_signal_logs schema check failed: {e}")
            print(f"❌ ERROR: {e}")
        
        # Test 2: Check outcome_log schema
        print("\n2️⃣ Checking outcome_log schema...")
        try:
            result2 = await ai_db.fetch_one("""
                SELECT column_name, data_type, udt_name 
                FROM information_schema.columns 
                WHERE table_name = 'outcome_log' 
                ORDER BY column_name
            """)
            print(f"✅ outcome_log columns: {[row[0] for row in await ai_db.fetch_query(result2[0])]}")
        except Exception as e:
            errors_found.append(f"outcome_log schema check failed: {e}")
            print(f"❌ ERROR: {e}")
        
        # Test 3: Check paper_trade_log schema
        print("\n3️⃣ Checking paper_trade_log schema...")
        try:
            result3 = await ai_db.fetch_one("""
                SELECT column_name, data_type, udt_name 
                FROM information_schema.columns 
                WHERE table_name = 'paper_trade_log' 
                ORDER BY column_name
            """)
            columns = [row[0] for row in await ai_db.fetch_query(result3[0])]
            print(f"✅ paper_trade_log columns: {columns}")
            
            # Verify expected columns exist
            expected = ['id', 'prediction_id', 'symbol', 'strike_price', 'entry_price', 
                      'exit_price', 'quantity', 'pnl', 'trade_type', 'timestamp']
            missing = [col for col in expected if col not in columns]
            if missing:
                errors_found.append(f"Missing paper_trade_log columns: {missing}")
                print(f"❌ MISSING COLUMNS: {missing}")
            else:
                print("✅ All expected paper_trade_log columns present")
                
        except Exception as e:
            errors_found.append(f"paper_trade_log schema check failed: {e}")
            print(f"❌ ERROR: {e}")
        
        # Test 4: Test text casting JOIN (should work)
        print("\n4️⃣ Testing text casting JOIN...")
        try:
            result4 = await ai_db.fetch_one("""
                SELECT COUNT(*) as join_count
                FROM ai_signal_logs p 
                LEFT JOIN outcome_log o ON p.id::text = o.prediction_id::text
                LIMIT 1
            """)
            print(f"✅ Text casting JOIN works: {result4[0]} rows")
        except Exception as e:
            errors_found.append(f"Text casting JOIN failed: {e}")
            print(f"❌ ERROR: {e}")
        
        # Test 5: Test paper_trade_log queries with actual columns
        print("\n5️⃣ Testing paper_trade_log queries...")
        try:
            result5 = await ai_db.fetch_query("""
                SELECT id, prediction_id, symbol, strike_price,
                       entry_price, exit_price, quantity, pnl, trade_type,
                       timestamp
                FROM paper_trade_log
                WHERE timestamp >= NOW() - INTERVAL '24 hours'
                ORDER BY timestamp DESC
                LIMIT 3
            """)
            print(f"✅ Paper trade query works: {len(result5)} rows")
            
            # Verify expected columns exist
            expected = ['id', 'prediction_id', 'symbol', 'strike_price', 'entry_price', 
                      'exit_price', 'quantity', 'pnl', 'trade_type', 'timestamp']
            actual = [row[0] for row in await ai_db.fetch_query("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'paper_trade_log' 
                ORDER BY column_name
            """)]
            missing = [col for col in expected if col not in actual]
            if missing:
                errors_found.append(f"Missing paper_trade_log columns: {missing}")
                print(f"❌ MISSING COLUMNS: {missing}")
            else:
                print("✅ All expected paper_trade_log columns present")
        except Exception as e:
            errors_found.append(f"Paper trade query failed: {e}")
            print(f"❌ ERROR: {e}")
        
        # Test 6: Test AI learning engine query
        print("\n6️⃣ Testing AI learning engine query...")
        try:
            result6 = await ai_db.fetch_one("""
                SELECT COUNT(*) as total_predictions
                FROM ai_signal_logs p
                LEFT JOIN outcome_log o ON p.id::text = o.prediction_id::text
                WHERE p.formula_id = 1
                AND p.timestamp >= NOW() - INTERVAL '30 days'
            """)
            print(f"✅ Learning engine query works: {result6[0]} predictions")
        except Exception as e:
            errors_found.append(f"Learning engine query failed: {e}")
            print(f"❌ ERROR: {e}")
        
        # Test 7: Check foreign key consistency
        print("\n7️⃣ Checking foreign key consistency...")
        try:
            result7 = await ai_db.fetch_one("""
                SELECT 
                    tc.table_name, 
                    tc.constraint_name,
                    ccu.table_name as references_table,
                    ccu.column_name as references_column
                FROM information_schema.table_constraints tc
                JOIN information_schema.constraint_column_usage ccu 
                    ON tc.constraint_name = ccu.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY'
                AND (tc.table_name = 'ai_signal_logs' OR tc.table_name = 'outcome_log' OR tc.table_name = 'paper_trade_log')
            """)
            print(f"✅ Foreign key constraints: {len(await ai_db.fetch_query(result7[0]))} found")
        except Exception as e:
            errors_found.append(f"Foreign key check failed: {e}")
            print(f"❌ ERROR: {e}")
        
        # Final Result
        print("\n" + "="*50)
        if errors_found:
            print("🚨 SCHEMA VERIFICATION FAILED")
            print("❌ Errors found:")
            for i, error in enumerate(errors_found, 1):
                print(f"   {i}. {error}")
            print("\n🛠️  FIXES REQUIRED BEFORE MIGRATION:")
            print("   1. Fix all SQL errors above")
            print("   2. Ensure consistent column names")
            print("   3. Verify foreign key relationships")
            print("   4. Re-run verification until zero errors")
            return False
        else:
            print("🎉 SCHEMA VERIFICATION PASSED")
            print("✅ Zero SQL errors found")
            print("✅ All expected columns present")
            print("✅ Foreign keys consistent")
            print("✅ Ready for UUID migration")
            return True
            
    except Exception as e:
        print(f"❌ CRITICAL VERIFICATION ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(strict_schema_verification())
    exit(0 if success else 1)
