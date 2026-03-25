#!/usr/bin/env python3
"""
Validate Current State Before Production Schema Fixes
Checks data integrity and identifies issues that need cleanup
"""
import asyncio
from ai.ai_db import ai_db

async def validate_before_production_fix():
    print("🔍 Pre-Production Schema Validation")
    print("=" * 50)
    
    issues_found = []
    
    try:
        # Test 1: Check current formula_id type and values
        print("\n1️⃣ Checking formula_id current state...")
        try:
            # Check type
            type_result = await ai_db.fetch_one("""
                SELECT pg_typeof(formula_id) as data_type
                FROM ai_signal_logs
                LIMIT 1
            """)
            print(f"Current formula_id type: {type_result[0]}")
            
            # Check for invalid values
            invalid_result = await ai_db.fetch_one("""
                SELECT COUNT(*) as count
                FROM ai_signal_logs
                WHERE formula_id IS NOT NULL
                AND formula_id !~ '^[0-9]+$'
            """)
            print(f"Invalid formula_id values: {invalid_result[0]}")
            
            if invalid_result[0] > 0:
                issues_found.append(f"Found {invalid_result[0]} invalid formula_id values")
                
                # Show sample invalid values
                sample_invalid = await ai_db.fetch_query("""
                    SELECT id, formula_id, metadata
                    FROM ai_signal_logs
                    WHERE formula_id IS NOT NULL
                    AND formula_id !~ '^[0-9]+'
                    LIMIT 3
                """)
                for row in sample_invalid:
                    print(f"  - ID: {row[0]}, Invalid formula_id: '{row[1]}'")
        except Exception as e:
            issues_found.append(f"formula_id check failed: {e}")
            print(f"❌ ERROR: {e}")
        
        # Test 2: Check for orphan outcome_log rows
        print("\n2️⃣ Checking orphan outcome_log rows...")
        try:
            orphan_result = await ai_db.fetch_one("""
                SELECT COUNT(*) as count
                FROM outcome_log o
                LEFT JOIN ai_signal_logs p ON o.prediction_id::text = p.id::text
                WHERE p.id IS NULL
            """)
            print(f"Orphan outcome_log rows: {orphan_result[0]}")
            
            if orphan_result[0] > 0:
                issues_found.append(f"Found {orphan_result[0]} orphan outcome_log rows")
                
                # Show sample orphan rows
                sample_orphans = await ai_db.fetch_query("""
                    SELECT o.id, o.prediction_id, o.outcome, o.evaluation_time
                    FROM outcome_log o
                    LEFT JOIN ai_signal_logs p ON o.prediction_id::text = p.id::text
                    WHERE p.id IS NULL
                    LIMIT 3
                """)
                for row in sample_orphans:
                    print(f"  - ID: {row[0]}, prediction_id: {row[1]}, outcome: {row[2]}")
        except Exception as e:
            issues_found.append(f"Orphan check failed: {e}")
            print(f"❌ ERROR: {e}")
        
        # Test 3: Check current foreign key constraints
        print("\n3️⃣ Checking current foreign key constraints...")
        try:
            fk_result = await ai_db.fetch_query("""
                SELECT tc.constraint_name, tc.table_name, ccu.table_name as references_table
                FROM information_schema.table_constraints tc
                JOIN information_schema.constraint_column_usage ccu 
                    ON tc.constraint_name = ccu.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY'
                AND (tc.table_name = 'ai_signal_logs' OR tc.table_name = 'outcome_log')
            """)
            print(f"Current foreign key constraints: {len(fk_result)}")
            for row in fk_result:
                print(f"  - {row[0]} on {row[1]} → {row[2]}")
                
            # Check if fk_prediction exists
            fk_exists = any(row[0] == 'fk_prediction' for row in fk_result)
            if not fk_exists:
                issues_found.append("fk_prediction constraint does not exist")
        except Exception as e:
            issues_found.append(f"Foreign key check failed: {e}")
            print(f"❌ ERROR: {e}")
        
        # Test 4: Test current JOIN functionality
        print("\n4️⃣ Testing current JOIN functionality...")
        try:
            join_result = await ai_db.fetch_one("""
                SELECT COUNT(*) as count
                FROM ai_signal_logs p
                JOIN outcome_log o ON p.id::text = o.prediction_id::text
            """)
            print(f"Current JOIN result: {join_result[0]} rows")
        except Exception as e:
            issues_found.append(f"JOIN test failed: {e}")
            print(f"❌ ERROR: {e}")
        
        # Test 5: Check data counts
        print("\n5️⃣ Checking data counts...")
        try:
            signal_count = await ai_db.fetch_one("SELECT COUNT(*) FROM ai_signal_logs")
            outcome_count = await ai_db.fetch_one("SELECT COUNT(*) FROM outcome_log")
            paper_count = await ai_db.fetch_one("SELECT COUNT(*) FROM paper_trade_log")
            
            print(f"ai_signal_logs: {signal_count[0]} rows")
            print(f"outcome_log: {outcome_count[0]} rows")
            print(f"paper_trade_log: {paper_count[0]} rows")
        except Exception as e:
            issues_found.append(f"Data count check failed: {e}")
            print(f"❌ ERROR: {e}")
        
        # Summary
        print("\n" + "=" * 50)
        if issues_found:
            print("🚨 ISSUES FOUND - PRODUCTION FIXES NEEDED")
            print("❌ Issues:")
            for i, issue in enumerate(issues_found, 1):
                print(f"   {i}. {issue}")
            print("\n🛠️  RECOMMENDED ACTIONS:")
            print("   1. Run production-safe schema fix script")
            print("   2. Review and approve data cleanup actions")
            print("   3. Execute fixes during maintenance window")
            print("   4. Verify results with post-fix validation")
            return False
        else:
            print("🎉 NO ISSUES FOUND - SCHEMA IS HEALTHY")
            print("✅ All validations passed")
            print("✅ Ready for UUID migration when needed")
            return True
            
    except Exception as e:
        print(f"❌ CRITICAL VALIDATION ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(validate_before_production_fix())
    exit(0 if success else 1)
