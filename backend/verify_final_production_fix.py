#!/usr/bin/env python3
"""
Verify Final Production Schema Fixes
Confirms all production fixes applied successfully
"""
import asyncio
from ai.ai_db import ai_db

async def verify_final_production_fix():
    print("🔍 Final Production Schema Fix Verification")
    print("=" * 60)
    
    all_checks_passed = True
    results = {}
    
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
                print("✅ formula_id is INTEGER type")
                results['formula_id_type'] = 'PASS'
            else:
                print(f"❌ formula_id is {result[0] if result else 'NULL'} - should be INTEGER")
                results['formula_id_type'] = 'FAIL'
                all_checks_passed = False
        except Exception as e:
            print(f"❌ ERROR checking formula_id: {e}")
            results['formula_id_type'] = 'ERROR'
            all_checks_passed = False
        
        # Test 2: Verify fk_prediction constraint exists
        print("\n2️⃣ Checking fk_prediction constraint...")
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
                results['fk_prediction'] = 'PASS'
            else:
                print("❌ fk_prediction constraint missing")
                results['fk_prediction'] = 'FAIL'
                all_checks_passed = False
        except Exception as e:
            print(f"❌ ERROR checking foreign key: {e}")
            results['fk_prediction'] = 'ERROR'
            all_checks_passed = False
        
        # Test 3: Verify prediction_id_uuid column exists
        print("\n3️⃣ Checking prediction_id_uuid column...")
        try:
            result = await ai_db.fetch_query("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'paper_trade_log'
                AND column_name = 'prediction_id_uuid'
            """)
            
            if result and len(result) > 0:
                print(f"✅ prediction_id_uuid column exists: {result[0][1]}")
                results['prediction_id_uuid'] = 'PASS'
            else:
                print("❌ prediction_id_uuid column missing")
                results['prediction_id_uuid'] = 'FAIL'
                all_checks_passed = False
        except Exception as e:
            print(f"❌ ERROR checking prediction_id_uuid: {e}")
            results['prediction_id_uuid'] = 'ERROR'
            all_checks_passed = False
        
        # Test 4: Verify indexes created
        print("\n4️⃣ Checking indexes...")
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
            
            if not missing_indexes:
                print(f"✅ All expected indexes created: {found_indexes}")
                results['indexes'] = 'PASS'
            else:
                print(f"❌ Missing indexes: {missing_indexes}")
                results['indexes'] = 'FAIL'
                all_checks_passed = False
        except Exception as e:
            print(f"❌ ERROR checking indexes: {e}")
            results['indexes'] = 'ERROR'
            all_checks_passed = False
        
        # Test 5: Verify JOIN functionality
        print("\n5️⃣ Checking JOIN functionality...")
        try:
            result = await ai_db.fetch_one("""
                SELECT COUNT(*) as count
                FROM ai_signal_logs p
                LEFT JOIN outcome_log o ON p.id::text = o.prediction_id::text
            """)
            
            print(f"✅ JOIN test successful: {result[0]} rows")
            results['join_functionality'] = 'PASS'
        except Exception as e:
            print(f"❌ ERROR in JOIN test: {e}")
            results['join_functionality'] = 'ERROR'
            all_checks_passed = False
        
        # Test 6: Check table statistics
        print("\n6️⃣ Checking table statistics...")
        try:
            signal_count = await ai_db.fetch_one("SELECT COUNT(*) FROM ai_signal_logs")
            outcome_count = await ai_db.fetch_one("SELECT COUNT(*) FROM outcome_log")
            paper_count = await ai_db.fetch_one("SELECT COUNT(*) FROM paper_trade_log")
            
            print(f"✅ ai_signal_logs: {signal_count[0]} rows")
            print(f"✅ outcome_log: {outcome_count[0]} rows")
            print(f"✅ paper_trade_log: {paper_count[0]} rows")
            
            results['table_stats'] = 'PASS'
        except Exception as e:
            print(f"❌ ERROR checking table stats: {e}")
            results['table_stats'] = 'ERROR'
            all_checks_passed = False
        
        # Final result
        print("\n" + "=" * 60)
        print("📊 VERIFICATION RESULTS:")
        for check, status in results.items():
            icon = "✅" if status == 'PASS' else "❌" if status == 'FAIL' else "⚠️"
            print(f"  {icon} {check}: {status}")
        
        print("\n" + "=" * 60)
        if all_checks_passed:
            print("🎉 FINAL PRODUCTION SCHEMA FIXES VERIFICATION PASSED")
            print("✅ All schema fixes applied successfully")
            print("✅ Database is production-ready")
            print("✅ Ready for data insertion")
            print("✅ Prepared for future UUID migration")
            
            print("\n🚀 NEXT STEPS:")
            print("1. Remove text casting from JOIN queries in code")
            print("2. Start inserting real data")
            print("3. Monitor performance with new indexes")
            print("4. Plan UUID migration when needed")
            
            return True
        else:
            print("🚨 FINAL PRODUCTION SCHEMA FIXES VERIFICATION FAILED")
            print("❌ Some checks failed - review errors above")
            print("🛠️  TROUBLESHOOTING:")
            print("1. Ensure SQL script executed completely")
            print("2. Check database permissions")
            print("3. Review failed checks")
            print("4. Re-run SQL script if needed")
            
            return False
            
    except Exception as e:
        print(f"❌ CRITICAL VERIFICATION ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(verify_final_production_fix())
    exit(0 if success else 1)
