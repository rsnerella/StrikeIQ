import asyncio
import os
import sys

# Add backend to path
sys.path.append(os.getcwd())

from ai.ai_db import ai_db

async def check():
    try:
        print("Checking market_snapshots columns...")
        res = await ai_db.fetch_query("SELECT column_name FROM information_schema.columns WHERE table_name = 'market_snapshots'")
        print(f"market_snapshots: {[r[0] for r in res]}")
        
        print("\nChecking ai_signal_logs columns...")
        res = await ai_db.fetch_query("SELECT column_name FROM information_schema.columns WHERE table_name = 'ai_signal_logs'")
        print(f"ai_signal_logs: {[r[0] for r in res]}")
        
        print("\nChecking formula_experience columns...")
        res = await ai_db.fetch_query("SELECT column_name FROM information_schema.columns WHERE table_name = 'formula_experience'")
        print(f"formula_experience: {[r[0] for r in res]}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check())
