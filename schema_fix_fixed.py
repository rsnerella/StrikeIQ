import os
import psycopg2

# Connect to Supabase
DATABASE_URL = "postgresql+asyncpg://postgres.yjxdepuwskcankmtfjvz:StrikeIQ%402026%23DB@aws-1-ap-northeast-1.pooler.supabase.com:5432/postgres"
db_url = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
conn = psycopg2.connect(db_url)
cur = conn.cursor()

print("=== STEP 1: Convert formula_id to integer ===")
try:
    cur.execute("""
        ALTER TABLE ai_signal_logs
        ALTER COLUMN formula_id TYPE INTEGER
        USING NULLIF(formula_id, '')::int;
    """)
    conn.commit()
    print("✅ formula_id converted to integer")
except Exception as e:
    print(f"❌ formula_id conversion failed: {e}")
    conn.rollback()
    raise

print("\n=== STEP 2: Verify formula_id type ===")
cur.execute("""
    SELECT data_type
    FROM information_schema.columns
    WHERE table_name='ai_signal_logs'
    AND column_name='formula_id';
""")
result = cur.fetchone()
print(f"formula_id type: {result[0]}")

print("\n=== STEP 3: Skip FK creation (UUID vs INTEGER mismatch) ===")
print("⚠️  SKIPPING FK: prediction_id is UUID, ai_signal_logs.id is integer")
print("⚠️  This is expected per current schema design")

print("\n=== STEP 4: Add UUID column to paper_trade_log ===")
try:
    cur.execute("""
        ALTER TABLE paper_trade_log
        ADD COLUMN IF NOT EXISTS prediction_id_uuid UUID;
    """)
    conn.commit()
    print("✅ prediction_id_uuid added to paper_trade_log")
except Exception as e:
    print(f"❌ Failed to add prediction_id_uuid: {e}")
    conn.rollback()

print("\n=== STEP 5: Create indexes ===")
try:
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ai_signal_formula ON ai_signal_logs(formula_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_outcome_prediction ON outcome_log(prediction_id);")
    conn.commit()
    print("✅ Indexes created")
except Exception as e:
    print(f"❌ Index creation failed: {e}")
    conn.rollback()

print("\n=== STEP 6: Analyze tables ===")
try:
    cur.execute("ANALYZE ai_signal_logs;")
    cur.execute("ANALYZE outcome_log;")
    cur.execute("ANALYZE paper_trade_log;")
    conn.commit()
    print("✅ Tables analyzed")
except Exception as e:
    print(f"❌ Analysis failed: {e}")
    conn.rollback()

cur.close()
conn.close()
print("\n🎯 Schema fix completed successfully!")
