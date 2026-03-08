-- StrikeIQ Database Schema
-- PostgreSQL schema dump for Supabase

-- AI Signal Logs Table
CREATE TABLE IF NOT EXISTS ai_signal_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    symbol VARCHAR,
    signal VARCHAR,
    confidence FLOAT,
    spot_price FLOAT,
    metadata JSON
);
CREATE INDEX IF NOT EXISTS idx_ai_signal_logs_timestamp ON ai_signal_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_ai_signal_logs_symbol ON ai_signal_logs(symbol);
CREATE INDEX IF NOT EXISTS idx_ai_signal_logs_signal ON ai_signal_logs(signal);

-- Market Snapshots Table
CREATE TABLE IF NOT EXISTS market_snapshots (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    spot_price FLOAT,
    vwap FLOAT,
    change FLOAT,
    change_percent FLOAT,
    volume INTEGER,
    market_status VARCHAR,
    rsi FLOAT,
    momentum_score FLOAT,
    regime VARCHAR
);
CREATE INDEX IF NOT EXISTS idx_market_snapshots_timestamp ON market_snapshots(timestamp);
CREATE INDEX IF NOT EXISTS idx_market_snapshots_symbol ON market_snapshots(symbol);

-- Option Chain Snapshots Table
CREATE TABLE IF NOT EXISTS option_chain_snapshots (
    id SERIAL PRIMARY KEY,
    market_snapshot_id INTEGER REFERENCES market_snapshots(id),
    symbol VARCHAR,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    strike FLOAT,
    option_type VARCHAR,
    expiry VARCHAR,
    oi INTEGER,
    oi_change INTEGER,
    prev_oi INTEGER,
    oi_delta INTEGER,
    ltp FLOAT,
    iv FLOAT,
    volume INTEGER,
    theta FLOAT,
    delta FLOAT,
    gamma FLOAT,
    vega FLOAT
);
CREATE INDEX IF NOT EXISTS idx_option_chain_snapshots_timestamp ON option_chain_snapshots(timestamp);
CREATE INDEX IF NOT EXISTS idx_option_chain_snapshots_symbol ON option_chain_snapshots(symbol);
CREATE INDEX IF NOT EXISTS idx_option_chain_snapshots_strike ON option_chain_snapshots(strike);

-- Smart Money Predictions Table
CREATE TABLE IF NOT EXISTS smart_money_predictions (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    symbol VARCHAR,
    bias VARCHAR,
    confidence FLOAT,
    pcr FLOAT,
    pcr_shift_z FLOAT,
    atm_straddle FLOAT,
    straddle_change_normalized FLOAT,
    oi_acceleration_ratio FLOAT,
    iv_regime VARCHAR,
    actual_move FLOAT,
    result VARCHAR,
    model_version VARCHAR DEFAULT 'v1.0',
    expiry_date VARCHAR
);
CREATE INDEX IF NOT EXISTS idx_smart_money_predictions_timestamp ON smart_money_predictions(timestamp);
CREATE INDEX IF NOT EXISTS idx_smart_money_predictions_symbol ON smart_money_predictions(symbol);

-- Predictions Table
CREATE TABLE IF NOT EXISTS predictions (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    symbol VARCHAR,
    bullish_probability FLOAT,
    volatility_probability FLOAT,
    confidence_score FLOAT,
    regime VARCHAR,
    actual_move_30m FLOAT,
    accuracy_score FLOAT,
    model_version VARCHAR
);
CREATE INDEX IF NOT EXISTS idx_predictions_timestamp ON predictions(timestamp);
CREATE INDEX IF NOT EXISTS idx_predictions_symbol ON predictions(symbol);

-- Additional tables mentioned in requirements
CREATE TABLE IF NOT EXISTS ai_event_log (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    event_type VARCHAR,
    description TEXT,
    metadata JSON
);

CREATE TABLE IF NOT EXISTS ai_features (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    feature_name VARCHAR,
    feature_value FLOAT,
    metadata JSON
);

CREATE TABLE IF NOT EXISTS ai_models (
    id SERIAL PRIMARY KEY,
    model_name VARCHAR,
    version VARCHAR,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    model_config JSON,
    performance_metrics JSON
);

CREATE TABLE IF NOT EXISTS ai_predictions (
    id SERIAL PRIMARY KEY,
    model_id INTEGER REFERENCES ai_models(id),
    symbol VARCHAR,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    prediction_type VARCHAR,
    prediction_value FLOAT,
    confidence FLOAT,
    metadata JSON
);

CREATE TABLE IF NOT EXISTS formula_experience (
    id SERIAL PRIMARY KEY,
    formula_name VARCHAR,
    symbol VARCHAR,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    experience_data JSON,
    performance_score FLOAT
);

CREATE TABLE IF NOT EXISTS formula_master (
    id SERIAL PRIMARY KEY,
    formula_name VARCHAR UNIQUE,
    formula_type VARCHAR,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    formula_definition TEXT,
    parameters JSON
);

CREATE TABLE IF NOT EXISTS outcome_log (
    id SERIAL PRIMARY KEY,
    prediction_id INTEGER,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    actual_outcome FLOAT,
    predicted_outcome FLOAT,
    accuracy FLOAT,
    metadata JSON
);

CREATE TABLE IF NOT EXISTS paper_trade_log (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR,
    trade_type VARCHAR,
    entry_price FLOAT,
    exit_price FLOAT,
    quantity INTEGER,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    pnl FLOAT,
    metadata JSON
);

CREATE TABLE IF NOT EXISTS prediction_log (
    id SERIAL PRIMARY KEY,
    prediction_type VARCHAR,
    symbol VARCHAR,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    prediction_data JSON,
    confidence FLOAT,
    status VARCHAR
);

CREATE TABLE IF NOT EXISTS signal_outcomes (
    id SERIAL PRIMARY KEY,
    signal_id INTEGER,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    outcome_type VARCHAR,
    outcome_value FLOAT,
    accuracy FLOAT,
    metadata JSON
);
