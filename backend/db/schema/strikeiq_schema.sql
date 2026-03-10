-- ======================================================
-- StrikeIQ Production Database Schema (Fixed Version)
-- ======================================================

-- ===============================
-- AI SIGNAL LOGS
-- ===============================

CREATE TABLE IF NOT EXISTS ai_signal_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    symbol VARCHAR(20),
    signal VARCHAR(20),
    confidence DOUBLE PRECISION,
    spot_price DOUBLE PRECISION,
    metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_ai_signal_logs_symbol_time
ON ai_signal_logs(symbol, timestamp DESC);


-- ===============================
-- MARKET SNAPSHOTS
-- ===============================

CREATE TABLE IF NOT EXISTS market_snapshots (

    id SERIAL PRIMARY KEY,

    symbol VARCHAR(20),

    timestamp TIMESTAMPTZ DEFAULT NOW(),

    spot_price DOUBLE PRECISION,

    vwap DOUBLE PRECISION,

    change DOUBLE PRECISION,

    change_percent DOUBLE PRECISION,

    volume BIGINT,

    market_status VARCHAR(20),

    rsi DOUBLE PRECISION,

    momentum_score DOUBLE PRECISION,

    regime VARCHAR(20)
);

CREATE INDEX IF NOT EXISTS idx_market_snapshots_symbol_time
ON market_snapshots(symbol, timestamp DESC);


-- ===============================
-- OPTION CHAIN SNAPSHOTS
-- ===============================

CREATE TABLE IF NOT EXISTS option_chain_snapshots (

    id SERIAL PRIMARY KEY,

    market_snapshot_id INTEGER
    REFERENCES market_snapshots(id),

    symbol VARCHAR(20),

    timestamp TIMESTAMPTZ DEFAULT NOW(),

    strike DOUBLE PRECISION,

    option_type VARCHAR(2),

    expiry DATE,

    oi BIGINT,

    oi_change BIGINT,

    prev_oi BIGINT,

    oi_delta BIGINT,

    ltp DOUBLE PRECISION,

    iv DOUBLE PRECISION,

    volume BIGINT,

    theta DOUBLE PRECISION,

    delta DOUBLE PRECISION,

    gamma DOUBLE PRECISION,

    vega DOUBLE PRECISION
);

CREATE INDEX IF NOT EXISTS idx_option_chain_lookup
ON option_chain_snapshots(symbol, expiry, strike, option_type);

CREATE INDEX IF NOT EXISTS idx_option_chain_time
ON option_chain_snapshots(timestamp DESC);


-- ===============================
-- SMART MONEY PREDICTIONS
-- ===============================

CREATE TABLE IF NOT EXISTS smart_money_predictions (

    id SERIAL PRIMARY KEY,

    timestamp TIMESTAMPTZ DEFAULT NOW(),

    symbol VARCHAR(20),

    bias VARCHAR(10),

    confidence DOUBLE PRECISION,

    pcr DOUBLE PRECISION,

    pcr_shift_z DOUBLE PRECISION,

    atm_straddle DOUBLE PRECISION,

    straddle_change_normalized DOUBLE PRECISION,

    oi_acceleration_ratio DOUBLE PRECISION,

    iv_regime VARCHAR(20),

    actual_move DOUBLE PRECISION,

    result VARCHAR(10),

    model_version VARCHAR(20) DEFAULT 'v1.0',

    expiry_date DATE
);

CREATE INDEX IF NOT EXISTS idx_smart_money_predictions_symbol_time
ON smart_money_predictions(symbol, timestamp DESC);


-- ===============================
-- GENERIC PREDICTIONS
-- ===============================

CREATE TABLE IF NOT EXISTS predictions (

    id SERIAL PRIMARY KEY,

    timestamp TIMESTAMPTZ DEFAULT NOW(),

    symbol VARCHAR(20),

    bullish_probability DOUBLE PRECISION,

    volatility_probability DOUBLE PRECISION,

    confidence_score DOUBLE PRECISION,

    regime VARCHAR(20),

    actual_move_30m DOUBLE PRECISION,

    accuracy_score DOUBLE PRECISION,

    model_version VARCHAR(20)
);

CREATE INDEX IF NOT EXISTS idx_predictions_symbol_time
ON predictions(symbol, timestamp DESC);


-- ===============================
-- AI FEATURES
-- ===============================

