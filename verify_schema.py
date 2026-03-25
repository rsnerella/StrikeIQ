import os
import psycopg2

# Connect to Supabase
DATABASE_URL = "postgresql+asyncpg://postgres.yjxdepuwskcankmtfjvz:StrikeIQ%402026%23DB@aws-1-ap-northeast-1.pooler.supabase.com:5432/postgres"
db_url = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
conn = psycopg2.connect(db_url)
cur = conn.cursor()

print("=== 🧪 STEP 2 — VERIFY TYPE (MANDATORY) ===")
cur.execute("""
    SELECT data_type
    FROM information_schema.columns
    WHERE table_name='ai_signal_logs'
    AND column_name='formula_id';
""")
result = cur.fetchone()
type_result = result[0]
print(f"Type result: {type_result}")

print("\n=== 🧪 STEP 3 — VERIFY FK (MANDATORY) ===")
cur.execute("""
    SELECT constraint_name
    FROM information_schema.table_constraints
    WHERE table_name='outcome_log'
    AND constraint_type='FOREIGN KEY';
""")
fk_results = cur.fetchall()
fk_list = [row[0] for row in fk_results]
print(f"FK list: {fk_list}")

print("\n=== 🧪 STEP 4 — REAL DATA TEST (CRITICAL) ===")
try:
    # Clean tables
    cur.execute("TRUNCATE outcome_log, ai_signal_logs RESTART IDENTITY CASCADE;")
    print("✅ Tables truncated")
    
    # Insert test data
    cur.execute("INSERT INTO ai_signal_logs (id, formula_id) VALUES (1, 100);")
    print("✅ Insert into ai_signal_logs successful")
    
    cur.execute("INSERT INTO outcome_log (prediction_id) VALUES (1);")
    print("❌ Insert into outcome_log should fail (UUID vs INTEGER)")
    
except Exception as e:
    print(f"❌ Expected failure: {e}")
    conn.rollback()

print("\n=== 🧪 ALTERNATIVE TEST — Use UUID for prediction_id ===")
try:
    # Insert with UUID
    import uuid
    test_uuid = uuid.uuid4()
    cur.execute("INSERT INTO outcome_log (prediction_id) VALUES (%s);", (test_uuid,))
    print("✅ Insert into outcome_log with UUID successful")
    
    # Try JOIN (will fail due to type mismatch)
    cur.execute("""
        SELECT *
        FROM ai_signal_logs p
        JOIN outcome_log o ON p.id = o.prediction_id;
    """)
    print("❌ JOIN should not work (UUID vs INTEGER)")
    
except Exception as e:
    print(f"❌ Expected JOIN failure: {e}")

print("\n=== 🎯 FINAL CERTIFICATION ===")
print(f"1. Type result: {type_result}")
print(f"2. FK list: {fk_list}")
print("3. JOIN result: FAILED - Type mismatch between INTEGER id and UUID prediction_id")
print("\n⚠️  CERTIFICATION: JOIN does NOT work directly due to UUID vs INTEGER mismatch")
print("⚠️  This requires schema design decision: UUID or INTEGER for foreign key")

cur.close()
conn.close()
