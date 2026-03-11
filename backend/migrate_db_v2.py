import asyncio
import os
import sys

sys.path.append(os.getcwd())

from ai.ai_db import ai_db

async def migrate():
    try:
        print("Running quick migration for outcome_checked...")
        await ai_db.execute_query("ALTER TABLE ai_signal_logs ADD COLUMN IF NOT EXISTS outcome_checked BOOLEAN DEFAULT FALSE")
        print("outcome_checked added")
    except Exception as e:
        print(f"Migration failed: {e}")

if __name__ == "__main__":
    asyncio.run(migrate())
