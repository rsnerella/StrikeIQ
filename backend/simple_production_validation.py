#!/usr/bin/env python3
"""
Simple Production Validation - Handles empty databases safely
"""
import asyncio
from ai.ai_db import ai_db

async def simple_production_validation():
    print("🔍 Simple Production Schema Validation")
    print("=" * 50)
    
    try:
        # Test 1: Check if tables exist and have data
        print("\n1️⃣ Checking table existence and data...")
        try:
            signal_count = await ai_db.fetch_one("SELECT COUNT(*) FROM ai_signal_logs")
            outcome_count = await ai_db.fetch_one("SELECT COUNT(*) FROM outcome_log")
            paper_count = await ai_db.fetch_one("SELECT COUNT(*) FROM paper_trade_log")
            
            print(f"ai_signal_logs: {signal_count[0]} rows")
            print(f"outcome_log: {outcome_count[0]} rows") 
            print(f"paper_trade_log: {paper_count[0]} rows")
            
            if signal_count[0] == 0 and outcome_count[0] == 0 and paper_count[0] == 0:
                print("⚠️  Database appears to be empty - schema fixes still recommended")
        except Exception as e:
            print(f"❌ ERROR checking data: {e}")
        
        # Test 2: Check formula_id column type (if table exists)
        print("\n2️⃣ Checking formula_id column...")
        try:
            column_info = await ai_db.fetch_query("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'ai_signal_logs'
                AND column_name = 'formula_id'
            """)
            
            if column_info:
                for row in column_info:
                    print(f"✅ formula_id: {row[1]} (nullable: {row[2]})")
            else:
                print("⚠️  formula_id column not found")
        except Exception as e:
            print(f"❌ ERROR checking formula_id: {e}")
        
        # Test 3: Check foreign key constraints
        print("\n3️⃣ Checking foreign key constraints...")
        try:
            fk_info = await ai_db.fetch_query("""
                SELECT constraint_name, table_name
                FROM information_schema.table_constraints
                WHERE constraint_type = 'FOREIGN KEY'
                AND table_name IN ('ai_signal_logs', 'outcome_log', 'paper_trade_log')
            """)
            
            print(f"Foreign key constraints found: {len(fk_info)}")
            for row in fk_info:
                print(f"  - {row[0]} on {row[1]}")
                
            # Check for fk_prediction specifically
            has_fk_prediction = any(row[0] == 'fk_prediction' for row in fk_info)
            if not has_fk_prediction:
                print("⚠️  fk_prediction constraint missing")
            else:
                print("✅ fk_prediction constraint exists")
                
        except Exception as e:
            print(f"❌ ERROR checking foreign keys: {e}")
        
        # Test 4: Test basic JOIN (should work even with empty data)
        print("\n4️⃣ Testing basic JOIN...")
        try:
            join_result = await ai_db.fetch_one("""
                SELECT COUNT(*) as count
                FROM ai_signal_logs p
                LEFT JOIN outcome_log o ON p.id::text = o.prediction_id::text
            """)
            print(f"✅ JOIN test successful: {join_result[0]} rows")
        except Exception as e:
            print(f"❌ ERROR in JOIN test: {e}")
        
        print("\n" + "=" * 50)
        print("🎯 RECOMMENDATIONS:")
        print("1. Run production-safe schema fix script")
        print("2. This will:")
        print("   - Enable pgcrypto extension")
        print("   - Fix formula_id type (TEXT → INTEGER)")
        print("   - Add fk_prediction foreign key")
        print("   - Clean any orphan data")
        print("3. Safe for empty databases")
        print("4. Prepares for future UUID migration")
        
        return True
        
    except Exception as e:
        print(f"❌ CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(simple_production_validation())
    exit(0 if success else 1)
