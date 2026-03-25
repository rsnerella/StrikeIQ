-- Simple schema fixes for current state

-- Fix formula_id type
ALTER TABLE ai_signal_logs 
ALTER COLUMN formula_id TYPE INTEGER 
USING formula_id::int;

-- Add foreign key constraint
ALTER TABLE outcome_log
ADD CONSTRAINT fk_prediction
FOREIGN KEY (prediction_id) 
REFERENCES ai_signal_logs(id) ON DELETE CASCADE;

-- Update statistics
ANALYZE ai_signal_logs;
ANALYZE outcome_log;

-- Verification queries
SELECT 'formula_id type fixed' as result, pg_typeof(formula_id) as data_type
FROM ai_signal_logs;

SELECT 'foreign key added' as result, tc.constraint_name 
FROM information_schema.table_constraints tc
WHERE tc.constraint_name = 'fk_prediction';
