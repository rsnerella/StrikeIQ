import os
import psycopg2

# Connect to Supabase
DATABASE_URL = "postgresql+asyncpg://postgres.yjxdepuwskcankmtfjvz:StrikeIQ%402026%23DB@aws-1-ap-northeast-1.pooler.supabase.com:5432/postgres"
db_url = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
conn = psycopg2.connect(db_url)
cur = conn.cursor()

# Check current schema
print("=== ai_signal_logs schema ===")
cur.execute("""
    SELECT column_name, data_type, is_nullable
    FROM information_schema.columns
    WHERE table_name = 'ai_signal_logs'
    ORDER BY ordinal_position
""")
for row in cur.fetchall():
    print(f"{row[0]}: {row[1]} ({row[2]})")

print("\n=== outcome_log schema ===")
cur.execute("""
    SELECT column_name, data_type, is_nullable
    FROM information_schema.columns
    WHERE table_name = 'outcome_log'
    ORDER BY ordinal_position
""")
for row in cur.fetchall():
    print(f"{row[0]}: {row[1]} ({row[2]})")

print("\n=== Existing constraints ===")
cur.execute("""
    SELECT constraint_name, constraint_type
    FROM information_schema.table_constraints
    WHERE table_name IN ('ai_signal_logs', 'outcome_log')
    ORDER BY table_name, constraint_name
""")
for row in cur.fetchall():
    print(f"{row[0]}: {row[1]}")

cur.close()
conn.close()
