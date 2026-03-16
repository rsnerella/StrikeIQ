import logging
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.analytics.analytics_engine import AnalyticsEngine

def test_gex_calculation():
    engine = AnalyticsEngine()
    
    # Mock snapshot
    # NIFTY spot 24000
    # multiplier = 75
    # CE at 24000: gamma 0.001, oi 10000 -> GEX = 0.001 * 10000 * 75 = 750
    # PE at 24000: gamma 0.002, oi 5000 -> GEX = 0.002 * 5000 * 75 = 750
    # Net GEX should be 0 (flip)
    
    snapshot = {
        "symbol": "NIFTY",
        "spot": 24000,
        "calls": {
            "23900": {"gamma": 0.002, "oi": 10000},
            "24000": {"gamma": 0.001, "oi": 10000},
            "24100": {"gamma": 0.0005, "oi": 10000}
        },
        "puts": {
            "23900": {"gamma": 0.0005, "oi": 10000},
            "24000": {"gamma": 0.001, "oi": 10000},
            "24100": {"gamma": 0.002, "oi": 10000}
        }
    }
    
    result = engine.analyze(snapshot)
    print(f"Result: {result}")
    
    # Verification
    # Call GEX = (0.002+0.001+0.0005) * 10000 * 75 = 2625000
    # Put GEX = (0.0005+0.001+0.002) * 10000 * 75 = 2625000
    # Net GEX = 0
    # Flip Level should be 24000
    
    assert result['net_gex'] == 0
    assert result['gex_flip'] == 24000
    assert result['regime'] == "SHORT_GAMMA" # Since 0 is not > 0
    print("TEST PASSED: GEX 0 and Flip 24000 correctly identified")

    # Positive Gamma Test
    snapshot_bullish = {
        "symbol": "NIFTY",
        "spot": 24000,
        "calls": {
            "24000": {"gamma": 0.01, "oi": 10000} # Strong Call Gamma
        },
        "puts": {
            "24000": {"gamma": 0.001, "oi": 10000}
        }
    }
    result_bullish = engine.analyze(snapshot_bullish)
    print(f"Bullish Result: {result_bullish}")
    assert result_bullish['net_gex'] > 0
    assert result_bullish['regime'] == "POSITIVE_GAMMA"
    print("TEST PASSED: Positive Gamma detected")

if __name__ == "__main__":
    try:
        test_gex_calculation()
    except Exception as e:
        print(f"TEST FAILED: {e}")
        sys.exit(1)
