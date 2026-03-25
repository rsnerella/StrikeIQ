-- ================================================================
-- REAL DATA TEST - STRICT VERIFICATION
-- ================================================================

DELETE FROM outcome_log;
DELETE FROM ai_signal_logs;

INSERT INTO ai_signal_logs (id, formula_id)
VALUES (1, 100);

INSERT INTO outcome_log (prediction_id)
VALUES (1);

SELECT *
FROM ai_signal_logs p
JOIN outcome_log o
ON p.id = o.prediction_id;
