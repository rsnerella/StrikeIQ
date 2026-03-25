-- ================================================================
-- FINAL PRODUCTION SCHEMA FIXES - Empty Database
-- ================================================================
-- Safe for empty Supabase database (0 rows)
-- Applies all necessary schema fixes for production readiness

-- 1. Enable UUID support
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 2. Fix formula_id type (TEXT → INTEGER)
ALTER TABLE ai_signal_logs
ALTER COLUMN formula_id TYPE INTEGER
USING formula_id::int;

-- 3. Add foreign key constraint
ALTER TABLE outcome_log
ADD CONSTRAINT fk_prediction
FOREIGN KEY (prediction_id)
REFERENCES ai_signal_logs(id);

-- 4. Prepare for future UUID migration
ALTER TABLE paper_trade_log
ADD COLUMN IF NOT EXISTS prediction_id_uuid UUID;

-- 5. Optimize basic indexing
CREATE INDEX IF NOT EXISTS idx_ai_signal_formula 
ON ai_signal_logs(formula_id);

CREATE INDEX IF NOT EXISTS idx_outcome_prediction 
ON outcome_log(prediction_id);

-- 6. Analyze for query planner
ANALYZE ai_signal_logs;
ANALYZE outcome_log;
ANALYZE paper_trade_log;

-- ================================================================
-- VERIFICATION QUERIES
-- ================================================================

-- Check formula_id type
SELECT 
    'formula_id_type_check' as verification_step,
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'ai_signal_logs'
AND column_name = 'formula_id';

-- Check foreign key constraint
SELECT 
    'foreign_key_check' as verification_step,
    constraint_name,
    constraint_type,
    table_name
FROM information_schema.table_constraints
WHERE table_name = 'outcome_log'
AND constraint_type = 'FOREIGN KEY';

-- Check prediction_id_uuid column exists
SELECT 
    'prediction_id_uuid_check' as verification_step,
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'paper_trade_log'
AND column_name = 'prediction_id_uuid';

-- Check indexes created
SELECT 
    'index_check' as verification_step,
    indexname,
    tablename
FROM pg_indexes
WHERE tablename IN ('ai_signal_logs', 'outcome_log')
AND indexname LIKE 'idx_%';

-- Test JOIN functionality
SELECT 
    'join_functionality_check' as verification_step,
    COUNT(*) as joined_rows
FROM ai_signal_logs p
LEFT JOIN outcome_log o ON p.id::text = o.prediction_id::text;

NOTICE: 'Final production schema fixes completed successfully';
