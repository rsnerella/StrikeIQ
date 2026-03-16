import sys
import os
import asyncio
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verification")

async def verify_system():
    # 1. Test pathing and imports
    backend_root = os.path.abspath(os.path.dirname(__file__))
    if backend_root not in sys.path:
        sys.path.insert(0, backend_root)
    
    # Priorhesize backend over root if someone added root
    project_root = os.path.abspath(os.path.join(backend_root, '..'))
    if project_root in sys.path:
        sys.path.remove(project_root)
    sys.path.append(project_root)

    print(f"DEBUG: sys.path: {sys.path[:3]}...")
    
    try:
        from ai.prediction_service import prediction_service
        print("✅ Import verification: ai.prediction_service FOUND")
    except Exception as e:
        print(f"❌ Import verification FAILED: {e}")
        return

    # 2. Test database connection logic (stripping +psycopg)
    from app.core.config import settings
    from app.core.async_db import async_db
    
    print(f"DEBUG: DATABASE_URL: {settings.DATABASE_URL}")
    
    try:
        await async_db.initialize()
        print("✅ Database pool initialized successfully")
        
        # Simple query
        async with async_db.get_connection() as conn:
            val = await conn.fetchval("SELECT 1")
            print(f"✅ Database query test: 1 == {val}")
            
    except Exception as e:
        print(f"❌ Database verification FAILED: {e}")
    finally:
        await async_db.close()

if __name__ == "__main__":
    asyncio.run(verify_system())
