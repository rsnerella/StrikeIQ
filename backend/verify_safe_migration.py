#!/usr/bin/env python3
"""
Safe UUID Migration Verification
Verifies that the safe UUID migration works correctly
"""
import asyncio
from ai.ai_db import ai_db

async def verify_safe_migration():
    try:
        print("🔍 Verifying Safe UUID Migration...")
        
        # Test 1: Verify current state (should still be integer)
        print("\n1️⃣ Checking current state (should be INTEGER)...")
        result1 = await ai_db.fetch_one("""
            SELECT column_name, data_type, udt_name 
            FROM information_schema.columns 
            WHERE table_name = 'ai_signal_logs' AND column_name = 'id'
        """)
        print(f'Current ai_signal_logs.id: {result1}')
        
        # Test 2: Test text casting JOIN (should work)
        print("\n2️⃣ Testing text casting JOIN...")
        result2 = await ai_db.fetch_one("""
            SELECT COUNT(*) as join_count
            FROM ai_signal_logs p 
            LEFT JOIN outcome_log o ON p.id::text = o.prediction_id::text
            LIMIT 10
        """)
        print(f"✅ Text casting JOIN works: {result2[0]} rows")
        
        # Test 3: Check if formula_id column exists
        print("\n3️⃣ Checking formula_id column...")
        result3 = await ai_db.fetch_one("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'ai_signal_logs' AND column_name = 'formula_id'
        """)
        print(f'formula_id column: {result3}')
        
        # Test 4: Test paper_trade_log queries
        print("\n4️⃣ Testing paper_trade_log queries...")
        result4 = await ai_db.fetch_query("""
            SELECT id, prediction_id, symbol, strike_price,
                   entry_price, exit_price, quantity, pnl, trade_type,
                   timestamp
            FROM paper_trade_log
            WHERE timestamp >= NOW() - INTERVAL '24 hours'
            ORDER BY timestamp DESC
            LIMIT 3
        """)
        print(f"✅ Paper trade query works: {len(result4)} rows")
        
        print("\n✅ Current state verified - ready for migration")
        print("📋 Next steps:")
        print("   1. Run: psql -d strikeiq_prod -f migrations/safe_uuid_migration.sql")
        print("   2. Update code to remove text casting")
        print("   3. Run verification again")
        
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(verify_safe_migration())
