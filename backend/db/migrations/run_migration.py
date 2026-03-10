#!/usr/bin/env python3
"""
StrikeIQ Migration Runner
Runs database migrations to update Supabase schema
"""

import os
import sys
import asyncio
import asyncpg
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.core.config import settings

async def run_migration():
    """Run the migration script"""
    try:
        # Connect to Supabase PostgreSQL
        # Convert SQLAlchemy URL to asyncpg format
        db_url = settings.DATABASE_URL
        if db_url.startswith('postgresql+asyncpg://'):
            db_url = db_url.replace('postgresql+asyncpg://', 'postgresql://')
        elif db_url.startswith('postgresql://'):
            pass  # Already correct
        else:
            raise ValueError(f"Unsupported database URL format: {db_url}")
        
        conn = await asyncpg.connect(
            db_url,
            server_settings={'application_name': 'strikeiq_migration'}
        )
        
        logger.info("✅ Connected to Supabase PostgreSQL")
        
        # Read migration file
        migration_file = Path(__file__).parent / "001_update_ai_schema.sql"
        with open(migration_file, 'r') as f:
            migration_sql = f.read()
        
        logger.info(f"📄 Loaded migration: {migration_file.name}")
        
        # Execute migration
        try:
            await conn.execute(migration_sql)
            logger.info("✅ Migration executed successfully")
        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
            raise
        
        # Verify changes
        print("\n🔍 Verifying migration results...")
        
        # Check ai_predictions table
        result = await conn.fetch("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'ai_predictions' 
            ORDER BY ordinal_position
        """)
        print("📊 ai_predictions columns:")
        for row in result:
            print(f"  - {row['column_name']}: {row['data_type']}")
        
        # Check formula_master table
        result = await conn.fetch("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'formula_master' 
            ORDER BY ordinal_position
        """)
        print("\n📊 formula_master columns:")
        for row in result:
            print(f"  - {row['column_name']}: {row['data_type']}")
        
        # Check market_snapshot table exists
        result = await conn.fetch("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'market_snapshot'
            ) as exists
        """)
        if result[0]['exists']:
            print("✅ market_snapshot table created")
        else:
            print("❌ market_snapshot table not found")
        
        # Check indexes
        result = await conn.fetch("""
            SELECT indexname 
            FROM pg_indexes 
            WHERE tablename IN ('ai_predictions', 'formula_master', 'prediction_log', 'signal_outcomes', 'paper_trade_log', 'market_snapshot')
            ORDER BY tablename, indexname
        """)
        print("\n📈 Created indexes:")
        for row in result:
            print(f"  - {row['indexname']}")
        
        # Test backend compatibility
        print("\n🧪 Testing backend compatibility...")
        
        # Test ai_signal_engine query
        try:
            result = await conn.fetch("""
                SELECT id, formula_name, conditions, confidence_threshold, is_active
                FROM formula_master 
                WHERE is_active = TRUE
                LIMIT 3
            """)
            print(f"✅ formula_master query works: {len(result)} active formulas")
        except Exception as e:
            print(f"❌ formula_master query failed: {e}")
        
        # Test probability_engine query
        try:
            result = await conn.fetch("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'ai_predictions' 
                AND column_name IN ('probability', 'signal', 'target', 'stop')
            """)
            if len(result) == 4:
                print("✅ ai_predictions has all required columns for probability_engine")
            else:
                print(f"❌ ai_predictions missing columns: {len(result)}/4 found")
        except Exception as e:
            print(f"❌ ai_predictions column check failed: {e}")
        
        await conn.close()
        print("\n🎉 Migration completed successfully!")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    logger.info("🚀 Starting StrikeIQ Database Migration...")
    asyncio.run(run_migration())
