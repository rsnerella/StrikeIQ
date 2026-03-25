-- ================================================================
-- FINAL PRODUCTION SCHEMA FIX - Supabase Execution
-- ================================================================

-- 1. Enable UUID support
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 2. Fix formula_id type
ALTER TABLE ai_signal_logs
ALTER COLUMN formula_id TYPE INTEGER
USING formula_id::int;

-- 3. Add foreign key
ALTER TABLE outcome_log
ADD CONSTRAINT fk_prediction
FOREIGN KEY (prediction_id)
REFERENCES ai_signal_logs(id);

-- 4. Prepare UUID migration
ALTER TABLE paper_trade_log
ADD COLUMN IF NOT EXISTS prediction_id_uuid UUID;

-- 5. Indexes
CREATE INDEX IF NOT EXISTS idx_ai_signal_formula 
ON ai_signal_logs(formula_id);

CREATE INDEX IF NOT EXISTS idx_outcome_prediction 
ON outcome_log(prediction_id);

-- 6. Analyze
ANALYZE ai_signal_logs;
ANALYZE outcome_log;
ANALYZE paper_trade_log;

-- 7. Success message
DO $$
BEGIN
  RAISE NOTICE 'Schema fixes completed successfully';
END $$;

-- ================================================================
-- VERIFICATION QUERIES (Optional - Run separately)
-- ================================================================

-- Check formula_id type
SELECT 
    'formula_id_type' as check_name,
    column_name,
    data_type
FROM information_schema.columns
WHERE table_name = 'ai_signal_logs'
AND column_name = 'formula_id';

-- Check foreign key constraint
SELECT 
    'foreign_key_check' as check_name,
    constraint_name,
    constraint_type,
    table_name
FROM information_schema.table_constraints
WHERE table_name = 'outcome_log'
AND constraint_type = 'FOREIGN KEY';

-- Check prediction_id_uuid column
SELECT 
    'prediction_id_uuid_check' as check_name,
    column_name,
    data_type
FROM information_schema.columns
WHERE table_name = 'paper_trade_log'
AND column_name = 'prediction_id_uuid';

-- Check indexes
SELECT 
    'index_check' as check_name,
    indexname,
    tablename
FROM pg_indexes
WHERE tablename IN ('ai_signal_logs', 'outcome_log')
AND indexname LIKE 'idx_%';
