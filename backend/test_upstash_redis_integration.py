#!/usr/bin/env python3
"""
Upstash Redis Integration Test Script
Tests the unified Redis client with both local and Upstash Redis
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add the backend directory to the path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.core.config import settings
from app.core.unified_redis_client import unified_redis_client
from app.core.redis_client import test_redis_connection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class RedisIntegrationTest:
    """Test suite for Redis integration"""
    
    def __init__(self):
        self.test_results = []
        
    def log_test(self, test_name: str, passed: bool, message: str = ""):
        """Log test result"""
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"{status} {test_name}: {message}")
        self.test_results.append({
            "test": test_name,
            "passed": passed,
            "message": message
        })
        
    async def test_configuration(self):
        """Test Redis configuration"""
        logger.info("🔧 Testing Redis configuration...")
        
        # Test basic configuration
        self.log_test(
            "Basic config loaded",
            hasattr(settings, 'REDIS_PROVIDER'),
            f"Provider: {settings.REDIS_PROVIDER}"
        )
        
        # Test Upstash configuration
        self.log_test(
            "Upstash config present",
            bool(settings.UPSTASH_REDIS_URL and settings.UPSTASH_REDIS_TOKEN),
            f"URL configured: {bool(settings.UPSTASH_REDIS_URL)}, Token configured: {bool(settings.UPSTASH_REDIS_TOKEN)}"
        )
        
        # Test provider detection
        self.log_test(
            "Provider detection works",
            hasattr(settings, 'is_upstash_enabled'),
            f"Upstash enabled: {settings.is_upstash_enabled}"
        )
        
        # Test effective URL
        self.log_test(
            "Effective URL resolution",
            bool(settings.effective_redis_url),
            f"Effective URL: {settings.effective_redis_url}"
        )
        
    async def test_unified_client_initialization(self):
        """Test unified Redis client initialization"""
        logger.info("🚀 Testing unified client initialization...")
        
        try:
            await unified_redis_client.initialize()
            self.log_test("Client initialization", True, "Unified client initialized successfully")
            
            # Get provider info
            provider_info = await unified_redis_client.get_provider_info()
            self.log_test(
                "Provider info available",
                bool(provider_info),
                f"Active provider: {provider_info.get('active_provider')}"
            )
            
            # Test connection
            is_connected = await unified_redis_client.ping()
            self.log_test(
                "Redis connection",
                is_connected,
                f"Connected using: {provider_info.get('active_provider')}"
            )
            
        except Exception as e:
            self.log_test("Client initialization", False, str(e))
            
    async def test_basic_operations(self):
        """Test basic Redis operations"""
        logger.info("📝 Testing basic Redis operations...")
        
        test_key = "test_upstash_integration"
        test_value = "test_value_12345"
        
        try:
            # Test SET operation
            set_result = await unified_redis_client.set(test_key, test_value, ex=60)
            self.log_test("SET operation", set_result, f"Set result: {set_result}")
            
            # Test GET operation
            get_result = await unified_redis_client.get(test_key)
            self.log_test(
                "GET operation",
                get_result == test_value,
                f"Expected: {test_value}, Got: {get_result}"
            )
            
            # Test EXISTS operation
            exists_result = await unified_redis_client.exists(test_key)
            self.log_test("EXISTS operation", exists_result, f"Key exists: {exists_result}")
            
            # Test JSON operations
            test_data = {"test": "data", "number": 42}
            json_set_result = await unified_redis_client.set_json(test_key + "_json", test_data, ex=60)
            self.log_test("SET JSON operation", json_set_result, f"JSON set result: {json_set_result}")
            
            json_get_result = await unified_redis_client.get_json(test_key + "_json")
            self.log_test(
                "GET JSON operation",
                json_get_result == test_data,
                f"JSON data match: {json_get_result == test_data}"
            )
            
            # Test DELETE operation
            delete_result = await unified_redis_client.delete(test_key)
            self.log_test("DELETE operation", delete_result, f"Delete result: {delete_result}")
            
            delete_json_result = await unified_redis_client.delete(test_key + "_json")
            self.log_test("DELETE JSON operation", delete_json_result, f"Delete JSON result: {delete_json_result}")
            
        except Exception as e:
            self.log_test("Basic operations", False, str(e))
            
    async def test_hash_operations(self):
        """Test Redis hash operations"""
        logger.info("🗂️ Testing Redis hash operations...")
        
        test_hash_key = "test_hash"
        test_field = "test_field"
        test_field_value = "test_field_value"
        
        try:
            # Test HSET operation
            hset_result = await unified_redis_client.hset(test_hash_key, test_field, test_field_value)
            self.log_test("HSET operation", hset_result, f"HSET result: {hset_result}")
            
            # Test HGET operation
            hget_result = await unified_redis_client.hget(test_hash_key, test_field)
            self.log_test(
                "HGET operation",
                hget_result == test_field_value,
                f"Expected: {test_field_value}, Got: {hget_result}"
            )
            
            # Test HGETALL operation
            hgetall_result = await unified_redis_client.hgetall(test_hash_key)
            self.log_test(
                "HGETALL operation",
                test_field in hgetall_result and hgetall_result[test_field] == test_field_value,
                f"HGETALL result: {hgetall_result}"
            )
            
            # Cleanup
            await unified_redis_client.delete(test_hash_key)
            
        except Exception as e:
            self.log_test("Hash operations", False, str(e))
            
    async def test_list_operations(self):
        """Test Redis list operations"""
        logger.info("📋 Testing Redis list operations...")
        
        test_list_key = "test_list"
        test_values = ["item1", "item2", "item3"]
        
        try:
            # Test LPUSH operation
            lpush_result = await unified_redis_client.lpush(test_list_key, *test_values)
            self.log_test("LPUSH operation", lpush_result > 0, f"LPUSH result: {lpush_result}")
            
            # Test LRANGE operation
            lrange_result = await unified_redis_client.lrange(test_list_key, 0, -1)
            self.log_test(
                "LRANGE operation",
                len(lrange_result) >= len(test_values),
                f"LRANGE result: {lrange_result}"
            )
            
            # Test RPOP operation
            rpop_result = await unified_redis_client.rpop(test_list_key)
            self.log_test("RPOP operation", rpop_result is not None, f"RPOP result: {rpop_result}")
            
            # Cleanup
            await unified_redis_client.delete(test_list_key)
            
        except Exception as e:
            self.log_test("List operations", False, str(e))
            
    async def test_fallback_mechanism(self):
        """Test fallback mechanism between providers"""
        logger.info("🔄 Testing fallback mechanism...")
        
        provider_info = await unified_redis_client.get_provider_info()
        active_provider = provider_info.get('active_provider')
        
        self.log_test(
            "Active provider detected",
            active_provider is not None,
            f"Active provider: {active_provider}"
        )
        
        self.log_test(
            "Local Redis available",
            provider_info.get('local_available', False),
            "Local Redis client available"
        )
        
        self.log_test(
            "Upstash Redis available",
            provider_info.get('upstash_available', False),
            "Upstash Redis client available"
        )
        
    async def test_legacy_compatibility(self):
        """Test legacy compatibility with existing code"""
        logger.info("🔙 Testing legacy compatibility...")
        
        try:
            # Test legacy import
            from app.core.redis_client import redis_client as legacy_client
            self.log_test("Legacy import", True, "Legacy import successful")
            
            # Test legacy operations
            test_key = "legacy_test"
            await legacy_client.set(test_key, "legacy_value", ex=60)
            legacy_result = await legacy_client.get(test_key)
            self.log_test(
                "Legacy operations",
                legacy_result == "legacy_value",
                f"Legacy result: {legacy_result}"
            )
            
            # Cleanup
            await legacy_client.delete(test_key)
            
        except Exception as e:
            self.log_test("Legacy compatibility", False, str(e))
            
    async def run_all_tests(self):
        """Run all tests"""
        logger.info("🧪 Starting Upstash Redis Integration Tests")
        logger.info("=" * 60)
        
        # Run all test suites
        await self.test_configuration()
        await self.test_unified_client_initialization()
        await self.test_basic_operations()
        await self.test_hash_operations()
        await self.test_list_operations()
        await self.test_fallback_mechanism()
        await self.test_legacy_compatibility()
        
        # Print summary
        logger.info("=" * 60)
        logger.info("📊 Test Summary")
        
        passed = sum(1 for result in self.test_results if result["passed"])
        total = len(self.test_results)
        
        logger.info(f"Total tests: {total}")
        logger.info(f"Passed: {passed}")
        logger.info(f"Failed: {total - passed}")
        logger.info(f"Success rate: {(passed/total)*100:.1f}%")
        
        # Print failed tests
        failed_tests = [result for result in self.test_results if not result["passed"]]
        if failed_tests:
            logger.warning("❌ Failed Tests:")
            for test in failed_tests:
                logger.warning(f"  - {test['test']}: {test['message']}")
        
        # Get final provider info
        provider_info = await unified_redis_client.get_provider_info()
        logger.info(f"🔧 Final active provider: {provider_info.get('active_provider')}")
        
        return passed == total

async def main():
    """Main test function"""
    test = RedisIntegrationTest()
    
    try:
        success = await test.run_all_tests()
        
        if success:
            logger.info("🎉 All tests passed! Upstash Redis integration is working correctly.")
            return 0
        else:
            logger.error("❌ Some tests failed. Please check the configuration.")
            return 1
            
    except Exception as e:
        logger.error(f"💥 Test suite failed: {e}")
        return 1
        
    finally:
        # Cleanup
        try:
            await unified_redis_client.close()
        except Exception:
            pass

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
