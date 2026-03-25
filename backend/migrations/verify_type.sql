-- ================================================================
-- VERIFY TYPE - MUST RETURN INTEGER
-- ================================================================

SELECT data_type
FROM information_schema.columns
WHERE table_name='ai_signal_logs'
AND column_name='formula_id';
