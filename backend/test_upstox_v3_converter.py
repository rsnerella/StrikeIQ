#!/usr/bin/env python3
"""
Test script for Upstox V3 Raw Feed Converter
"""

import asyncio
import logging
from app.services.upstox_v3_raw_converter import convert_protobuf_to_upstox_v3_format, extract_market_data_from_upstox_v3

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_converter():
    """Test the converter with sample data"""
    
    # This would normally be real protobuf data from Upstox
    # For now, we'll test the structure
    
    print("🧪 Testing Upstox V3 Raw Feed Converter")
    print("=" * 50)
    
    # Test 1: Empty data
    print("Test 1: Empty data")
    try:
        result = convert_protobuf_to_upstox_v3_format(b"")
        print(f"✅ Empty data handled: {result}")
    except Exception as e:
        print(f"❌ Empty data failed: {e}")
    
    # Test 2: Invalid data  
    print("\nTest 2: Invalid data")
    try:
        result = convert_protobuf_to_upstox_v3_format(b"invalid_protobuf")
        print(f"✅ Invalid data handled: {result}")
    except Exception as e:
        print(f"❌ Invalid data failed: {e}")
    
    print("\n🎯 Converter structure test complete")
    print("Note: Full test requires real Upstox protobuf data")

if __name__ == "__main__":
    test_converter()
