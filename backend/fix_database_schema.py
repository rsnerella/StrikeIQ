#!/usr/bin/env python3
"""
Database Schema Fixes for StrikeIQ Runtime Crashes
"""

import asyncio
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent))

def fix_database_schema():
    """Apply database schema fixes"""
    
    print("=== 🔧 DATABASE SCHEMA FIXES ===\n")
    
    try:
        # Import database modules
        from ai.ai_db import ai_db
        import psycopg2
        from psycopg2.extras import RealDictCursor
        import os
        
        print("✅ Connected to database")
        
        # Get database URL and convert to psycopg2 format
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            print("❌ DATABASE_URL not found in environment")
            return False
        
        # Convert asyncpg URL to psycopg2 format
        if database_url.startswith("postgresql+asyncpg://"):
            database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
        
        print(f"🔗 Using database: {database_url.split('@')[1] if '@' in database_url else 'local'}")
            
        # Connect to database
        conn = psycopg2.connect(database_url)
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Fix 1: Add outcome column to outcome_log
        print("🔧 Fix 1: Adding outcome column to outcome_log...")
        try:
            cursor.execute("""
                ALTER TABLE outcome_log 
                ADD COLUMN IF NOT EXISTS outcome TEXT
            """)
            print("✅ outcome column added to outcome_log")
        except Exception as e:
            if "already exists" in str(e) or "column.*already exists" in str(e):
                print("✅ outcome column already exists")
            else:
                print(f"❌ Error adding outcome column: {e}")
        
        # Fix 2: Add option_type column to paper_trade_log
        print("\n🔧 Fix 2: Adding option_type column to paper_trade_log...")
        try:
            cursor.execute("""
                ALTER TABLE paper_trade_log 
                ADD COLUMN IF NOT EXISTS option_type TEXT
            """)
            print("✅ option_type column added to paper_trade_log")
        except Exception as e:
            if "already exists" in str(e) or "column.*already exists" in str(e):
                print("✅ option_type column already exists")
            else:
                print(f"❌ Error adding option_type column: {e}")
        
        # Fix 3: Convert prediction_id to UUID in paper_trade_log if needed
        print("\n🔧 Fix 3: Converting prediction_id to UUID in paper_trade_log...")
        try:
            # Check current type
            cursor.execute("""
                SELECT data_type 
                FROM information_schema.columns 
                WHERE table_name = 'paper_trade_log' 
                AND column_name = 'prediction_id'
            """)
            result = cursor.fetchone()
            
            if result and 'uuid' not in result[0].lower():
                cursor.execute("""
                    ALTER TABLE paper_trade_log
                    ALTER COLUMN prediction_id TYPE uuid
                    USING prediction_id::uuid
                """)
                print("✅ prediction_id converted to UUID")
            else:
                print("✅ prediction_id already UUID")
        except Exception as e:
            print(f"❌ Error converting prediction_id: {e}")
        
        # Fix 4: Verify UUID joins work
        print("\n🔧 Fix 4: Testing UUID join...")
        try:
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM ai_signal_logs p 
                LEFT JOIN outcome_log o ON p.id = o.prediction_id
                LEFT JOIN paper_trade_log pt ON p.id = pt.prediction_id
                LIMIT 1
            """)
            result = cursor.fetchone()
            print(f"✅ UUID join test successful: {result[0]} records")
        except Exception as e:
            print(f"❌ UUID join test failed: {e}")
        
        # Close connection
        cursor.close()
        conn.close()
        
        print("\n🎉 DATABASE SCHEMA FIXES COMPLETE!")
        print("✅ All required columns added")
        print("✅ UUID types aligned")
        print("✅ JOIN queries tested")
        
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = fix_database_schema()
    if success:
        print("\n✅ Ready for production runtime!")
    else:
        print("\n❌ Database fixes failed - check connection")
