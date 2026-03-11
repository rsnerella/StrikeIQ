import asyncio
from app.models.database import engine
from sqlalchemy import text

async def create_tables():
    print("Creating system_config table...")
    async with engine.begin() as conn:
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS system_config (
                key VARCHAR PRIMARY KEY,
                value JSONB,
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        """))
    print("Done.")

if __name__ == "__main__":
    asyncio.run(create_tables())
