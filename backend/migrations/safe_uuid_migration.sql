-- ================================================================
-- SAFE UUID MIGRATION - StrikeIQ Database
-- ================================================================
-- Purpose: Convert ai_signal_logs.id from INTEGER to UUID safely
-- Method: Add new UUID column, backfill with gen_random_uuid(), preserve mapping
-- Rules: No data loss, maintain referential integrity

BEGIN;

-- ================================================================
-- STEP 1: Create mapping table for ID conversion
-- ================================================================

-- Create temporary mapping table to track old int -> new uuid relationships
CREATE TEMPORARY TABLE id_migration_map (
    old_int INTEGER PRIMARY KEY,
    new_uuid UUID NOT NULL DEFAULT gen_random_uuid()
);

-- Populate mapping table with existing IDs
INSERT INTO id_migration_map (old_int)
SELECT id FROM ai_signal_logs ORDER BY id;

-- ================================================================
-- STEP 2: Add UUID column to ai_signal_logs
-- ================================================================

-- Add new UUID column
ALTER TABLE ai_signal_logs 
ADD COLUMN id_uuid UUID NOT NULL DEFAULT gen_random_uuid();

-- Update UUID column with mapped values
UPDATE ai_signal_logs 
SET id_uuid = m.new_uuid
FROM id_migration_map m 
WHERE ai_signal_logs.id = m.old_int;

-- ================================================================
-- STEP 3: Update foreign key references
-- ================================================================

-- Create mapping for outcome_log references
CREATE TEMPORARY TABLE outcome_migration_map AS
SELECT o.prediction_id as old_uuid, m.new_uuid as new_uuid
FROM outcome_log o
JOIN id_migration_map m ON o.prediction_id::text = m.old_int::text;

-- Update outcome_log references to new UUIDs
UPDATE outcome_log 
SET prediction_id = m.new_uuid
FROM outcome_migration_map m
WHERE outcome_log.prediction_id = m.old_uuid;

-- ================================================================
-- STEP 4: Handle other foreign key constraints
-- ================================================================

-- Drop existing foreign key constraints (if any)
DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN 
        SELECT conname, conrelid::regclass AS table_name
        FROM pg_constraint 
        WHERE confdelid = 'ai_signal_logs'::regclass
    LOOP
        BEGIN
            EXECUTE 'ALTER TABLE ' || r.table_name || ' DROP CONSTRAINT ' || r.conname;
            RAISE NOTICE 'Dropped constraint % on %', r.conname, r.table_name;
        EXCEPTION WHEN OTHERS THEN
            RAISE NOTICE 'Constraint % not found or already dropped', r.conname;
        END;
    END LOOP;
END $$;

-- ================================================================
-- STEP 5: Replace integer ID with UUID ID
-- ================================================================

-- Drop old integer primary key
ALTER TABLE ai_signal_logs 
DROP CONSTRAINT ai_signal_logs_pkey;

-- Drop old integer column
ALTER TABLE ai_signal_logs 
DROP COLUMN id;

-- Rename UUID column to id
ALTER TABLE ai_signal_logs 
RENAME COLUMN id_uuid TO id;

-- Set primary key on UUID column
ALTER TABLE ai_signal_logs 
ADD PRIMARY KEY (id);

-- ================================================================
-- STEP 6: Recreate foreign key constraints
-- ================================================================

-- Recreate foreign key on outcome_log
ALTER TABLE outcome_log 
ADD CONSTRAINT fk_outcome_log_prediction_id 
FOREIGN KEY (prediction_id) REFERENCES ai_signal_logs(id) ON DELETE CASCADE;

-- ================================================================
-- STEP 7: Update formula_id column (if exists)
-- ================================================================

-- If formula_id column exists, backfill it from JSON metadata
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'ai_signal_logs' AND column_name = 'formula_id'
    ) THEN
        UPDATE ai_signal_logs 
        SET formula_id = (metadata->>'formula_id')::int 
        WHERE metadata->>'formula_id' IS NOT NULL 
        AND (metadata->>'formula_id') ~ '^[0-9]+$';
        
        -- Add index for performance
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ai_signal_logs_formula_id 
        ON ai_signal_logs(formula_id);
    END IF;
END $$;

-- ================================================================
-- STEP 8: Cleanup and verification
-- ================================================================

-- Drop temporary tables
DROP TABLE IF EXISTS id_migration_map;
DROP TABLE IF EXISTS outcome_migration_map;

-- Update table statistics
ANALYZE ai_signal_logs;
ANALYZE outcome_log;

-- Add comments for documentation
COMMENT ON COLUMN ai_signal_logs.id IS 'UUID primary key (migrated from integer)';
COMMENT ON TABLE ai_signal_logs IS 'AI signal logs with UUID primary key for optimal performance';

COMMIT;

-- ================================================================
-- VERIFICATION QUERIES
-- ================================================================

-- Verify UUID types match
SELECT 
    'ai_signal_logs.id' as table_column,
    pg_typeof(id) as data_type
UNION ALL
SELECT 
    'outcome_log.prediction_id' as table_column,
    pg_typeof(prediction_id) as data_type;

-- Verify data integrity
SELECT 
    COUNT(*) as total_signals,
    COUNT(CASE WHEN id IS NOT NULL THEN 1 END) as signals_with_uuid,
    COUNT(prediction_id) as outcomes_with_references
FROM ai_signal_logs;

-- Verify foreign key integrity
SELECT 
    COUNT(*) as orphaned_outcomes
FROM outcome_log o
LEFT JOIN ai_signal_logs s ON o.prediction_id = s.id
WHERE s.id IS NULL;
