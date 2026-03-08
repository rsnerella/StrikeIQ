"""
Working database connection test with proper URL format
"""
import asyncio
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_working_db():
    """Test with standard Supabase connection pattern"""
    try:
        # Standard Supabase connection format
        db_url = "postgresql+asyncpg://postgres.YOUR_PASSWORD@db.YOUR_PROJECT_REF.supabase.co:5432/postgres"
        
        logger.info("Testing with standard Supabase URL format...")
        logger.info("Note: Replace YOUR_PASSWORD and YOUR_PROJECT_REF with actual values")
        
        # Create engine with minimal settings for testing
        engine = create_async_engine(
            db_url,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            echo=False
        )
        
        # Test connection
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT version()"))
            version = result.scalar()
            
        logger.info(f"✅ Connection successful! PostgreSQL version: {version}")
        await engine.dispose()
        return True
        
    except Exception as e:
        logger.error(f"❌ Connection failed: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_working_db())
