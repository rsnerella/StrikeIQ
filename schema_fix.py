import os
import psycopg2
from psycopg2 import sql

# Connect to Supabase
DATABASE_URL = "postgresql+asyncpg://postgres.yjxdepuwskcankmtfjvz:StrikeIQ%402026%23DB@aws-1-ap-northeast-1.pooler.supabase.com:5432/postgres"
# Convert to psycopg2 format
db_url = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
conn = psycopg2.connect(db_url)
cur = conn.cursor()

# Schema fix SQL
schema_fix = """
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

ALTER TABLE ai_signal_logs
ALTER COLUMN formula_id TYPE INTEGER
USING NULLIF(formula_id, '')::int;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_prediction'
    ) THEN
        ALTER TABLE outcome_log
        ADD CONSTRAINT fk_prediction
        FOREIGN KEY (prediction_id)
        REFERENCES ai_signal_logs(id);
    END IF;
END $$;

ALTER TABLE paper_trade_log
ADD COLUMN IF NOT EXISTS prediction_id_uuid UUID;

CREATE INDEX IF NOT EXISTS idx_ai_signal_formula 
ON ai_signal_logs(formula_id);

CREATE INDEX IF NOT EXISTS idx_outcome_prediction 
ON outcome_log(prediction_id);

ANALYZE ai_signal_logs;
ANALYZE outcome_log;
ANALYZE paper_trade_log;
"""

try:
    cur.execute(schema_fix)
    conn.commit()
    print('✅ Schema fix executed successfully')
except Exception as e:
    print(f'❌ Schema fix failed: {e}')
    conn.rollback()
    raise

cur.close()
conn.close()
