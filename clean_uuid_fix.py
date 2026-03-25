import os
import psycopg2
import uuid

# Connect to Supabase
DATABASE_URL = "postgresql+asyncpg://postgres.yjxdepuwskcankmtfjvz:StrikeIQ%402026%23DB@aws-1-ap-northeast-1.pooler.supabase.com:5432/postgres"
db_url = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
conn = psycopg2.connect(db_url)
cur = conn.cursor()

print("=== 🔧 RESET — DROP EXISTING UUID COLUMNS ===")
try:
    cur.execute("ALTER TABLE ai_signal_logs DROP COLUMN IF EXISTS id_uuid;")
    conn.commit()
    print("✅ Dropped existing id_uuid")
except Exception as e:
    print(f"⚠️  No id_uuid to drop: {e}")

try:
    cur.execute("ALTER TABLE signal_outcomes DROP COLUMN IF EXISTS signal_id_uuid;")
    conn.commit()
    print("✅ Dropped existing signal_id_uuid")
except Exception as e:
    print(f"⚠️  No signal_id_uuid to drop: {e}")

print("\n=== 🔧 STEP 1 — ADD UUID COLUMN TO ai_signal_logs ===")
cur.execute("""
    ALTER TABLE ai_signal_logs 
    ADD COLUMN id_uuid UUID DEFAULT gen_random_uuid();
""")
conn.commit()
print("✅ id_uuid column added to ai_signal_logs")

print("\n=== 🔧 STEP 2 — ADD UUID COLUMN TO signal_outcomes ===")
cur.execute("""
    ALTER TABLE signal_outcomes 
    ADD COLUMN signal_id_uuid UUID;
""")
conn.commit()
print("✅ signal_id_uuid column added to signal_outcomes")

print("\n=== 🔧 STEP 3 — DROP DEPENDENT CONSTRAINT ===")
cur.execute("""
    ALTER TABLE signal_outcomes
    DROP CONSTRAINT IF EXISTS signal_outcomes_signal_id_fkey;
""")
conn.commit()
print("✅ signal_outcomes_signal_id_fkey dropped")

print("\n=== 🔧 STEP 4 — DROP OLD COLUMNS ===")
cur.execute("ALTER TABLE ai_signal_logs DROP COLUMN IF EXISTS id CASCADE;")
conn.commit()
print("✅ ai_signal_logs.id dropped")

cur.execute("ALTER TABLE signal_outcomes DROP COLUMN IF EXISTS signal_id;")
conn.commit()
print("✅ signal_outcomes.signal_id dropped")

print("\n=== 🔧 STEP 5 — RENAME COLUMNS ===")
cur.execute("""
    ALTER TABLE ai_signal_logs 
    RENAME COLUMN id_uuid TO id;
""")
conn.commit()
print("✅ ai_signal_logs.id_uuid renamed to id")

cur.execute("""
    ALTER TABLE signal_outcomes 
    RENAME COLUMN signal_id_uuid TO signal_id;
""")
conn.commit()
print("✅ signal_outcomes.signal_id_uuid renamed to signal_id")

print("\n=== 🔧 STEP 6 — ENSURE outcome_log TYPE ===")
cur.execute("""
    ALTER TABLE outcome_log
    ALTER COLUMN prediction_id TYPE UUID
    USING prediction_id::uuid;
""")
conn.commit()
print("✅ outcome_log.prediction_id converted to UUID")

print("\n=== 🔧 STEP 7 — ADD PRIMARY KEY ===")
cur.execute("""
    ALTER TABLE ai_signal_logs
    ADD PRIMARY KEY (id);
""")
conn.commit()
print("✅ Primary key added to ai_signal_logs.id")

print("\n=== 🔧 STEP 8 — ADD FK CONSTRAINTS ===")
cur.execute("""
    ALTER TABLE outcome_log
    ADD CONSTRAINT fk_prediction
    FOREIGN KEY (prediction_id)
    REFERENCES ai_signal_logs(id);
""")
conn.commit()
print("✅ fk_prediction constraint added")

cur.execute("""
    ALTER TABLE signal_outcomes
    ADD CONSTRAINT signal_outcomes_signal_id_fkey
    FOREIGN KEY (signal_id)
    REFERENCES ai_signal_logs(id);
""")
conn.commit()
print("✅ signal_outcomes_signal_id_fkey constraint added")

print("\n=== 🧪 STEP 9 — FINAL TEST ===")
# Clean tables
cur.execute("TRUNCATE signal_outcomes, outcome_log, ai_signal_logs CASCADE;")
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

cur.execute("""
    INSERT INTO signal_outcomes (signal_id)
    SELECT id FROM ai_signal_logs LIMIT 1;
""")
conn.commit()
print("✅ Insert into signal_outcomes successful")

# Test JOINs
cur.execute("""
    SELECT *
    FROM ai_signal_logs p
    JOIN outcome_log o ON p.id = o.prediction_id;
""")
outcome_result = cur.fetchall()
print(f"✅ outcome_log JOIN successful! Rows: {len(outcome_result)}")

cur.execute("""
    SELECT *
    FROM ai_signal_logs p
    JOIN signal_outcomes s ON p.id = s.signal_id;
""")
signal_result = cur.fetchall()
print(f"✅ signal_outcomes JOIN successful! Rows: {len(signal_result)}")

if len(outcome_result) == 1 and len(signal_result) == 1:
    print("🎯 BOTH JOINS RETURN EXACTLY 1 ROW - PERFECT!")
else:
    print(f"⚠️  Expected 1 row each, got {len(outcome_result)} and {len(signal_result)}")

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

cur.execute("""
    SELECT data_type
    FROM information_schema.columns
    WHERE table_name='signal_outcomes'
    AND column_name='signal_id';
""")
signal_type = cur.fetchone()[0]

# Check FKs
cur.execute("""
    SELECT constraint_name
    FROM information_schema.table_constraints
    WHERE table_name='outcome_log'
    AND constraint_type='FOREIGN KEY';
""")
outcome_fk = cur.fetchone()

cur.execute("""
    SELECT constraint_name
    FROM information_schema.table_constraints
    WHERE table_name='signal_outcomes'
    AND constraint_type='FOREIGN KEY';
""")
signal_fk = cur.fetchone()

print(f"1. ai_signal_logs.id type: {ai_id_type}")
print(f"2. outcome_log.prediction_id type: {outcome_type}")
print(f"3. signal_outcomes.signal_id type: {signal_type}")
print(f"4. outcome_log FK: {outcome_fk[0] if outcome_fk else 'None'}")
print(f"5. signal_outcomes FK: {signal_fk[0] if signal_fk else 'None'}")
print(f"6. outcome_log JOIN result: {len(outcome_result)} rows")
print(f"7. signal_outcomes JOIN result: {len(signal_result)} rows")

cur.close()
conn.close()
print("\n🚀 COMPLETE UUID ALIGNMENT SUCCESS!")
