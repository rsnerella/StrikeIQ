-- Schema fixes for missing columns in StrikeIQ database
-- Run this to fix missing columns causing errors

-- Fix 1: Add trade_status column if missing (rename from trade_type if needed)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'paper_trade_log' AND column_name = 'trade_type'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'paper_trade_log' AND column_name = 'trade_status'
    ) THEN
        ALTER TABLE paper_trade_log 
        RENAME COLUMN trade_type TO trade_status;
    ELSIF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'paper_trade_log' AND column_name = 'trade_status'
    ) THEN
        ALTER TABLE paper_trade_log 
        ADD COLUMN trade_status VARCHAR(20) DEFAULT 'OPEN';
    END IF;
END $$;

-- Fix 2: Add evaluation_time column to outcome_log if missing
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'outcome_log' AND column_name = 'evaluation_time'
    ) THEN
        ALTER TABLE outcome_log 
        ADD COLUMN evaluation_time TIMESTAMPTZ DEFAULT NOW();
    END IF;
END $$;

-- Fix 3: Add option_type column to paper_trade_log if missing
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'paper_trade_log' AND column_name = 'option_type'
    ) THEN
        ALTER TABLE paper_trade_log 
        ADD COLUMN option_type VARCHAR(10);
    END IF;
END $$;

-- Fix 4: Add exit_time column to paper_trade_log if missing
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'paper_trade_log' AND column_name = 'exit_time'
    ) THEN
        ALTER TABLE paper_trade_log 
        ADD COLUMN exit_time TIMESTAMPTZ;
    END IF;
END $$;

-- Fix 5: Add entry_time column if timestamp exists but entry_time doesn't
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'paper_trade_log' AND column_name = 'timestamp'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'paper_trade_log' AND column_name = 'entry_time'
    ) THEN
        ALTER TABLE paper_trade_log 
        RENAME COLUMN timestamp TO entry_time;
    ELSIF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'paper_trade_log' AND column_name = 'entry_time'
    ) THEN
        ALTER TABLE paper_trade_log 
        ADD COLUMN entry_time TIMESTAMPTZ DEFAULT NOW();
    END IF;
END $$;

-- Verify the fixes
SELECT 
    'paper_trade_log' as table_name,
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns 
WHERE table_name = 'paper_trade_log' 
AND column_name IN ('trade_status', 'option_type', 'entry_time', 'exit_time')
UNION ALL
SELECT 
    'outcome_log' as table_name,
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns 
WHERE table_name = 'outcome_log' 
AND column_name = 'evaluation_time'
ORDER BY table_name, column_name;
