import asyncio
import os
import sys

sys.path.append(os.getcwd())

from ai.ai_db import ai_db

async def migrate():
    try:
        print("Running migrations...")
        
        # market_snapshots
        await ai_db.execute_query("ALTER TABLE market_snapshots ADD COLUMN IF NOT EXISTS pcr DOUBLE PRECISION")
        await ai_db.execute_query("ALTER TABLE market_snapshots ADD COLUMN IF NOT EXISTS total_call_oi BIGINT")
        await ai_db.execute_query("ALTER TABLE market_snapshots ADD COLUMN IF NOT EXISTS total_put_oi BIGINT")
        await ai_db.execute_query("ALTER TABLE market_snapshots ADD COLUMN IF NOT EXISTS atm_strike DOUBLE PRECISION")
        print("market_snapshots updated")
        
        # ai_signal_logs
        await ai_db.execute_query("ALTER TABLE ai_signal_logs ADD COLUMN IF NOT EXISTS snapshot_id INTEGER")
        await ai_db.execute_query("ALTER TABLE ai_signal_logs ADD COLUMN IF NOT EXISTS strike DOUBLE PRECISION")
        await ai_db.execute_query("ALTER TABLE ai_signal_logs ADD COLUMN IF NOT EXISTS direction VARCHAR(10)")
        await ai_db.execute_query("ALTER TABLE ai_signal_logs ADD COLUMN IF NOT EXISTS entry DOUBLE PRECISION")
        await ai_db.execute_query("ALTER TABLE ai_signal_logs ADD COLUMN IF NOT EXISTS stop_loss DOUBLE PRECISION")
        await ai_db.execute_query("ALTER TABLE ai_signal_logs ADD COLUMN IF NOT EXISTS target DOUBLE PRECISION")
        print("ai_signal_logs updated")
        
        # formula_experience
        await ai_db.execute_query("DROP TABLE IF EXISTS formula_experience")
        await ai_db.execute_query("""
            CREATE TABLE formula_experience (
                id SERIAL PRIMARY KEY,
                formula_id VARCHAR(50),
                total_tests INTEGER DEFAULT 0,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                accuracy DOUBLE PRECISION DEFAULT 0.0,
                avg_reward DOUBLE PRECISION DEFAULT 0.0,
                avg_risk DOUBLE PRECISION DEFAULT 0.0,
                confidence_adjustment DOUBLE PRECISION DEFAULT 0.0,
                success_rate DOUBLE PRECISION DEFAULT 0.0,
                experience_adjusted_confidence DOUBLE PRECISION DEFAULT 0.5,
                last_updated TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        print("formula_experience recreated")
        
        print("Migration completed successfully")
    except Exception as e:
        print(f"Migration failed: {e}")

if __name__ == "__main__":
    asyncio.run(migrate())
