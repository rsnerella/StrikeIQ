
import asyncio
from ai.ai_db import ai_db

async def main():
    res = await ai_db.fetch_query("SELECT id, formula_name, conditions FROM formula_master WHERE formula_name LIKE 'PCR%'")
    for r in res:
        print(f"ID: {r[0]}, Name: {r[1]}, Conditions: {r[2]}")

if __name__ == "__main__":
    asyncio.run(main())
