import asyncio
import sys
sys.path.append('.')
from dotenv import load_dotenv
load_dotenv()

async def test_db():
    try:
        from app.models.database import test_db_connection
        result = await test_db_connection()
        print('DATABASE CONNECTION: ' + ('OK' if result else 'FAILED'))
        return result
    except Exception as e:
        print('DATABASE CONNECTION: FAILED - ' + str(e))
        return False

asyncio.run(test_db())
