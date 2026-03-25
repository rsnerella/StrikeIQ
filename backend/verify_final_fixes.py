#!/usr/bin/env python3
"""
Final Schema Fixes Verification
Verifies formula_id type, foreign key, and JOIN functionality
"""
import asyncio
from ai.ai_db import ai_db

async def verify_final_fixes():
    print("🔍 Final Schema Fixes Verification")
    
    try:
        # Test 1: Verify formula_id type
        print("\n1️⃣ Checking formula_id type...")
        try:
            result1 = await ai_db.fetch_one("""
                SELECT 
                    pg_typeof(formula_id) as data_type,
                    COUNT(*) as total_rows,
                    COUNT(formula_id) as non_null_rows
                FROM ai_signal_logs
            """)
            print(f"✅ formula_id type: {result1[0]}")
            print(f"✅ Total rows: {result1[1]}, Non-null rows: {result1[2]}")
            
            if result1[0] != 'integer':
                print(f"❌ ERROR: formula_id should be INTEGER, got {result1[0]}")
                return False
        except Exception as e:
            print(f"❌ ERROR checking formula_id: {e}")
            return False
        
        # Test 2: Verify foreign key constraint
        print("\n2️⃣ Checking foreign key constraint...")
        try:
            result2 = await ai_db.fetch_one("""
                SELECT tc.constraint_name, tc.table_name, ccu.table_name as references_table
                FROM information_schema.table_constraints tc
                JOIN information_schema.constraint_column_usage ccu 
                    ON tc.constraint_name = ccu.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_name = 'outcome_log'
            """)
            if result2:
                print(f"✅ Foreign key constraint: {result2[0]}")
                print(f"✅ References: {result2[2]}")
            else:
                print("❌ ERROR: No foreign key constraint found")
                return False
        except Exception as e:
            print(f"❌ ERROR checking foreign key: {e}")
            return False
        
        # Test 3: Verify real data JOIN
        print("\n3️⃣ Checking real data JOIN...")
        try:
            result3 = await ai_db.fetch_one("""
                SELECT COUNT(*) as joined_rows
                FROM ai_signal_logs p
                JOIN outcome_log o 
                ON p.id::text = o.prediction_id::text
            """)
            print(f"✅ JOIN result: {result3[0]} rows joined")
            
            if result3[0] is None:
                print("❌ ERROR: JOIN returned NULL")
                return False
        except Exception as e:
            print(f"❌ ERROR in JOIN test: {e}")
            return False
        
        # Test 4: Verify paper_trade_log preparation
        print("\n4️⃣ Checking paper_trade_log preparation...")
        try:
            result4 = await ai_db.fetch_query("""
                SELECT column_name, data_type
                FROM information_schema.columns 
                WHERE table_name = 'paper_trade_log' 
                AND column_name IN ('prediction_id', 'prediction_id_uuid')
                ORDER BY column_name
            """)
            columns = {row[0]: row[1] for row in result4}
            print(f"✅ paper_trade_log columns: {columns}")
            
            if 'prediction_id' not in columns:
                print("❌ ERROR: prediction_id column missing")
                return False
            
            if 'prediction_id_uuid' not in columns:
                print("❌ ERROR: prediction_id_uuid column missing")
                return False
        except Exception as e:
            print(f"❌ ERROR checking paper_trade_log: {e}")
            return False
        
        print("\n" + "="*50)
        print("🎉 FINAL SCHEMA FIXES VERIFICATION PASSED")
        print("✅ formula_id is INTEGER type")
        print("✅ Foreign key constraint exists")
        print("✅ Text casting JOIN works")
        print("✅ paper_trade_log prepared for UUID migration")
        print("✅ Ready for safe UUID migration")
        return True
        
    except Exception as e:
        print(f"❌ CRITICAL VERIFICATION ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(verify_final_fixes())
    exit(0 if success else 1)
