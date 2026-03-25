-- ================================================================
-- SAFE EMPTY DATABASE SCHEMA FIXES
-- ================================================================
-- Safe for databases with 0 rows
-- Fixes formula_id type and adds missing foreign key

-- Enable required extension
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ================================================================
-- FIX formula_id TYPE (safe for empty tables)
-- ================================================================

-- Convert formula_id from text to integer (safe with empty data)
ALTER TABLE ai_signal_logs
ALTER COLUMN formula_id TYPE INTEGER
USING formula_id::int;

-- ================================================================
-- ADD MISSING FOREIGN KEY CONSTRAINT
-- ================================================================

-- Add fk_prediction constraint to outcome_log
ALTER TABLE outcome_log
ADD CONSTRAINT fk_prediction
FOREIGN KEY (prediction_id)
REFERENCES ai_signal_logs(id)
ON DELETE SET NULL
ON UPDATE CASCADE;

-- ================================================================
-- VERIFICATION
-- ================================================================

-- Verify formula_id type change
SELECT 
    'formula_id_type_check' as verification_step,
    column_name,
    data_type
FROM information_schema.columns
WHERE table_name = 'ai_signal_logs'
AND column_name = 'formula_id';

-- Verify foreign key constraint
SELECT 
    'foreign_key_check' as verification_step,
    tc.constraint_name,
    tc.constraint_type,
    ccu.table_name as references_table
FROM information_schema.table_constraints tc
JOIN information_schema.constraint_column_usage ccu 
    ON tc.constraint_name = ccu.constraint_name
WHERE tc.table_name = 'outcome_log'
AND tc.constraint_type = 'FOREIGN KEY';

-- Test JOIN functionality
SELECT 
    'join_functionality_check' as verification_step,
    COUNT(*) as joined_rows
FROM ai_signal_logs p
LEFT JOIN outcome_log o ON p.id::text = o.prediction_id::text;

-- Update statistics
ANALYZE ai_signal_logs;
ANALYZE outcome_log;

NOTICE: 'Schema fixes completed successfully for empty database';
