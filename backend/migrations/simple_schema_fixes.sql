-- Simple schema fixes without procedural blocks
-- Run these individual statements

-- Fix 1: Add trade_status column if missing
ALTER TABLE paper_trade_log 
ADD COLUMN IF NOT EXISTS trade_status VARCHAR(20) DEFAULT 'OPEN';

-- Fix 2: Add evaluation_time column to outcome_log if missing
ALTER TABLE outcome_log 
ADD COLUMN IF NOT EXISTS evaluation_time TIMESTAMPTZ DEFAULT NOW();

-- Fix 3: Add option_type column to paper_trade_log if missing
ALTER TABLE paper_trade_log 
ADD COLUMN IF NOT EXISTS option_type VARCHAR(10);

-- Fix 4: Add exit_time column to paper_trade_log if missing
ALTER TABLE paper_trade_log 
ADD COLUMN IF NOT EXISTS exit_time TIMESTAMPTZ;

-- Fix 5: Add entry_time column if missing
ALTER TABLE paper_trade_log 
ADD COLUMN IF NOT EXISTS entry_time TIMESTAMPTZ DEFAULT NOW();

-- Verify fixes
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
