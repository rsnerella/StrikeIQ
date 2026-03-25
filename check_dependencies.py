import os
import psycopg2

# Connect to Supabase
DATABASE_URL = "postgresql+asyncpg://postgres.yjxdepuwskcankmtfjvz:StrikeIQ%402026%23DB@aws-1-ap-northeast-1.pooler.supabase.com:5432/postgres"
db_url = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
conn = psycopg2.connect(db_url)
cur = conn.cursor()

print("=== 🔍 CHECK DEPENDENCIES ===")
cur.execute("""
    SELECT tc.table_name, tc.constraint_name, tc.constraint_type,
           kcu.column_name, ccu.table_name AS foreign_table_name,
           ccu.column_name AS foreign_column_name
    FROM information_schema.table_constraints AS tc
    JOIN information_schema.key_column_usage AS kcu
        ON tc.constraint_name = kcu.constraint_name
        AND tc.table_schema = kcu.table_schema
    JOIN information_schema.constraint_column_usage AS ccu
        ON ccu.constraint_name = tc.constraint_name
        AND ccu.table_schema = tc.table_schema
    WHERE tc.constraint_type = 'FOREIGN KEY'
    AND ccu.table_name = 'ai_signal_logs'
    ORDER BY tc.table_name;
""")
dependencies = cur.fetchall()
for dep in dependencies:
    print(f"Table: {dep[0]}, Constraint: {dep[1]}, Column: {dep[3]} → ai_signal_logs.{dep[5]}")

print("\n=== 🔍 CHECK ALL TABLE SCHEMAS ===")
cur.execute("""
    SELECT table_name, column_name, data_type
    FROM information_schema.columns
    WHERE table_name IN (
        SELECT table_name FROM information_schema.tables 
        WHERE table_schema = 'public'
    )
    AND column_name LIKE '%id%'
    ORDER BY table_name, ordinal_position;
""")
all_id_columns = cur.fetchall()
for table, col, dtype in all_id_columns:
    print(f"{table}.{col}: {dtype}")

cur.close()
conn.close()
