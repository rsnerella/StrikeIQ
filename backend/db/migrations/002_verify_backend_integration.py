#!/usr/bin/env python3
"""
StrikeIQ Backend Integration Verification
Tests that backend code can successfully connect to the updated database schema
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

async def test_ai_signal_engine():
    """Test AI Signal Engine database operations"""
    try:
        # Convert SQLAlchemy URL to asyncpg format
        db_url = settings.DATABASE_URL
        if db_url.startswith('postgresql+asyncpg://'):
            db_url = db_url.replace('postgresql+asyncpg://', 'postgresql://')
        elif db_url.startswith('postgresql://'):
            pass  # Already correct
        else:
            raise ValueError(f"Unsupported database URL format: {db_url}")
        
        conn = await asyncpg.connect(db_url)
        logger.info("✅ Connected to database for integration testing")
        
        # Test 1: AI Signal Engine - Market Snapshot Query
        logger.info("🧪 Testing AI Signal Engine queries...")
        
        # Create test market snapshot
        await conn.execute("""
            INSERT INTO market_snapshot (symbol, spot_price, pcr, total_call_oi, total_put_oi, atm_strike, timestamp)
            VALUES ('NIFTY', 22450.0, 1.2, 1500000, 1250000, 22450, NOW())
            ON CONFLICT DO NOTHING
        """)
        
        # Test market snapshot query (used by ai_signal_engine)
        result = await conn.fetchrow("""
            SELECT symbol, spot_price, pcr, total_call_oi, total_put_oi, atm_strike, timestamp
            FROM market_snapshot
            ORDER BY timestamp DESC
            LIMIT 1
        """)
        
        if result:
            logger.info(f"✅ Market snapshot query works: {result['symbol']} @ {result['spot_price']}")
        else:
            logger.error("❌ Market snapshot query failed")
            return False
        
        # Test 2: Formula Master Query (used by ai_signal_engine)
        result = await conn.fetch("""
            SELECT id, formula_name, formula_type, conditions, confidence_threshold, is_active
            FROM formula_master
            WHERE is_active = TRUE
            ORDER BY id
        """)
        
        if result:
            logger.info(f"✅ Formula master query works: {len(result)} active formulas")
            for formula in result:
                logger.info(f"  - {formula['formula_name']}: {formula['conditions']}")
        else:
            logger.error("❌ Formula master query failed")
            return False
        
        # Test 3: Prediction Log Insert (used by ai_signal_engine)
        await conn.execute("""
            INSERT INTO prediction_log (
                prediction_type, symbol, timestamp, prediction_data, 
                confidence, status, formula_id, signal, nifty_spot, 
                prediction_time, outcome_checked
            ) VALUES (
                'formula_prediction', 'NIFTY', NOW(), 
                '{"signal": "BUY", "confidence": 0.8}', 
                0.8, 'ACTIVE', 1, 'BUY', 22450.0, 
                NOW(), FALSE
            )
        """)
        
        result = await conn.fetchrow("""
            SELECT id, signal, confidence, outcome_checked
            FROM prediction_log
            WHERE symbol = 'NIFTY'
            ORDER BY timestamp DESC
            LIMIT 1
        """)
        
        if result:
            logger.info(f"✅ Prediction log insert works: {result['signal']} @ {result['confidence']}")
        else:
            logger.error("❌ Prediction log insert failed")
            return False
        
        # Test 4: AI Predictions Insert (used by probability_engine)
        await conn.execute("""
            INSERT INTO ai_predictions (
                symbol, timestamp, probability, signal, target, stop, 
                prediction_type, confidence
            ) VALUES (
                'NIFTY', NOW(), 0.75, 'BUY', 22600.0, 22300.0, 
                'ml_prediction', 0.75
            )
        """)
        
        result = await conn.fetchrow("""
            SELECT id, signal, probability, target, stop
            FROM ai_predictions
            WHERE symbol = 'NIFTY'
            ORDER BY timestamp DESC
            LIMIT 1
        """)
        
        if result:
            logger.info(f"✅ AI predictions insert works: {result['signal']} @ {result['probability']}")
        else:
            logger.error("❌ AI predictions insert failed")
            return False
        
        # Test 5: AI Signal Log Insert (used by chart_signal_engine)
        await conn.execute("""
            INSERT INTO ai_signal_logs (
                symbol, timestamp, signal, confidence, spot_price, metadata
            ) VALUES (
                'NIFTY', NOW(), 'BUY', 0.85, 22450.0, 
                '{"source": "chart_signal_engine", "wave": "impulse"}'
            )
        """)
        
        result = await conn.fetchrow("""
            SELECT id, signal, confidence, metadata
            FROM ai_signal_logs
            WHERE symbol = 'NIFTY'
            ORDER BY timestamp DESC
            LIMIT 1
        """)
        
        if result:
            logger.info(f"✅ AI signal logs insert works: {result['signal']} @ {result['confidence']}")
        else:
            logger.error("❌ AI signal logs insert failed")
            return False
        
        # Test 6: Signal Outcomes Insert (used by training_dataset_builder)
        await conn.execute("""
            INSERT INTO signal_outcomes (
                signal_id, timestamp, outcome_type, outcome_value, accuracy, result
            ) VALUES (
                1, NOW(), 'price_movement', 150.0, 0.85, 'CORRECT'
            )
        """)
        
        result = await conn.fetchrow("""
            SELECT id, outcome_type, outcome_value, accuracy, result
            FROM signal_outcomes
            ORDER BY timestamp DESC
            LIMIT 1
        """)
        
        if result:
            logger.info(f"✅ Signal outcomes insert works: {result['result']} @ {result['accuracy']}")
        else:
            logger.error("❌ Signal outcomes insert failed")
            return False
        
        await conn.close()
        logger.info("🎉 All backend integration tests passed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Backend integration test failed: {e}")
        return False

async def test_foreign_keys():
    """Test foreign key constraints"""
    try:
        # Convert SQLAlchemy URL to asyncpg format
        db_url = settings.DATABASE_URL
        if db_url.startswith('postgresql+asyncpg://'):
            db_url = db_url.replace('postgresql+asyncpg://', 'postgresql://')
        elif db_url.startswith('postgresql://'):
            pass  # Already correct
        else:
            raise ValueError(f"Unsupported database URL format: {db_url}")
        
        conn = await asyncpg.connect(db_url)
        logger.info("✅ Connected to database for foreign key testing")
        
        # Test foreign key constraints
        logger.info("🧪 Testing foreign key constraints...")
        
        # Test 1: signal_outcomes -> ai_signal_logs foreign key
        try:
            await conn.execute("""
                INSERT INTO signal_outcomes (signal_id, timestamp, outcome_type)
                VALUES (99999, NOW(), 'test')
            """)
            logger.error("❌ Foreign key constraint not working for signal_outcomes")
            return False
        except Exception as e:
            if "foreign key" in str(e).lower():
                logger.info("✅ Foreign key constraint works for signal_outcomes")
            else:
                logger.error(f"❌ Unexpected error: {e}")
                return False
        
        # Test 2: paper_trade_log -> prediction_log foreign key
        try:
            await conn.execute("""
                INSERT INTO paper_trade_log (symbol, prediction_id, timestamp)
                VALUES ('NIFTY', 99999, NOW())
            """)
            logger.error("❌ Foreign key constraint not working for paper_trade_log")
            return False
        except Exception as e:
            if "foreign key" in str(e).lower():
                logger.info("✅ Foreign key constraint works for paper_trade_log")
            else:
                logger.error(f"❌ Unexpected error: {e}")
                return False
        
        await conn.close()
        logger.info("🎉 All foreign key tests passed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Foreign key test failed: {e}")
        return False

async def main():
    """Run all integration tests"""
    logger.info("🚀 Starting StrikeIQ Backend Integration Verification...")
    
    # Test backend operations
    backend_test = await test_ai_signal_engine()
    if not backend_test:
        logger.error("❌ Backend integration tests failed")
        sys.exit(1)
    
    # Test foreign keys
    fk_test = await test_foreign_keys()
    if not fk_test:
        logger.error("❌ Foreign key tests failed")
        sys.exit(1)
    
    logger.info("🎉 All integration tests completed successfully!")
    logger.info("✅ Backend is now compatible with updated database schema!")

if __name__ == "__main__":
    asyncio.run(main())