CREATE TABLE IF NOT EXISTS ai_features (

    id SERIAL PRIMARY KEY,

    symbol VARCHAR(20),

    timestamp TIMESTAMPTZ DEFAULT NOW(),

    feature_name VARCHAR(50),

    feature_value DOUBLE PRECISION,

    metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_ai_features_symbol_time
ON ai_features(symbol, timestamp DESC);


-- ===============================
-- AI MODELS
-- ===============================

CREATE TABLE IF NOT EXISTS ai_models (

    id SERIAL PRIMARY KEY,

    model_name VARCHAR(50),

    version VARCHAR(20),

    created_at TIMESTAMPTZ DEFAULT NOW(),

    model_config JSONB,

    performance_metrics JSONB
);


-- ===============================
-- AI PREDICTIONS
-- ===============================

CREATE TABLE IF NOT EXISTS ai_predictions (

    id SERIAL PRIMARY KEY,

    model_id INTEGER REFERENCES ai_models(id),

    symbol VARCHAR(20),

    timestamp TIMESTAMPTZ DEFAULT NOW(),

    prediction_type VARCHAR(50),

    prediction_value DOUBLE PRECISION,

    confidence DOUBLE PRECISION,

    probability DOUBLE PRECISION,

    signal VARCHAR(20),

    target DOUBLE PRECISION,

    stop DOUBLE PRECISION,

    metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_ai_predictions_symbol_time
ON ai_predictions(symbol, timestamp DESC);


-- ===============================
-- FORMULA MASTER
-- ===============================

CREATE TABLE IF NOT EXISTS formula_master (

    id SERIAL PRIMARY KEY,

    formula_name VARCHAR UNIQUE,

    formula_type VARCHAR,

    created_at TIMESTAMPTZ DEFAULT NOW(),

    formula_definition TEXT,

    parameters JSONB,

    conditions TEXT,

    confidence_threshold DOUBLE PRECISION,

    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_formula_master_active
ON formula_master(is_active)
WHERE is_active = TRUE;


-- ===============================
-- FORMULA EXPERIENCE
-- ===============================

CREATE TABLE IF NOT EXISTS formula_experience (

    id SERIAL PRIMARY KEY,

    formula_name VARCHAR,

    symbol VARCHAR(20),

    timestamp TIMESTAMPTZ DEFAULT NOW(),

    experience_data JSONB,

    performance_score DOUBLE PRECISION
);


-- ===============================
-- PREDICTION LOG
-- ===============================

CREATE TABLE IF NOT EXISTS prediction_log (

    id SERIAL PRIMARY KEY,

    prediction_type VARCHAR,

    symbol VARCHAR(20),

    timestamp TIMESTAMPTZ DEFAULT NOW(),

    prediction_data JSONB,

    confidence DOUBLE PRECISION,

    status VARCHAR,

    formula_id INTEGER,

    signal VARCHAR,

    nifty_spot DOUBLE PRECISION,

    prediction_time TIMESTAMPTZ,

    outcome VARCHAR,

    outcome_time TIMESTAMPTZ,

    outcome_checked BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_prediction_log_symbol_time
ON prediction_log(symbol, timestamp DESC);


-- ===============================
-- PAPER TRADE LOG
-- ===============================

CREATE TABLE IF NOT EXISTS paper_trade_log (

    id SERIAL PRIMARY KEY,

    symbol VARCHAR(20),

    trade_type VARCHAR(10),

    entry_price DOUBLE PRECISION,

    exit_price DOUBLE PRECISION,

    quantity INTEGER,

    timestamp TIMESTAMPTZ DEFAULT NOW(),

    pnl DOUBLE PRECISION,

    prediction_id INTEGER REFERENCES prediction_log(id),

    metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_paper_trade_symbol_time
ON paper_trade_log(symbol, timestamp DESC);


-- ===============================
-- SIGNAL OUTCOMES
-- ===============================

CREATE TABLE IF NOT EXISTS signal_outcomes (

    id SERIAL PRIMARY KEY,

    signal_id INTEGER REFERENCES ai_signal_logs(id),

    timestamp TIMESTAMPTZ DEFAULT NOW(),

    outcome_type VARCHAR,

    outcome_value DOUBLE PRECISION,

    accuracy DOUBLE PRECISION,

    result VARCHAR,

    metadata JSONB
);


-- ======================================================
-- OPTIONAL CLEANUP FUNCTION (Prevents DB Explosion)
-- ======================================================

CREATE OR REPLACE FUNCTION cleanup_old_option_chain()
RETURNS void AS $$
BEGIN
    DELETE FROM option_chain_snapshots
    WHERE timestamp < NOW() - INTERVAL '2 days';
END;
$$ LANGUAGE plpgsql;