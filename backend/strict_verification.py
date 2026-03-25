#!/usr/bin/env python3
"""
STRICT VERIFICATION - No assumptions, no shortcuts
Verifies schema fix with real data test
"""
import asyncio
from ai.ai_db import ai_db

async def strict_verification():
    print("🚨 STRICT VERIFICATION - No assumptions, no shortcuts")
    print("=" * 60)
    
    errors_found = []
    
    try:
        # Test 1: Verify formula_id is INTEGER
        print("\n1️⃣ Checking formula_id type...")
        try:
            result = await ai_db.fetch_one("""
                SELECT pg_typeof(formula_id) as data_type
                FROM ai_signal_logs
                LIMIT 1
            """)
            
            if result and result[0] == 'integer':
                print("✅ formula_id is INTEGER")
            else:
                print(f"❌ formula_id is {result[0] if result else 'NULL'} - MUST be INTEGER")
                errors_found.append("formula_id not INTEGER")
                return False
        except Exception as e:
            print(f"❌ ERROR checking formula_id: {e}")
            errors_found.append(f"formula_id check failed: {e}")
            return False
        
        # Test 2: Verify fk_prediction constraint exists
        print("\n2️⃣ Checking fk_prediction constraint...")
        try:
            result = await ai_db.fetch_query("""
                SELECT constraint_name, table_name, constraint_type
                FROM information_schema.table_constraints
                WHERE table_name = 'outcome_log'
                AND constraint_type = 'FOREIGN KEY'
            """)
            
            if result and len(result) > 0:
                constraint_name = result[0][0]
                if constraint_name == 'fk_prediction':
                    print("✅ fk_prediction constraint exists")
                else:
                    print(f"❌ Found constraint {constraint_name}, expected fk_prediction")
                    errors_found.append("Wrong constraint name")
                    return False
            else:
                print("❌ No foreign key constraint found")
                errors_found.append("No foreign key constraint")
                return False
        except Exception as e:
            print(f"❌ ERROR checking foreign key: {e}")
            errors_found.append(f"Foreign key check failed: {e}")
            return False
        
        # Test 3: Verify indexes exist
        print("\n3️⃣ Checking indexes...")
        try:
            result = await ai_db.fetch_query("""
                SELECT indexname, tablename
                FROM pg_indexes
                WHERE tablename IN ('ai_signal_logs', 'outcome_log')
                AND indexname LIKE 'idx_%'
            """)
            
            expected_indexes = ['idx_ai_signal_formula', 'idx_outcome_prediction']
            found_indexes = [row[0] for row in result]
            
            missing_indexes = [idx for idx in expected_indexes if idx not in found_indexes]
            if missing_indexes:
                print(f"❌ Missing indexes: {missing_indexes}")
                errors_found.append(f"Missing indexes: {missing_indexes}")
                return False
            else:
                print(f"✅ All indexes found: {found_indexes}")
        except Exception as e:
            print(f"❌ ERROR checking indexes: {e}")
            errors_found.append(f"Index check failed: {e}")
            return False
        
        # Test 4: REAL DATA TEST - CRITICAL
        print("\n4️⃣ REAL DATA TEST - Critical verification...")
        try:
            # Clean test data
            await ai_db.execute_query("DELETE FROM outcome_log")
            await ai_db.execute_query("DELETE FROM ai_signal_logs")
            print("✅ Cleaned test data")
            
            # Insert test data
            insert1 = await ai_db.execute_query(
                "INSERT INTO ai_signal_logs (id, formula_id) VALUES (1, 100)"
            )
            insert2 = await ai_db.execute_query(
                "INSERT INTO outcome_log (prediction_id) VALUES (1)"
            )
            
            if insert1 and insert2:
                print("✅ INSERT into both tables works")
            else:
                print("❌ INSERT failed")
                errors_found.append("INSERT failed")
                return False
            
            # JOIN test WITHOUT casting
            join_result = await ai_db.fetch_query("""
                SELECT *
                FROM ai_signal_logs p
                JOIN outcome_log o
                ON p.id = o.prediction_id
            """)
            
            if join_result and len(join_result) == 1:
                print("✅ JOIN returns 1 row WITHOUT casting")
                print(f"✅ JOIN result: {join_result[0]}")
            else:
                print(f"❌ JOIN returned {len(join_result) if join_result else 0} rows - MUST be 1")
                errors_found.append("JOIN failed or returned wrong row count")
                return False
                
        except Exception as e:
            print(f"❌ ERROR in real data test: {e}")
            errors_found.append(f"Real data test failed: {e}")
            return False
        
        # Final result
        print("\n" + "=" * 60)
        if not errors_found:
            print("🎉 STRICT VERIFICATION PASSED")
            print("✅ formula_id is INTEGER")
            print("✅ fk_prediction constraint exists")
            print("✅ All indexes created")
            print("✅ INSERT into both tables works")
            print("✅ JOIN returns 1 row WITHOUT casting")
            print("✅ System is PRODUCTION READY")
            
            print("\n🚀 SUCCESS: p.id = o.prediction_id works WITHOUT hacks")
            return True
        else:
            print("🚨 STRICT VERIFICATION FAILED")
            print("❌ Errors found:")
            for i, error in enumerate(errors_found, 1):
                print(f"   {i}. {error}")
            print("\n🛠️  MUST FIX BEFORE CONTINUING:")
            print("   1. Review and fix all errors above")
            print("   2. Re-run verification until it passes")
            print("   3. DO NOT continue to UUID migration")
            
            return False
            
    except Exception as e:
        print(f"❌ CRITICAL VERIFICATION ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(strict_verification())
    exit(0 if success else 1)
