-- ================================================================
-- REAL DATA TEST - CRITICAL VERIFICATION
-- ================================================================

-- clean test
DELETE FROM outcome_log;
DELETE FROM ai_signal_logs;

-- insert test data
INSERT INTO ai_signal_logs (id, formula_id) VALUES (1, 100);
INSERT INTO outcome_log (prediction_id) VALUES (1);

-- JOIN test
SELECT *
FROM ai_signal_logs p
JOIN outcome_log o
ON p.id = o.prediction_id;
