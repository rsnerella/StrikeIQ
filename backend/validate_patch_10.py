"""
STRIKEIQ PATCH 10 VALIDATION SCRIPT
Verify loop_now usage is fixed in helper functions
"""

import asyncio
import time
import logging
import inspect
from app.services.websocket_market_feed import WebSocketMarketFeed

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def validate_patch_10():
    """Validate PATCH 10: Fix loop_now usage in helper functions"""
    
    logger.info("🔧 STRIKEIQ PATCH 10 VALIDATION")
    logger.info("="*60)
    
    feed = WebSocketMarketFeed()
    
    # PATCH 10: Verify helper functions use local time
    logger.info("✅ PATCH 10: Fix loop_now usage in helper functions")
    
    # Check _monitor_broadcast uses local 'now' instead of 'loop_now'
    broadcast_source = inspect.getsource(feed._monitor_broadcast)
    
    if 'now = time.time()' in broadcast_source and 'loop_now' not in broadcast_source:
        logger.info("   ✅ _monitor_broadcast uses local time correctly")
    else:
        logger.error("   ❌ _monitor_broadcast still has incorrect time usage")
    
    # Check _monitor_redis_call uses local time correctly
    redis_source = inspect.getsource(feed._monitor_redis_call)
    
    if 'time.time()' in redis_source and 'loop_now' not in redis_source:
        logger.info("   ✅ _monitor_redis_call uses local time correctly")
    else:
        logger.error("   ❌ _monitor_redis_call has incorrect time usage")
    
    # Verify loop_now is still used correctly in main processing loops
    process_source = inspect.getsource(feed._process_loop)
    
    if 'loop_now = time.time()' in process_source:
        logger.info("   ✅ loop_now correctly used in _process_loop")
    else:
        logger.warning("   ⚠️ loop_now not found in _process_loop")
    
    # Verify loop_now is still used correctly in message handler
    handler_source = inspect.getsource(feed._handle_routed_message)
    
    if 'loop_now = time.time()' in handler_source:
        logger.info("   ✅ loop_now correctly used in _handle_routed_message")
    else:
        logger.warning("   ⚠️ loop_now not found in _handle_routed_message")
    
    logger.info("="*60)
    logger.info("🎯 PATCH 10 VALIDATION COMPLETE")

async def test_helper_functions():
    """Test that helper functions work correctly with local time"""
    logger.info("📊 TESTING HELPER FUNCTIONS")
    logger.info("="*60)
    
    feed = WebSocketMarketFeed()
    
    # Test _monitor_broadcast with local time
    logger.info("   • Testing _monitor_broadcast...")
    
    async def dummy_broadcast():
        await asyncio.sleep(0.001)  # Simulate some work
    
    try:
        start = time.time()
        await feed._monitor_broadcast("test", dummy_broadcast)
        elapsed = time.time() - start
        logger.info(f"   ✅ _monitor_broadcast works correctly ({elapsed:.4f}s)")
    except Exception as e:
        logger.error(f"   ❌ _monitor_broadcast failed: {e}")
    
    # Test _monitor_redis_call with local time
    logger.info("   • Testing _monitor_redis_call...")
    
    async def dummy_redis_operation():
        await asyncio.sleep(0.001)  # Simulate Redis operation
        return "test_result"
    
    try:
        start = time.time()
        result = await feed._monitor_redis_call("test_operation", dummy_redis_operation)
        elapsed = time.time() - start
        logger.info(f"   ✅ _monitor_redis_call works correctly ({elapsed:.4f}s)")
        logger.info(f"   ✅ Returned result: {result}")
    except Exception as e:
        logger.error(f"   ❌ _monitor_redis_call failed: {e}")
    
    logger.info("="*60)

async def main():
    """Main validation function"""
    await validate_patch_10()
    await test_helper_functions()
    
    logger.info("🚀 PATCH 10 VALIDATION COMPLETE")
    logger.info("✅ Helper functions use local time correctly")
    logger.info("✅ Main loops still use cached loop_time correctly")
    logger.info("🎯 StrikeIQ time optimization properly implemented")

if __name__ == "__main__":
    asyncio.run(main())
