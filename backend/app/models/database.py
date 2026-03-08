from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text
from ..core.config import settings
import logging

logger = logging.getLogger(__name__)

SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

# Verify asyncpg driver for async FastAPI
if not SQLALCHEMY_DATABASE_URL.startswith("postgresql+asyncpg://"):
    raise ValueError("DATABASE_URL must use postgresql+asyncpg:// driver for async FastAPI")

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True
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

async def test_db_connection():
    """Test Supabase PostgreSQL connection"""
    try:
        logger.info("Checking database connectivity...")
        
        # Test connection with simple query
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1 as test"))
            test_value = result.scalar()
            
        if test_value == 1:
            logger.info("✅ Database connection successful")
            return True
        else:
            logger.error("❌ Database test query failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False
