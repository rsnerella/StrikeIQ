-- Migration 001: Update AI Schema to Match Backend Code
-- This migration adds missing columns and tables to align Supabase with backend models

-- Add missing columns to ai_predictions table
ALTER TABLE ai_predictions 
ADD COLUMN IF NOT EXISTS probability FLOAT,
ADD COLUMN IF NOT EXISTS signal VARCHAR,
ADD COLUMN IF NOT EXISTS target FLOAT,
ADD COLUMN IF NOT EXISTS stop FLOAT;

-- Add indexes for ai_predictions
CREATE INDEX IF NOT EXISTS idx_ai_predictions_timestamp ON ai_predictions(timestamp);
CREATE INDEX IF NOT EXISTS idx_ai_predictions_symbol ON ai_predictions(symbol);

-- Add missing columns to formula_master table
ALTER TABLE formula_master 
ADD COLUMN IF NOT EXISTS conditions TEXT,
ADD COLUMN IF NOT EXISTS confidence_threshold FLOAT,
ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;

-- Add indexes for formula_master
CREATE INDEX IF NOT EXISTS idx_formula_master_name ON formula_master(formula_name);
CREATE INDEX IF NOT EXISTS idx_formula_master_active ON formula_master(is_active) WHERE is_active = TRUE;

-- Add missing columns to prediction_log table
ALTER TABLE prediction_log 
ADD COLUMN IF NOT EXISTS formula_id INTEGER,
ADD COLUMN IF NOT EXISTS signal VARCHAR,
ADD COLUMN IF NOT EXISTS nifty_spot FLOAT,
ADD COLUMN IF NOT EXISTS prediction_time TIMESTAMP,
ADD COLUMN IF NOT EXISTS outcome VARCHAR,
ADD COLUMN IF NOT EXISTS outcome_time TIMESTAMP,
ADD COLUMN IF NOT EXISTS outcome_checked BOOLEAN DEFAULT FALSE;

-- Add indexes for prediction_log
CREATE INDEX IF NOT EXISTS idx_prediction_log_timestamp ON prediction_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_prediction_log_symbol ON prediction_log(symbol);
CREATE INDEX IF NOT EXISTS idx_prediction_log_outcome_checked ON prediction_log(outcome_checked) WHERE outcome_checked = FALSE;

-- Add missing column to signal_outcomes table
ALTER TABLE signal_outcomes 
ADD COLUMN IF NOT EXISTS result VARCHAR;

-- Add foreign key constraint to signal_outcomes
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'signal_outcomes_signal_id_fkey') THEN
        ALTER TABLE signal_outcomes 
        ADD CONSTRAINT signal_outcomes_signal_id_fkey 
        FOREIGN KEY (signal_id) REFERENCES ai_signal_logs(id);
    END IF;
END
$$;

-- Add indexes for signal_outcomes
CREATE INDEX IF NOT EXISTS idx_signal_outcomes_timestamp ON signal_outcomes(timestamp);
CREATE INDEX IF NOT EXISTS idx_signal_outcomes_signal_id ON signal_outcomes(signal_id);

-- Add missing column to paper_trade_log table
ALTER TABLE paper_trade_log 
ADD COLUMN IF NOT EXISTS prediction_id INTEGER;

-- Add foreign key constraint to paper_trade_log
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'paper_trade_log_prediction_id_fkey') THEN
        ALTER TABLE paper_trade_log 
        ADD CONSTRAINT paper_trade_log_prediction_id_fkey 
        FOREIGN KEY (prediction_id) REFERENCES prediction_log(id);
    END IF;
END
$$;

-- Add indexes for paper_trade_log
CREATE INDEX IF NOT EXISTS idx_paper_trade_log_timestamp ON paper_trade_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_paper_trade_log_symbol ON paper_trade_log(symbol);

-- Create legacy market_snapshot table (matches ai/models.py)
CREATE TABLE IF NOT EXISTS market_snapshot (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    spot_price FLOAT NOT NULL,
    pcr FLOAT NOT NULL,
    total_call_oi FLOAT NOT NULL,
    total_put_oi FLOAT NOT NULL,
    atm_strike FLOAT NOT NULL,
    timestamp TIMESTAMP DEFAULT NOW()
);

-- Add index for market_snapshot
CREATE INDEX IF NOT EXISTS idx_market_snapshot_symbol_timestamp ON market_snapshot(symbol, timestamp);

-- Add missing indexes for ai_features
CREATE INDEX IF NOT EXISTS idx_ai_features_timestamp ON ai_features(timestamp);
CREATE INDEX IF NOT EXISTS idx_ai_features_symbol ON ai_features(symbol);

-- Add missing index for ai_models
CREATE INDEX IF NOT EXISTS idx_ai_models_created_at ON ai_models(created_at);

-- Insert default formula_master data if empty
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM formula_master LIMIT 1) THEN
        INSERT INTO formula_master (formula_name, formula_type, formula_definition, parameters, conditions, confidence_threshold, is_active) VALUES
        ('PCR_Bullish', 'RULE_BASED', 'PCR > 1.2 AND spot_price > 20000', '{"pcr_threshold": 1.2, "min_spot": 20000}', 'pcr > 1.2 AND spot_price > 20000', 0.7, true),
        ('PCR_Bearish', 'RULE_BASED', 'PCR < 0.8 AND spot_price < 20000', '{"pcr_threshold": 0.8, "max_spot": 20000}', 'pcr < 0.8 AND spot_price < 20000', 0.7, true),
        ('OI_Velocity_Bullish', 'RULE_BASED', 'oi_velocity > 100 AND total_call_oi > total_put_oi', '{"min_oi_velocity": 100}', 'oi_velocity > 100 AND total_call_oi > total_put_oi', 0.6, true);
    END IF;
END
$$;

-- Migration complete
SELECT 'Migration 001: AI Schema Update Completed' as status;
