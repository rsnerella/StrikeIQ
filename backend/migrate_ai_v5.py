
import asyncio
from ai.ai_db import ai_db

async def migrate_v5():
    print("Renaming outcome_log.prediction_id to signal_id...")
    
    queries = [
        "ALTER TABLE outcome_log RENAME COLUMN prediction_id TO signal_id"
    ]
    
    for q in queries:
        try:
            await ai_db.execute_query(q)
            print(f"Executed: {q}")
        except Exception as e:
            print(f"Error executing {q}: {e}")

if __name__ == "__main__":
    asyncio.run(migrate_v5())
