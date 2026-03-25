-- ================================================================
-- PRODUCTION SCHEMA FIXES - StrikeIQ Database Migration
-- ================================================================
-- Purpose: Convert temporary fixes into production-grade schema
-- Rules: No data loss, backward compatibility, proper indexing
-- ================================================================

BEGIN;

-- ================================================================
-- 1. FIX UUID TYPE MISMATCH
-- ================================================================

-- Step 1: Create UUID column in ai_signal_logs (temporary)
ALTER TABLE ai_signal_logs 
ADD COLUMN id_uuid UUID DEFAULT gen_random_uuid();

-- Step 2: Backfill UUID from existing integer IDs
UPDATE ai_signal_logs 
SET id_uuid = lpad(id::text, 32, '0')::uuid;

-- Step 3: Drop foreign key constraints that reference ai_signal_logs.id
-- (We'll recreate them after the type change)
DO $$ 
DECLARE
    r RECORD;
BEGIN
    FOR r IN 
        SELECT conname, conrelid::regclass AS table_name
        FROM pg_constraint 
        WHERE confdelid = 'ai_signal_logs'::regclass
    LOOP
        EXECUTE 'ALTER TABLE ' || r.table_name || ' DROP CONSTRAINT ' || r.conname;
        RAISE NOTICE 'Dropped constraint % on %', r.conname, r.table_name;
    END LOOP;
END $$;

-- Step 4: Drop old integer id and rename UUID column
ALTER TABLE ai_signal_logs 
DROP COLUMN id;

ALTER TABLE ai_signal_logs 
RENAME COLUMN id_uuid TO id;

-- Step 5: Make id the primary key again
ALTER TABLE ai_signal_logs 
ADD PRIMARY KEY (id);

-- Step 6: Recreate foreign key constraints
ALTER TABLE outcome_log 
ADD CONSTRAINT fk_outcome_log_prediction_id 
FOREIGN KEY (prediction_id) REFERENCES ai_signal_logs(id) ON DELETE CASCADE;

-- ================================================================
-- 2. ADD DEDICATED formula_id COLUMN
-- ================================================================

-- Step 1: Add integer formula_id column (if not exists)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'ai_signal_logs' AND column_name = 'formula_id_int'
    ) THEN
        ALTER TABLE ai_signal_logs 
        ADD COLUMN formula_id_int INTEGER;
    END IF;
END $$;

-- Step 2: Backfill from JSON metadata
UPDATE ai_signal_logs 
SET formula_id_int = (metadata->>'formula_id')::int 
WHERE metadata->>'formula_id' IS NOT NULL 
AND (metadata->>'formula_id') ~ '^[0-9]+$';

-- Step 3: Drop old text formula_id and rename integer column
ALTER TABLE ai_signal_logs 
DROP COLUMN formula_id;

ALTER TABLE ai_signal_logs 
RENAME COLUMN formula_id_int TO formula_id;

-- Step 4: Add index for performance
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ai_signal_logs_formula_id 
ON ai_signal_logs(formula_id);

-- ================================================================
-- 3. FIX paper_trade_log SCHEMA
-- ================================================================

-- Step 1: Add missing columns if they don't exist
DO $$
BEGIN
    -- Add option_type if missing
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'paper_trade_log' AND column_name = 'option_type'
    ) THEN
        ALTER TABLE paper_trade_log 
        ADD COLUMN option_type VARCHAR(10);
    END IF;
    
    -- Add trade_status if missing (rename from trade_type)
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'paper_trade_log' AND column_name = 'trade_type'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'paper_trade_log' AND column_name = 'trade_status'
    ) THEN
        ALTER TABLE paper_trade_log 
        RENAME COLUMN trade_type TO trade_status;
    END IF;
    
    -- Rename timestamp to entry_time if needed
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'paper_trade_log' AND column_name = 'timestamp'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'paper_trade_log' AND column_name = 'entry_time'
    ) THEN
        ALTER TABLE paper_trade_log 
        RENAME COLUMN timestamp TO entry_time;
    END IF;
END $$;

-- Step 2: Update index to use new column name
DROP INDEX IF EXISTS idx_paper_trade_symbol_time;
CREATE INDEX CONCURRENTLY idx_paper_trade_symbol_time 
ON paper_trade_log(symbol, entry_time DESC);

-- ================================================================
-- 4. PERFORMANCE OPTIMIZATIONS
-- ================================================================

-- Add composite indexes for common query patterns
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ai_signal_logs_formula_time 
ON ai_signal_logs(formula_id, timestamp DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_outcome_log_prediction_time 
ON outcome_log(prediction_id, evaluation_time DESC);

-- Add partial index for active formulas only
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ai_signal_logs_active_formula 
ON ai_signal_logs(formula_id, timestamp DESC) 
WHERE metadata->>'formula_id' IS NOT NULL;

-- ================================================================
-- 5. CLEANUP AND VALIDATION
-- ================================================================

-- Update table statistics for query planner
ANALYZE ai_signal_logs;
ANALYZE outcome_log;
ANALYZE paper_trade_log;

-- Add comments for documentation
COMMENT ON COLUMN ai_signal_logs.id IS 'UUID primary key replacing integer ID';
COMMENT ON COLUMN ai_signal_logs.formula_id IS 'Dedicated integer formula_id for performance';
COMMENT ON COLUMN paper_trade_log.option_type IS 'Option type (CE/PE) - optional field';
COMMENT ON COLUMN paper_trade_log.trade_status IS 'Trade status (OPEN/CLOSED/PENDING)';
COMMENT ON COLUMN paper_trade_log.entry_time IS 'Entry timestamp for trade execution';

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

-- Verify formula_id column exists and is populated
SELECT 
    COUNT(*) as total_rows,
    COUNT(formula_id) as rows_with_formula_id,
    COUNT(CASE WHEN metadata->>'formula_id' IS NOT NULL THEN 1 END) as rows_with_json_formula_id
FROM ai_signal_logs;

-- Verify paper_trade_log structure
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'paper_trade_log' 
AND column_name IN ('option_type', 'trade_status', 'entry_time')
ORDER BY column_name;
