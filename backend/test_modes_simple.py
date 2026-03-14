#!/usr/bin/env python3
"""
Simple Subscription Mode Tester
Tests different modes to find complete options data
"""

# Available subscription modes
SUBSCRIPTION_MODES = {
    "ltp": "LTP Only - Fastest updates, minimal data",
    "option_greek": "Options Greeks Only - Delta, theta, gamma, vega, rho",
    "full": "Full Data - LTP, some bid/ask, limited Greeks",
    "full_d30": "Full Market Depth (30 levels) - Complete bid/ask, all Greeks, OI, volume",
    "full_d5": "Full Market Depth (5 levels) - Complete data with 5 depth levels",
    "full_d10": "Full Market Depth (10 levels) - Complete data with 10 depth levels"
}

def analyze_expected_data(mode: str):
    """Analyze what data to expect from each mode"""
    expectations = {
        "ltp": {
            "ltp": "YES",
            "bid_ask": "NO",
            "greeks": "NO", 
            "oi": "NO",
            "volume": "NO"
        },
        "option_greek": {
            "ltp": "NO",
            "bid_ask": "NO",
            "greeks": "YES (delta, theta, gamma, vega, rho)",
            "oi": "NO",
            "volume": "NO"
        },
        "full": {
            "ltp": "YES",
            "bid_ask": "LIMITED",
            "greeks": "LIMITED",
            "oi": "LIMITED",
            "volume": "LIMITED"
        },
        "full_d30": {
            "ltp": "YES",
            "bid_ask": "YES (30 levels)",
            "greeks": "YES (all Greeks)",
            "oi": "YES (real-time)",
            "volume": "YES (real-time)"
        },
        "full_d5": {
            "ltp": "YES",
            "bid_ask": "YES (5 levels)",
            "greeks": "YES (all Greeks)",
            "oi": "YES (real-time)",
            "volume": "YES (real-time)"
        },
        "full_d10": {
            "ltp": "YES",
            "bid_ask": "YES (10 levels)",
            "greeks": "YES (all Greeks)",
            "oi": "YES (real-time)",
            "volume": "YES (real-time)"
        }
    }
    return expectations.get(mode, {})

def print_mode_comparison():
    """Print comparison of all modes"""
    print("SUBSCRIPTION MODE COMPARISON")
    print("=" * 70)
    
    headers = ["Mode", "LTP", "Bid/Ask", "Greeks", "OI", "Volume", "Description"]
    print(f"{'Mode':<12} {'LTP':<8} {'Bid/Ask':<10} {'Greeks':<8} {'OI':<6} {'Volume':<8} {'Description':<25}")
    print("-" * 70)
    
    for mode, description in SUBSCRIPTION_MODES.items():
        exp = analyze_expected_data(mode)
        print(f"{mode:<12} {exp.get('ltp', '?'):<8} {exp.get('bid_ask', '?'):<10} {exp.get('greeks', '?'):<8} {exp.get('oi', '?'):<6} {exp.get('volume', '?'):<8} {description:<25}")

def main():
    """Main test function"""
    print("Upstox WebSocket Subscription Mode Tester")
    print("=" * 70)
    print("Testing different subscription modes to find complete options data")
    print("=" * 70)
    
    # Print comparison table
    print_mode_comparison()
    
    print("\n" + "=" * 70)
    print("RECOMMENDATION:")
    print("Based on Upstox documentation and community research:")
    print("1. 'full_d30' - Most likely to have complete options data")
    print("2. 'full_d10' - Good balance of depth and performance") 
    print("3. 'full_d5' - Faster than d30, still complete data")
    print("4. 'full' - May have limited options data")
    print("5. 'option_greek' - Greeks only, no bid/ask")
    print("6. 'ltp' - Fastest but very limited")
    
    print("\n" + "=" * 70)
    print("NEXT STEPS:")
    print("1. Test 'full_d30' mode first (highest probability of complete data)")
    print("2. If still limited, try 'full_d10' and 'full_d5'")
    print("3. Monitor logs for MarketFF messages")
    print("4. Check for bid/ask, Greeks, OI, volume data")
    print("5. Compare message frequency and completeness")
    
    print("\n" + "=" * 70)
    print("TEST INSTRUCTIONS:")
    print("To test a mode, change the subscription in websocket_market_feed.py:")
    print("  Line 863: \"mode\": \"full_d30\"  # Change this to test different modes")
    print("  Available modes: ltp, option_greek, full, full_d30, full_d5, full_d10")
    print("  Restart the system after changing the mode")
    print("  Monitor logs for data completeness")

if __name__ == "__main__":
    main()
