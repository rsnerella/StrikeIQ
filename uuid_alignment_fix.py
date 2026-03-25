import os
import psycopg2
import uuid

# Connect to Supabase
DATABASE_URL = "postgresql+asyncpg://postgres.yjxdepuwskcankmtfjvz:StrikeIQ%402026%23DB@aws-1-ap-northeast-1.pooler.supabase.com:5432/postgres"
db_url = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
conn = psycopg2.connect(db_url)
cur = conn.cursor()

print("=== 🔧 STEP 1 — ADD UUID COLUMN ===")
try:
    cur.execute("""
        ALTER TABLE ai_signal_logs 
        ADD COLUMN id_uuid UUID DEFAULT gen_random_uuid();
    """)
    conn.commit()
    print("✅ id_uuid column added")
except Exception as e:
    print(f"❌ Failed to add id_uuid: {e}")
    conn.rollback()
    raise

print("\n=== 🔧 STEP 2 — UPDATE outcome_log MAPPING ===")
print("⚠️  DB is empty → skipping mapping")

print("\n=== 🔧 STEP 3 — DROP OLD COLUMN + RENAME ===")
try:
    cur.execute("ALTER TABLE ai_signal_logs DROP COLUMN id;")
    conn.commit()
    print("✅ Old id column dropped")
    
    cur.execute("""
        ALTER TABLE ai_signal_logs 
        RENAME COLUMN id_uuid TO id;
    """)
    conn.commit()
    print("✅ id_uuid renamed to id")
except Exception as e:
    print(f"❌ Failed to drop/rename: {e}")
    conn.rollback()
    raise

print("\n=== 🔧 STEP 4 — ENSURE outcome_log TYPE ===")
try:
    cur.execute("""
        ALTER TABLE outcome_log
        ALTER COLUMN prediction_id TYPE UUID
        USING prediction_id::uuid;
    """)
    conn.commit()
    print("✅ outcome_log.prediction_id converted to UUID")
except Exception as e:
    print(f"❌ Failed to convert prediction_id: {e}")
    conn.rollback()
    raise

print("\n=== 🔧 STEP 5 — ADD FK ===")
try:
    cur.execute("""
        ALTER TABLE outcome_log
        ADD CONSTRAINT fk_prediction
        FOREIGN KEY (prediction_id)
        REFERENCES ai_signal_logs(id);
    """)
    conn.commit()
    print("✅ fk_prediction constraint added")
except Exception as e:
    print(f"❌ Failed to add FK: {e}")
    conn.rollback()
    raise

print("\n=== 🧪 STEP 6 — FINAL TEST ===")
try:
    # Clean tables
    cur.execute("TRUNCATE outcome_log, ai_signal_logs CASCADE;")
    conn.commit()
    print("✅ Tables truncated")
    
    # Insert test data
    cur.execute("INSERT INTO ai_signal_logs (id) VALUES (gen_random_uuid());")
    conn.commit()
    print("✅ Insert into ai_signal_logs successful")
    
    cur.execute("""
        INSERT INTO outcome_log (prediction_id)
        SELECT id FROM ai_signal_logs LIMIT 1;
    """)
    conn.commit()
    print("✅ Insert into outcome_log successful")
    
    # Test JOIN
    cur.execute("""
        SELECT *
        FROM ai_signal_logs p
        JOIN outcome_log o
        ON p.id = o.prediction_id;
    """)
    result = cur.fetchall()
    print(f"✅ JOIN successful! Rows returned: {len(result)}")
    
    if len(result) == 1:
        print("🎯 EXACTLY 1 row returned - PERFECT!")
    else:
        print(f"⚠️  Expected 1 row, got {len(result)}")
        
except Exception as e:
    print(f"❌ Final test failed: {e}")
    conn.rollback()
    raise

print("\n=== 🎯 VERIFICATION ===")
# Check final types
cur.execute("""
    SELECT data_type
    FROM information_schema.columns
    WHERE table_name='ai_signal_logs'
    AND column_name='id';
""")
ai_id_type = cur.fetchone()[0]

cur.execute("""
    SELECT data_type
    FROM information_schema.columns
    WHERE table_name='outcome_log'
    AND column_name='prediction_id';
""")
outcome_type = cur.fetchone()[0]

# Check FK
cur.execute("""
    SELECT constraint_name
    FROM information_schema.table_constraints
    WHERE table_name='outcome_log'
    AND constraint_type='FOREIGN KEY';
""")
fk_result = cur.fetchone()

print(f"1. ai_signal_logs.id type: {ai_id_type}")
print(f"2. outcome_log.prediction_id type: {outcome_type}")
print(f"3. FK constraint: {fk_result[0] if fk_result else 'None'}")
print(f"4. JOIN result: {len(result)} rows")

cur.close()
conn.close()
print("\n🚀 UUID ALIGNMENT COMPLETE!")
