#!/usr/bin/env python3
"""
Dynamic Subscription Mode Tester
Dynamically changes subscription modes to test complete options data extraction
"""

import asyncio
import json
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Available subscription modes based on Upstox documentation
SUBSCRIPTION_MODES = {
    "ltp": "LTP Only - Fastest updates, minimal data",
    "option_greek": "Options Greeks Only - Delta, theta, gamma, vega, rho",
    "full": "Full Data - LTP, some bid/ask, limited Greeks",
    "full_d30": "Full Market Depth - Complete bid/ask, all Greeks, OI, volume",
    "full_d5": "Full Market Depth (5 levels) - Complete data with 5 depth levels",
    "full_d10": "Full Market Depth (10 levels) - Complete data with 10 depth levels"
}

def create_subscription_payload(mode: str, instrument_keys: list):
    """Create subscription payload for testing"""
    return {
        "guid": "strikeiq-test",
        "method": "sub",
        "data": {
            "mode": mode,
            "instrumentKeys": instrument_keys[:5]  # Test with first 5 instruments
        }
    }

def analyze_expected_data(mode: str):
    """Analyze what data to expect from each mode"""
    expectations = {
        "ltp": {
            "ltp": "✅ Available",
            "bid_ask": "❌ Not available",
            "greeks": "❌ Not available", 
            "oi": "❌ Not available",
            "volume": "❌ Not available"
        },
        "option_greek": {
            "ltp": "❌ Not available",
            "bid_ask": "❌ Not available",
            "greeks": "✅ Available (delta, theta, gamma, vega, rho)",
            "oi": "❌ Not available",
            "volume": "❌ Not available"
        },
        "full": {
            "ltp": "✅ Available",
            "bid_ask": "🤔 Limited (may be available)",
            "greeks": "🤔 Limited (may be available)",
            "oi": "🤔 Limited (may be available)",
            "volume": "🤔 Limited (may be available)"
        },
        "full_d30": {
            "ltp": "✅ Available",
            "bid_ask": "✅ Available (30 levels)",
            "greeks": "✅ Available (all Greeks)",
            "oi": "✅ Available (real-time)",
            "volume": "✅ Available (real-time)"
        },
        "full_d5": {
            "ltp": "✅ Available",
            "bid_ask": "✅ Available (5 levels)",
            "greeks": "✅ Available (all Greeks)",
            "oi": "✅ Available (real-time)",
            "volume": "✅ Available (real-time)"
        },
        "full_d10": {
            "ltp": "✅ Available",
            "bid_ask": "✅ Available (10 levels)",
            "greeks": "✅ Available (all Greeks)",
            "oi": "✅ Available (real-time)",
            "volume": "✅ Available (real-time)"
        }
    }
    return expectations.get(mode, {})

def print_mode_comparison():
    """Print comparison of all modes"""
    print("📊 SUBSCRIPTION MODE COMPARISON")
    print("=" * 80)
    
    headers = ["Mode", "LTP", "Bid/Ask", "Greeks", "OI", "Volume", "Description"]
    print(f"{'Mode':<12} {'LTP':<8} {'Bid/Ask':<10} {'Greeks':<8} {'OI':<6} {'Volume':<8} {'Description':<25}")
    print("-" * 80)
    
    for mode, description in SUBSCRIPTION_MODES.items():
        exp = analyze_expected_data(mode)
        print(f"{mode:<12} {exp.get('ltp', '?'):<8} {exp.get('bid_ask', '?'):<10} {exp.get('greeks', '?'):<8} {exp.get('oi', '?'):<6} {exp.get('volume', '?'):<8} {description:<25}")

def create_test_script(mode: str):
    """Create a test script for a specific mode"""
    script = f"""
# Test Script for {mode} Mode
# Expected: {SUBSCRIPTION_MODES[mode]}

# Test instruments (sample options)
test_instruments = [
    "NSE_FO|57650",  # Deep OTM CE
    "NSE_FO|57724",  # ATM CE  
    "NSE_FO|57723",  # ATM PE
    "NSE_FO|57800",  # ITM CE
    "NSE_FO|57773"   # ITM PE
]

# Create subscription payload
payload = {{
    "guid": "strikeiq-test-{mode}",
    "method": "sub", 
    "data": {{
        "mode": "{mode}",
        "instrumentKeys": test_instruments
    }}
}}

# Expected data analysis
expected = {analyze_expected_data(mode)}

print("🧪 Testing {mode} Mode")
print("📊 Expected Data:")
for field, status in expected.items():
    print(f"  {{field}}: {{status}}")

# Monitor logs for:
# 1. MarketFF vs IndexFF messages
# 2. Bid/Ask data presence
# 3. Greeks data presence  
# 4. OI/Volume data presence
# 5. Message frequency and completeness

# Key indicators to watch for:
# - "MARKETFF DETECTED" for options
# - "BID/ASK: bid=X.XX, ask=Y.YY" 
# - "GREEKS: iv=X.XX, delta=Y.YY"
# - "OI: ZZZZZ, volume: VVVVV"
"""
    
    return script

def main():
    """Main test function"""
    print("🔬 Upstox WebSocket Subscription Mode Tester")
    print("=" * 80)
    print("Testing different subscription modes to find complete options data")
    print("=" * 80)
    
    # Print comparison table
    print_mode_comparison()
    
    print("\n" + "=" * 80)
    print("🎯 RECOMMENDATION:")
    print("Based on Upstox documentation and community research:")
    print("1. 'full_d30' - Most likely to have complete options data")
    print("2. 'full_d10' - Good balance of depth and performance") 
    print("3. 'full_d5' - Faster than d30, still complete data")
    print("4. 'full' - May have limited options data")
    print("5. 'option_greek' - Greeks only, no bid/ask")
    print("6. 'ltp' - Fastest but very limited")
    
    print("\n" + "=" * 80)
    print("🧪 NEXT STEPS:")
    print("1. Test 'full_d30' mode first (highest probability of complete data)")
    print("2. If still limited, try 'full_d10' and 'full_d5'")
    print("3. Monitor logs for MarketFF messages")
    print("4. Check for bid/ask, Greeks, OI, volume data")
    print("5. Compare message frequency and completeness")
    
    print("\n" + "=" * 80)
    print("📝 GENERATING TEST SCRIPTS...")
    
    # Generate test scripts for each mode
    for mode in ["full_d30", "full_d10", "full_d5", "full"]:
        script = create_test_script(mode)
        filename = f"test_{mode}_mode.py"
        
        with open(filename, 'w') as f:
            f.write(script)
        
        print(f"✅ Created: {filename}")
    
    print("\n🚀 READY TO TEST!")
    print("Run any test script to see expected behavior and monitoring points")

if __name__ == "__main__":
    main()
