# Windows async event loop fix for psycopg compatibility
import sys
import asyncio
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(
        asyncio.WindowsSelectorEventLoopPolicy()
    )

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text
from ..core.config import settings
import logging
import ssl

logger = logging.getLogger(__name__)

SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

# Verify async driver for async FastAPI
if not (SQLALCHEMY_DATABASE_URL.startswith("postgresql+asyncpg://") or 
        SQLALCHEMY_DATABASE_URL.startswith("postgresql+psycopg://")):
    raise ValueError("DATABASE_URL must use postgresql+asyncpg:// or postgresql+psycopg:// driver")

ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    connect_args={"ssl": ssl_context}
)

AsyncSessionLocal = async_sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

def get_async_session():
    """Get async session for database operations"""
    return AsyncSessionLocal()

import asyncio

async def test_db_connection(max_retries: int = 3, delay: int = 5):
    """Test Supabase PostgreSQL connection with retry logic (Task 6)"""
    last_error = None
    
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Checking database connectivity (Attempt {attempt}/{max_retries})...")
            
            # Test connection with simple query
            async with engine.begin() as conn:
                result = await conn.execute(text("SELECT 1 as test"))
                test_value = result.scalar()
                
            if test_value == 1:
                logger.info("✅ Database connection successful")
                return True
            else:
                logger.error(f"❌ Database test query failed (Attempt {attempt})")
                
        except Exception as e:
            last_error = e
            logger.error(f"❌ Database connection failed (Attempt {attempt}): {e}")
            
            if attempt < max_retries:
                logger.info(f"Retrying in {delay} seconds...")
                await asyncio.sleep(delay)
    
    logger.critical(f"❌ Database connection fatally failed after {max_retries} attempts")
    return False
