-- ================================================================
-- STRICT SUPABASE SCHEMA FIX - EXECUTE EXACTLY AS WRITTEN
-- ================================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

ALTER TABLE ai_signal_logs
ALTER COLUMN formula_id TYPE INTEGER
USING NULLIF(formula_id, '')::int;

ALTER TABLE outcome_log
ADD CONSTRAINT fk_prediction
FOREIGN KEY (prediction_id)
REFERENCES ai_signal_logs(id);

ALTER TABLE paper_trade_log
ADD COLUMN IF NOT EXISTS prediction_id_uuid UUID;

CREATE INDEX IF NOT EXISTS idx_ai_signal_formula 
ON ai_signal_logs(formula_id);

CREATE INDEX IF NOT EXISTS idx_outcome_prediction 
ON outcome_log(prediction_id);

ANALYZE ai_signal_logs;
ANALYZE outcome_log;
ANALYZE paper_trade_log;
