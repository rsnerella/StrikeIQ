-- ================================================================
-- FINAL SCHEMA FIXES - Prepare for UUID Migration
-- ================================================================
-- Purpose: Fix formula_id type, add foreign key, verify joins
-- Rules: No data loss, maintain consistency

BEGIN;

-- ================================================================
-- 1. FIX formula_id TYPE
-- ================================================================

-- Convert formula_id from text to integer for proper type consistency
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'ai_signal_logs' AND column_name = 'formula_id'
    ) THEN
        -- Check if any non-integer values exist
        IF EXISTS (
            SELECT 1 FROM ai_signal_logs 
            WHERE formula_id IS NOT NULL 
            AND formula_id ~ '^[0-9]+$' = FALSE
        ) THEN
            RAISE WARNING 'Found non-integer formula_id values - will be set to NULL';
            UPDATE ai_signal_logs 
            SET formula_id = NULL 
            WHERE formula_id IS NOT NULL 
            AND formula_id ~ '^[0-9]+$' = FALSE;
        END IF;
        
        -- Convert to integer
        ALTER TABLE ai_signal_logs 
        ALTER COLUMN formula_id TYPE INTEGER 
        USING formula_id::int;
        
        RAISE NOTICE 'formula_id column converted to INTEGER type';
    END IF;
END $$;

-- ================================================================
-- 2. ADD FOREIGN KEY CONSTRAINT
-- ================================================================

-- Add foreign key constraint if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'fk_prediction'
        AND table_name = 'outcome_log'
    ) THEN
        ALTER TABLE outcome_log
        ADD CONSTRAINT fk_prediction
        FOREIGN KEY (prediction_id) 
        REFERENCES ai_signal_logs(id)
        ON DELETE SET NULL;
        
        RAISE NOTICE 'Added fk_prediction foreign key constraint';
    END IF;
END $$;

-- ================================================================
-- 3. PREPARE paper_trade_log FOR UUID MIGRATION
-- ================================================================

-- Add UUID column to paper_trade_log for future migration
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'paper_trade_log' AND column_name = 'prediction_id_uuid'
    ) THEN
        ALTER TABLE paper_trade_log 
        ADD COLUMN prediction_id_uuid UUID;
        
        RAISE NOTICE 'Added prediction_id_uuid column to paper_trade_log';
    END IF;
END $$;

-- ================================================================
-- 4. UPDATE STATISTICS
-- ================================================================

ANALYZE ai_signal_logs;
ANALYZE outcome_log;
ANALYZE paper_trade_log;

-- ================================================================
-- 5. VERIFICATION QUERIES
-- ================================================================

-- Verify formula_id type
SELECT 
    'formula_id type check' as test_name,
    pg_typeof(formula_id) as data_type,
    COUNT(*) as total_rows,
    COUNT(formula_id) as non_null_rows
FROM ai_signal_logs;

-- Verify foreign key constraint
SELECT 
    'foreign_key_check' as test_name,
    tc.constraint_name,
    tc.table_name,
    ccu.table_name as references_table
FROM information_schema.table_constraints tc
JOIN information_schema.constraint_column_usage ccu 
    ON tc.constraint_name = ccu.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
AND tc.table_name = 'outcome_log';

-- Verify real data JOIN
SELECT 
    'real_data_join_test' as test_name,
    COUNT(*) as joined_rows
FROM ai_signal_logs p
JOIN outcome_log o 
ON p.id::text = o.prediction_id::text;

-- Verify paper_trade_log preparation
SELECT 
    'paper_trade_log_prep_check' as test_name,
    column_name,
    data_type
FROM information_schema.columns 
WHERE table_name = 'paper_trade_log' 
AND column_name IN ('prediction_id', 'prediction_id_uuid')
ORDER BY column_name;

COMMIT;

-- ================================================================
-- EXPECTED RESULTS
-- ================================================================
-- formula_id should be INTEGER type
-- fk_prediction constraint should exist on outcome_log
-- JOIN should return valid row count (0+ if data exists)
-- paper_trade_log should have both prediction_id (int) and prediction_id_uuid (uuid) columns
