"""
Database connection test for Supabase PostgreSQL
"""
import asyncio
import logging
import sys
import os

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from app.core.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_db_connection():
    """Test Supabase PostgreSQL connection"""
    try:
        logger.info("Checking database connectivity...")
        
        # Verify DATABASE_URL format
        db_url = settings.DATABASE_URL
        logger.info(f"Database URL: {db_url.split('@')[0]}@***")
        
        # Ensure asyncpg driver for async FastAPI
        if not db_url.startswith("postgresql+asyncpg://"):
            logger.error("❌ DATABASE_URL must use postgresql+asyncpg:// driver")
            return False
        
        # Create async engine with safe pool settings
        engine = create_async_engine(
            db_url,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            echo=False  # Set to True for SQL debugging
        )
        
        # Test connection with simple query
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1 as test"))
            test_value = result.scalar()
            
        if test_value == 1:
            logger.info("✅ Database connection successful")
            logger.info("✅ Supabase PostgreSQL is reachable")
            return True
        else:
            logger.error("❌ Database test query failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False
    finally:
        if 'engine' in locals():
            await engine.dispose()

if __name__ == "__main__":
    asyncio.run(test_db_connection())
