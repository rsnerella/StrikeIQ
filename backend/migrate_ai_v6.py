
import asyncio
from ai.ai_db import ai_db

async def migrate_v6():
    print("Migrating formula_experience...")
    
    queries = [
        "ALTER TABLE formula_experience ADD COLUMN IF NOT EXISTS experience_adjusted_confidence FLOAT DEFAULT 0",
        "ALTER TABLE formula_experience ADD COLUMN IF NOT EXISTS confidence_stats JSONB DEFAULT '{}'"
    ]
    
    for q in queries:
        try:
            await ai_db.execute_query(q)
            print(f"Executed: {q}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(migrate_v6())
