import os
from dotenv import load_dotenv
load_dotenv()

print("DEBUG ENV DATABASE_URL:", os.getenv("DATABASE_URL"))

from db.database import debug_db_connection
import asyncio

async def test():
    await debug_db_connection()

if __name__ == "__main__":
    asyncio.run(test())
