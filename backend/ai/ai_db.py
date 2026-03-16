# Windows async event loop fix for psycopg compatibility
import sys
import asyncio
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(
        asyncio.WindowsSelectorEventLoopPolicy()
    )

import logging
from typing import Optional, List, Dict, Any
from sqlalchemy import text
from app.models.database import engine, AsyncSessionLocal

logger = logging.getLogger(__name__)

class AIDatabase:
    """
    Refactored AI Database wrapper using centralized SQLAlchemy AsyncSession.
    Ensures all AI writes go to Supabase.
    """
    def __init__(self):
        pass
            
    async def execute_query(self, query: str, params: tuple = None) -> bool:
        """Execute a query with parameters (Async)"""
        try:
            # Map %s to :name for SQLAlchemy text() if needed
            # But simpler: just use text() and params
            async with engine.begin() as conn:
                # Basic conversion of %s to :param_N
                if "%s" in query:
                    query, params_dict = self._convert_params(query, params)
                    await conn.execute(text(query), params_dict)
                else:
                    await conn.execute(text(query), params or {})
            return True
        except Exception as e:
            logger.error(f"AI DB execute failed: {e}")
            return False
            
    async def fetch_query(self, query: str, params: tuple = None) -> List[Any]:
        """Execute a query and fetch results (Async)"""
        try:
            async with engine.connect() as conn:
                if "%s" in query:
                    query, params_dict = self._convert_params(query, params)
                    result = await conn.execute(text(query), params_dict)
                else:
                    result = await conn.execute(text(query), params or {})
                return [list(row) for row in result.fetchall()]
        except Exception as e:
            logger.error(f"AI DB fetch failed: {e}")
            return []
            
    async def fetch_one(self, query: str, params: tuple = None) -> Optional[Any]:
        """Execute a query and fetch single result (Async)"""
        try:
            async with engine.connect() as conn:
                if "%s" in query:
                    query, params_dict = self._convert_params(query, params)
                    result = await conn.execute(text(query), params_dict)
                else:
                    result = await conn.execute(text(query), params or {})
                row = result.fetchone()
                return list(row) if row else None
        except Exception as e:
            logger.error(f"AI DB fetch_one failed: {e}")
            return None

    def _convert_params(self, query: str, params: tuple) -> tuple:
        """Helper to convert %s to named parameters for SQLAlchemy"""
        if not params:
            return query, {}
        
        new_query = query
        params_dict = {}
        for i, val in enumerate(params):
            placeholder = f"p{i}"
            new_query = new_query.replace("%s", f":{placeholder}", 1)
            params_dict[placeholder] = val
        return new_query, params_dict

# Global database instance
ai_db = AIDatabase()

