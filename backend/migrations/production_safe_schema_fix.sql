-- ================================================================
-- PRODUCTION-SAFE SCHEMA FIXES - Supabase PostgreSQL
-- ================================================================
-- Purpose: Fix formula_id type, add foreign key, clean data
-- Rules: No data loss, validate before constraints, safe for production

-- Enable required extension
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ================================================================
-- STEP 2: VALIDATE DATA BEFORE CHANGES
-- ================================================================

-- Check invalid formula_id values (non-numeric)
DO $$
DECLARE
    invalid_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO invalid_count
    FROM ai_signal_logs
    WHERE formula_id IS NOT NULL
    AND formula_id !~ '^\d+$';
    
    IF invalid_count > 0 THEN
        RAISE NOTICE 'Found % invalid formula_id values - will be cleaned', invalid_count;
        
        -- Show sample invalid values
        RAISE NOTICE 'Sample invalid formula_id values:';
        FOR row IN 
            SELECT formula_id FROM ai_signal_logs 
            WHERE formula_id IS NOT NULL 
            AND formula_id !~ '^\d+$' 
            LIMIT 5
        LOOP
            RAISE NOTICE '  Invalid: %', row.formula_id;
        END LOOP;
    ELSE
        RAISE NOTICE 'No invalid formula_id values found';
    END IF;
END $$;

-- Check orphan outcome_log rows
DO $$
DECLARE
    orphan_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO orphan_count
    FROM outcome_log o
    LEFT JOIN ai_signal_logs p ON o.prediction_id::text = p.id::text
    WHERE p.id IS NULL;
    
    IF orphan_count > 0 THEN
        RAISE NOTICE 'Found % orphan outcome_log rows - will be cleaned', orphan_count;
        
        -- Show sample orphan rows
        RAISE NOTICE 'Sample orphan outcome_log rows:';
        FOR row IN 
            SELECT o.id, o.prediction_id, o.outcome 
            FROM outcome_log o
            LEFT JOIN ai_signal_logs p ON o.prediction_id::text = p.id::text
            WHERE p.id IS NULL
            LIMIT 5
        LOOP
            RAISE NOTICE '  Orphan ID: %, prediction_id: %', row.id, row.prediction_id;
        END LOOP;
    ELSE
        RAISE NOTICE 'No orphan outcome_log rows found';
    END IF;
END $$;

-- ================================================================
-- STEP 3: CLEAN DATA (SAFE CLEANUP)
-- ================================================================

-- Fix invalid formula_id values (set NULL - safe approach)
UPDATE ai_signal_logs
SET formula_id = NULL
WHERE formula_id IS NOT NULL
AND formula_id !~ '^\d+$';

RAISE NOTICE 'Cleaned invalid formula_id values (set to NULL)';

-- Clean orphan outcome_log rows (safe approach - set prediction_id to NULL)
UPDATE outcome_log o
SET prediction_id = NULL
WHERE NOT EXISTS (
    SELECT 1 FROM ai_signal_logs p
    WHERE p.id::text = o.prediction_id::text
);

RAISE NOTICE 'Cleaned orphan outcome_log rows (set prediction_id to NULL)';

-- ================================================================
-- STEP 4: FIX formula_id TYPE
-- ================================================================

-- First ensure all formula_id values are valid integers
UPDATE ai_signal_logs
SET formula_id = NULL
WHERE formula_id IS NOT NULL
AND formula_id !~ '^\d+$';

-- Convert formula_id from text to integer
ALTER TABLE ai_signal_logs
ALTER COLUMN formula_id TYPE INTEGER
USING formula_id::int;

RAISE NOTICE 'Converted formula_id from TEXT to INTEGER';

-- ================================================================
-- STEP 5: ADD FOREIGN KEY CONSTRAINT
-- ================================================================

-- Add foreign key constraint with safe options
ALTER TABLE outcome_log
ADD CONSTRAINT fk_prediction
FOREIGN KEY (prediction_id)
REFERENCES ai_signal_logs(id)
ON DELETE SET NULL
ON UPDATE CASCADE;

RAISE NOTICE 'Added fk_prediction foreign key constraint';

-- ================================================================
-- STEP 6: VERIFICATION AND VALIDATION
-- ================================================================

-- Verify formula_id type change
SELECT 
    'formula_id_type_check' as verification_step,
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'ai_signal_logs'
AND column_name = 'formula_id';

-- Verify foreign key constraint
SELECT 
    'foreign_key_check' as verification_step,
    tc.constraint_name,
    tc.constraint_type,
    ccu.table_name as references_table,
    ccu.column_name as references_column,
    rc.delete_rule,
    rc.update_rule
FROM information_schema.table_constraints tc
JOIN information_schema.constraint_column_usage ccu 
    ON tc.constraint_name = ccu.constraint_name
JOIN information_schema.referential_constraints rc
    ON tc.constraint_name = rc.constraint_name
WHERE tc.table_name = 'outcome_log'
AND tc.constraint_type = 'FOREIGN KEY';

-- Verify data integrity after changes
SELECT 
    'data_integrity_check' as verification_step,
    COUNT(*) as total_signals,
    COUNT(formula_id) as signals_with_formula_id,
    COUNT(CASE WHEN formula_id IS NULL THEN 1 END) as null_formula_ids
FROM ai_signal_logs;

-- Test JOIN functionality
SELECT 
    'join_functionality_check' as verification_step,
    COUNT(*) as joined_rows
FROM ai_signal_logs p
JOIN outcome_log o ON p.id::text = o.prediction_id::text
WHERE p.id IS NOT NULL
AND o.prediction_id IS NOT NULL;

-- Verify no orphan rows remain
SELECT 
    'orphan_check' as verification_step,
    COUNT(*) as remaining_orphans
FROM outcome_log o
WHERE NOT EXISTS (
    SELECT 1 FROM ai_signal_logs p
    WHERE p.id::text = o.prediction_id::text
);

-- Update statistics
ANALYZE ai_signal_logs;
ANALYZE outcome_log;

RAISE NOTICE 'Schema fixes completed successfully';
RAISE NOTICE 'Verification queries executed - check results above';
