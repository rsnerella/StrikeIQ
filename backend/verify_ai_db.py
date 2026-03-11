
import asyncio
from ai.ai_db import ai_db

async def verify_schema():
    print("Verifying Database Schema for StrikeIQ AI System...")
    
    tables = [
        "market_snapshots",
        "ai_signal_logs",
        "outcome_log",
        "formula_experience",
        "system_config",
        "formula_master"
    ]
    
    print("-" * 50)
    for table in tables:
        try:
            query = f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table}'"
            cols = await ai_db.fetch_query(query)
            col_names = [c[0] for c in cols]
            print(f"Table: {table}")
            print(f"Columns: {col_names}")
            print("-" * 20)
        except Exception as e:
            print(f"Error checking table {table}: {e}")
    print("-" * 50)

if __name__ == "__main__":
    asyncio.run(verify_schema())
