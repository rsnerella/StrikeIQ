-- ================================================================
-- VERIFY SCHEMA - MANDATORY VERIFICATION
-- ================================================================

-- Check formula_id type
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name='ai_signal_logs'
AND column_name='formula_id';

-- Check foreign key constraint
SELECT constraint_name
FROM information_schema.table_constraints
WHERE table_name='outcome_log';

-- Check indexes
SELECT indexname
FROM pg_indexes
WHERE tablename IN ('ai_signal_logs','outcome_log');
