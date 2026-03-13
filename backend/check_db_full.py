import asyncio
import os
import sys

# Add backend to path
sys.path.append(os.getcwd())

from ai.ai_db import ai_db

async def check_ml_data():
    try:
        print("Checking all tables in database...")
        tables_query = "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
        tables = await ai_db.fetch_query(tables_query)
        print(f"Tables: {[t[0] for t in tables]}")
        
        for table in [t[0] for t in tables]:
            count = await ai_db.fetch_one(f"SELECT COUNT(*) FROM {table}")
            print(f"- {table}: {count[0]} entries")
            
    except Exception as e:
        print(f"Error checking ML data: {e}")

if __name__ == "__main__":
    asyncio.run(check_ml_data())
