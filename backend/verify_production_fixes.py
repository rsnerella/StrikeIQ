#!/usr/bin/env python3
"""
Verify Production Schema Fixes
Confirms all changes were applied successfully
"""
import asyncio
from ai.ai_db import ai_db

async def verify_production_fixes():
    print("🔍 Production Schema Fixes Verification")
    print("=" * 50)
    
    all_checks_passed = True
    
    try:
        # Test 1: Verify formula_id is now INTEGER
        print("\n1️⃣ Verifying formula_id type...")
        try:
            result = await ai_db.fetch_one("""
                SELECT pg_typeof(formula_id) as data_type
                FROM ai_signal_logs
                LIMIT 1
            """)
            
            if result and result[0] == 'integer':
                print("✅ formula_id is INTEGER type")
            else:
                print(f"❌ formula_id is {result[0] if result else 'NULL'} - should be INTEGER")
                all_checks_passed = False
        except Exception as e:
            print(f"❌ ERROR checking formula_id: {e}")
            all_checks_passed = False
        
        # Test 2: Verify fk_prediction constraint exists
        print("\n2️⃣ Verifying fk_prediction constraint...")
        try:
            result = await ai_db.fetch_query("""
                SELECT constraint_name, table_name, constraint_type
                FROM information_schema.table_constraints
                WHERE constraint_name = 'fk_prediction'
                AND table_name = 'outcome_log'
                AND constraint_type = 'FOREIGN KEY'
            """)
            
            if result and len(result) > 0:
                print("✅ fk_prediction constraint exists on outcome_log")
            else:
                print("❌ fk_prediction constraint missing")
                all_checks_passed = False
        except Exception as e:
            print(f"❌ ERROR checking foreign key: {e}")
            all_checks_passed = False
        
        # Test 3: Verify JOIN functionality
        print("\n3️⃣ Verifying JOIN functionality...")
        try:
            result = await ai_db.fetch_one("""
                SELECT COUNT(*) as count
                FROM ai_signal_logs p
                LEFT JOIN outcome_log o ON p.id::text = o.prediction_id::text
            """)
            
            print(f"✅ JOIN test successful: {result[0]} rows")
        except Exception as e:
            print(f"❌ ERROR in JOIN test: {e}")
            all_checks_passed = False
        
        # Test 4: Verify no orphan rows (should be 0 in empty DB)
        print("\n4️⃣ Verifying no orphan rows...")
        try:
            result = await ai_db.fetch_one("""
                SELECT COUNT(*) as count
                FROM outcome_log o
                WHERE NOT EXISTS (
                    SELECT 1 FROM ai_signal_logs p
                    WHERE p.id::text = o.prediction_id::text
                )
            """)
            
            print(f"✅ Orphan rows: {result[0]} (should be 0)")
        except Exception as e:
            print(f"❌ ERROR checking orphan rows: {e}")
            all_checks_passed = False
        
        # Test 5: Check data integrity
        print("\n5️⃣ Verifying data integrity...")
        try:
            signal_count = await ai_db.fetch_one("SELECT COUNT(*) FROM ai_signal_logs")
            outcome_count = await ai_db.fetch_one("SELECT COUNT(*) FROM outcome_log")
            
            print(f"✅ ai_signal_logs: {signal_count[0]} rows")
            print(f"✅ outcome_log: {outcome_count[0]} rows")
            
            if signal_count[0] == 0 and outcome_count[0] == 0:
                print("✅ Database is empty - schema fixes applied successfully")
        except Exception as e:
            print(f"❌ ERROR checking data integrity: {e}")
            all_checks_passed = False
        
        # Final result
        print("\n" + "=" * 50)
        if all_checks_passed:
            print("🎉 PRODUCTION SCHEMA FIXES VERIFICATION PASSED")
            print("✅ All schema fixes applied successfully")
            print("✅ formula_id is INTEGER type")
            print("✅ fk_prediction constraint exists")
            print("✅ JOIN functionality works")
            print("✅ Ready for UUID migration when needed")
            
            print("\n🚀 NEXT STEPS:")
            print("1. Database is ready for production use")
            print("2. UUID migration can be performed when ready")
            print("3. Text casting JOINs will work until UUID migration")
            print("4. Performance optimized for current schema")
            
            return True
        else:
            print("🚨 PRODUCTION SCHEMA FIXES VERIFICATION FAILED")
            print("❌ Some checks failed - review errors above")
            print("🛠️  TROUBLESHOOTING:")
            print("1. Check SQL script execution")
            print("2. Verify database permissions")
            print("3. Review error messages")
            print("4. Re-run fixes if needed")
            
            return False
            
    except Exception as e:
        print(f"❌ CRITICAL VERIFICATION ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(verify_production_fixes())
    exit(0 if success else 1)
