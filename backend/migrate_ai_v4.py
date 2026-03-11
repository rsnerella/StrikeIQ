
import asyncio
from ai.ai_db import ai_db

async def migrate_v4():
    print("Migrating ai_signal_logs for Phase 4/5/6...")
    
    queries = [
        "ALTER TABLE ai_signal_logs ADD COLUMN IF NOT EXISTS entry_premium FLOAT",
        "ALTER TABLE ai_signal_logs ADD COLUMN IF NOT EXISTS observed_high FLOAT",
        "ALTER TABLE ai_signal_logs ADD COLUMN IF NOT EXISTS observed_low FLOAT",
        "ALTER TABLE ai_signal_logs ADD COLUMN IF NOT EXISTS signal_reason TEXT"
    ]
    
    for q in queries:
        try:
            await ai_db.execute_query(q)
            print(f"Executed: {q}")
        except Exception as e:
            print(f"Error executing {q}: {e}")

if __name__ == "__main__":
    asyncio.run(migrate_v4())
