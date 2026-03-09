import asyncio
import os
import sys
from dotenv import load_dotenv

# Add backend to path so we can import db
sys.path.append(os.path.join(os.getcwd(), "backend"))

# Load environment variables
load_dotenv(os.path.join(os.getcwd(), "backend", ".env"))

from db.database import engine
from sqlalchemy import text

async def create_table():
    query = """
    CREATE TABLE IF NOT EXISTS ai_trade_history (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        symbol TEXT,
        strategy TEXT,
        direction TEXT,
        trade_type TEXT,
        entry_price DOUBLE PRECISION,
        target_price DOUBLE PRECISION,
        stoploss_price DOUBLE PRECISION,
        confidence DOUBLE PRECISION,
        trade_reason TEXT,
        strike DOUBLE PRECISION,
        lot_size INTEGER,
        expected_profit DOUBLE PRECISION,
        expected_loss DOUBLE PRECISION,
        opened_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        closed_at TIMESTAMP WITH TIME ZONE,
        exit_price DOUBLE PRECISION,
        pnl DOUBLE PRECISION,
        result TEXT,
        market_regime TEXT,
        signal_strength DOUBLE PRECISION
    );
    """
    try:
        async with engine.begin() as conn:
            await conn.execute(text(query))
        print("Table ai_trade_history created successfully.")
    except Exception as e:
        print(f"Error creating table: {e}")

if __name__ == "__main__":
    asyncio.run(create_table())
