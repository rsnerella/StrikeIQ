
import asyncio
from ai.ai_db import ai_db
import json

async def main():
    res = await ai_db.fetch_query("SELECT id, formula_name, conditions FROM formula_master WHERE is_active = TRUE LIMIT 5")
    for r in res:
        print(f"ID: {r[0]}, Name: {r[1]}, Conditions: {r[2]}")

if __name__ == "__main__":
    asyncio.run(main())
