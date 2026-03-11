
import asyncio
from ai.ai_db import ai_db

async def migrate_v9():
    print("Fixing outcome_log column types...")
    
    queries = [
        "ALTER TABLE outcome_log ALTER COLUMN predicted_outcome TYPE TEXT",
        "ALTER TABLE outcome_log ALTER COLUMN actual_outcome TYPE TEXT"
    ]
    
    for q in queries:
        try:
            await ai_db.execute_query(q)
            print(f"Executed: {q}")
        except Exception as e:
            print(f"Error executing {q}: {e}")

if __name__ == "__main__":
    asyncio.run(migrate_v9())
