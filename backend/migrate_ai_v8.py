
import asyncio
from ai.ai_db import ai_db

async def migrate_v8():
    print("Migrating ai_signal_logs for Phase 4 (formula_id)...")
    
    queries = [
        "ALTER TABLE ai_signal_logs ADD COLUMN IF NOT EXISTS formula_id TEXT"
    ]
    
    for q in queries:
        try:
            await ai_db.execute_query(q)
            print(f"Executed: {q}")
        except Exception as e:
            print(f"Error executing {q}: {e}")

if __name__ == "__main__":
    asyncio.run(migrate_v8())
