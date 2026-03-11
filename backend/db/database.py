from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
import os
import ssl
import asyncio
import asyncpg
from urllib.parse import urlparse

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://localhost:5432/postgres"
)
print("DEBUG DATABASE_URL:", DATABASE_URL)

if DATABASE_URL is None:
    raise RuntimeError("DATABASE_URL is not loaded from environment")

parsed = urlparse(DATABASE_URL)
print("DEBUG DB HOST:", parsed.hostname)
print("DEBUG DB USER:", parsed.username)
print("DEBUG DB PORT:", parsed.port)

async def debug_db_connection():
    try:
        # asyncpg doesn't support +asyncpg scheme, fix for debug connect
        dsn = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
        conn = await asyncpg.connect(dsn)
        print("DEBUG: asyncpg connection SUCCESS")
        await conn.close()
    except Exception as e:
        print("DEBUG: asyncpg connection FAILED:", str(e))

# Note: In a script context this will run, in a worker context it might need an event loop
try:
    asyncio.create_task(debug_db_connection())
except RuntimeError:
    # If no event loop is running yet (e.g. startup), this will fail
    # We can use it for simple script testing
    pass


ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

engine = create_async_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args={"ssl": ssl_context}
)

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)