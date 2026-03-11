
import asyncio
from ai.ai_db import ai_db

async def migrate_v7():
    print("Migrating ai_signal_logs for Phase 3 (exit_premium, pnl)...")
    
    queries = [
        "ALTER TABLE ai_signal_logs ADD COLUMN IF NOT EXISTS exit_premium FLOAT",
        "ALTER TABLE ai_signal_logs ADD COLUMN IF NOT EXISTS pnl FLOAT"
    ]
    
    for q in queries:
        try:
            await ai_db.execute_query(q)
            print(f"Executed: {q}")
        except Exception as e:
            print(f"Error executing {q}: {e}")

if __name__ == "__main__":
    asyncio.run(migrate_v7())
