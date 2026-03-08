import asyncio
import os
import sys
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from app.core.config import settings
    DB_URL = settings.DATABASE_URL
except Exception:
    DB_URL = "postgresql://strikeiq:strikeiq123@localhost:5432/strikeiq"

engine = create_engine(DB_URL)

SQL_COMMANDS = [
    """
    CREATE TABLE IF NOT EXISTS ai_signal_logs (
        id SERIAL PRIMARY KEY,
        symbol VARCHAR,
        timestamp TIMESTAMP WITH TIME ZONE,
        signal_type VARCHAR,
        confidence FLOAT,
        price FLOAT,
        wave VARCHAR,
        trend VARCHAR,
        pcr FLOAT,
        gamma FLOAT,
        oi_velocity FLOAT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS signal_outcomes (
        id SERIAL PRIMARY KEY,
        signal_id INTEGER,
        price_after_5m FLOAT,
        price_after_15m FLOAT,
        price_after_30m FLOAT,
        result VARCHAR,
        evaluated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS ai_features (
        id SERIAL PRIMARY KEY,
        signal_id INTEGER,
        price FLOAT,
        pcr FLOAT,
        gamma_exposure FLOAT,
        oi_velocity FLOAT,
        wave VARCHAR,
        momentum FLOAT,
        volatility FLOAT,
        trend VARCHAR,
        label VARCHAR
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS ai_models (
        id SERIAL PRIMARY KEY,
        model_name VARCHAR,
        version VARCHAR,
        accuracy FLOAT,
        trained_on TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        dataset_size INTEGER
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS ai_predictions (
        id SERIAL PRIMARY KEY,
        symbol VARCHAR,
        timestamp TIMESTAMP WITH TIME ZONE,
        probability FLOAT,
        signal VARCHAR,
        target FLOAT,
        stop FLOAT
    );
    """
]

def create_tables():
    with engine.connect() as conn:
        for sql in SQL_COMMANDS:
            try:
                conn.execute(text(sql))
            except Exception as e:
                print(f"Failed to execute: {sql[:50]}... Error: {e}")
        conn.commit()
    print("AI Tables Verified/Created Successfully")

if __name__ == "__main__":
    create_tables()
