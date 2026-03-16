"""
Async Database Layer for StrikeIQ
Replaces synchronous psycopg2 with asyncpg connection pooling
"""

import asyncpg
import asyncio
from typing import Optional, Dict, Any, List, Union
from contextlib import asynccontextmanager
import logging
from ..core.config import settings

logger = logging.getLogger(__name__)

class AsyncDatabase:
    """Async database connection manager with connection pooling"""
    
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize connection pool"""
        if self._initialized:
            return
        
        try:
            # Parse database URL
            db_url = settings.DATABASE_URL
            
            # Extract basic scheme only (asyncpg hates '+psycopg' or '+asyncpg' dialects in DSN)
            if "://" in db_url:
                scheme, rest = db_url.split("://", 1)
                base_scheme = scheme.split("+")[0]
                db_url = f"{base_scheme}://{rest}"
            
            # Ensure it's postgresql/postgres
            if not (db_url.startswith("postgresql://") or db_url.startswith("postgres://")):
                logger.warning(f"Unexpected DB scheme in {db_url}, attempting anyway...")

            self.pool = await asyncpg.create_pool(
                db_url,
                min_size=5,
                max_size=20,
                command_timeout=60,
                server_settings={
                    'application_name': 'strikeiq',
                    'timezone': 'UTC'
                }
            )
            self._initialized = True
            logger.info("✅ Async database pool initialized")
            
        except Exception as e:
            logger.error(f"❌ Database pool initialization failed: {e}")
            raise
    
    async def close(self):
        """Close connection pool"""
        if self.pool:
            await self.pool.close()
            self._initialized = False
            logger.info("✅ Database pool closed")
    
    @asynccontextmanager
    async def get_connection(self):
        """Get database connection from pool"""
        if not self._initialized:
            await self.initialize()
        
        async with self.pool.acquire() as connection:
            yield connection
    
    async def execute(self, query: str, *args) -> str:
        """Execute SQL query without returning results"""
        async with self.get_connection() as conn:
            try:
                result = await conn.execute(query, *args)
                return result
            except Exception as e:
                logger.error(f"Query execution failed: {e}")
                raise
    
    async def fetch(self, query: str, *args) -> List[Dict[str, Any]]:
        """Execute query and return all results"""
        async with self.get_connection() as conn:
            try:
                rows = await conn.fetch(query, *args)
                return [dict(row) for row in rows]
            except Exception as e:
                logger.error(f"Query fetch failed: {e}")
                raise
    
    async def fetchrow(self, query: str, *args) -> Optional[Dict[str, Any]]:
        """Execute query and return single result"""
        async with self.get_connection() as conn:
            try:
                row = await conn.fetchrow(query, *args)
                return dict(row) if row else None
            except Exception as e:
                logger.error(f"Query fetchrow failed: {e}")
                raise
    
    async def fetchval(self, query: str, *args) -> Any:
        """Execute query and return single value"""
        async with self.get_connection() as conn:
            try:
                return await conn.fetchval(query, *args)
            except Exception as e:
                logger.error(f"Query fetchval failed: {e}")
                raise
    
    async def execute_transaction(self, queries: List[tuple]) -> bool:
        """Execute multiple queries in a transaction"""
        async with self.get_connection() as conn:
            try:
                async with conn.transaction():
                    for query, args in queries:
                        await conn.execute(query, *args)
                return True
            except Exception as e:
                logger.error(f"Transaction failed: {e}")
                return False
    
    async def insert_and_return_id(self, query: str, *args) -> int:
        """Insert record and return ID"""
        async with self.get_connection() as conn:
            try:
                result = await conn.fetchval(query + " RETURNING id", *args)
                return result
            except Exception as e:
                logger.error(f"Insert with ID failed: {e}")
                raise

# Global database instance
async_db = AsyncDatabase()

# Convenience functions
async def get_async_db():
    """Get async database instance"""
    return async_db

async def get_db_pool():
    """Get database pool for probability engine"""
    return async_db.pool

async def execute_query(query: str, *args) -> str:
    """Execute query without results"""
    return await async_db.execute(query, *args)

async def fetch_query(query: str, *args) -> List[Dict[str, Any]]:
    """Execute query and return results"""
    return await async_db.fetch(query, *args)

async def fetch_one(query: str, *args) -> Optional[Dict[str, Any]]:
    """Execute query and return single result"""
    return await async_db.fetchrow(query, *args)

async def execute_transaction(queries: List[tuple]) -> bool:
    """Execute transaction"""
    return await async_db.execute_transaction(queries)
