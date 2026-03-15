#!/usr/bin/env python3
"""
StrikeIQ Backend Health Diagnostic
Tests all core services without full application startup
"""

import asyncio
import sys
import os
sys.path.append('.')

# Load environment
from dotenv import load_dotenv
load_dotenv()

async def test_database():
    """Test PostgreSQL connection"""
    try:
        from app.models.database import test_db_connection
        db_ok = await test_db_connection()
        print('DATABASE: ' + ('OK' if db_ok else 'FAILED'))
        return db_ok
    except Exception as e:
        print('DATABASE: FAILED - ' + str(e))
        return False

async def test_redis():
    """Test Redis connection"""
    try:
        from app.core.redis_client import test_redis_connection
        redis_ok = await test_redis_connection()
        print('REDIS: ' + ('OK' if redis_ok else 'FAILED'))
        return redis_ok
    except Exception as e:
        print('REDIS: FAILED - ' + str(e))
        return False

async def test_redis_setget():
    """Test Redis SET/GET functionality"""
    try:
        from app.core.unified_redis_client import unified_redis_client
        await unified_redis_client.initialize()
        
        # Test SET
        result = await unified_redis_client.set('strikeiq:test', 'ok')
        print('REDIS SET: ' + ('OK' if result else 'FAILED'))
        
        # Test GET
        value = await unified_redis_client.get('strikeiq:test')
        print('REDIS GET: ' + ('OK' if value == 'ok' else 'FAILED'))
        return value == 'ok'
    except Exception as e:
        print('REDIS SET/GET: FAILED - ' + str(e))
        return False

async def test_database_query():
    """Test simple database query"""
    try:
        from app.models.database import engine
        from sqlalchemy import text
        
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            value = result.scalar()
            print('DATABASE QUERY: ' + ('OK' if value == 1 else 'FAILED'))
            return value == 1
    except Exception as e:
        print('DATABASE QUERY: FAILED - ' + str(e))
        return False

async def test_instrument_registry():
    """Test instrument registry loading"""
    try:
        from app.services.instrument_registry import get_instrument_registry
        registry = get_instrument_registry()
        await registry.load()
        print('INSTRUMENT REGISTRY: OK')
        return True
    except Exception as e:
        print('INSTRUMENT REGISTRY: FAILED - ' + str(e))
        return False

async def main():
    print('=== STRIKEIQ BACKEND HEALTH DIAGNOSTIC ===')
    print()
    
    # Test basic services
    db_ok = await test_database()
    redis_ok = await test_redis()
    
    print()
    print('=== FUNCTIONAL TESTS ===')
    
    # Test functionality
    redis_setget_ok = await test_redis_setget()
    db_query_ok = await test_database_query()
    registry_ok = await test_instrument_registry()
    
    print()
    print('=== SYSTEM HEALTH REPORT ===')
    print('DATABASE: ' + ('OK' if db_ok and db_query_ok else 'FAILED'))
    print('REDIS: ' + ('OK' if redis_ok and redis_setget_ok else 'FAILED'))
    print('INSTRUMENT_REGISTRY: ' + ('OK' if registry_ok else 'FAILED'))
    
    print()
    print('=== SUMMARY ===')
    all_ok = db_ok and redis_ok and redis_setget_ok and db_query_ok and registry_ok
    print('OVERALL STATUS: ' + ('HEALTHY' if all_ok else 'DEGRADED'))

if __name__ == "__main__":
    asyncio.run(main())
