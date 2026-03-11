
import asyncio
from ai.ai_db import ai_db

async def migrate():
    print("Migrating market_snapshots to include gamma_exposure and expected_move...")
    
    queries = [
        "ALTER TABLE market_snapshots ADD COLUMN IF NOT EXISTS gamma_exposure FLOAT DEFAULT 0",
        "ALTER TABLE market_snapshots ADD COLUMN IF NOT EXISTS expected_move FLOAT DEFAULT 0",
        "ALTER TABLE ai_signal_logs ADD COLUMN IF NOT EXISTS signal_reason TEXT"
    ]
    
    for q in queries:
        try:
            await ai_db.execute_query(q)
            print(f"Executed: {q}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(migrate())
