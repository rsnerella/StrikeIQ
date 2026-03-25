#!/usr/bin/env python3
"""
Test Clean AI Logging
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ai.ai_logger import log, log_market_data, log_decision, log_fetching

def test_clean_logging():
    """Test the clean AI logging functionality"""
    
    print("=== TESTING CLEAN AI LOGGING ===\n")
    
    # Test 1: Basic logging
    log("Testing basic logging")
    
    # Test 2: Market data logging
    log_market_data(spot=22450, pcr=0.83, rsi=50, gamma="NEUTRAL")
    
    # Test 3: Decision logging
    log_decision(confidence=52, signal="NONE")
    
    # Test 4: Fetching logging
    log_fetching("market data")
    
    # Test 5: Logging with data dict
    log("Decision result", {"spot": 22450, "confidence": 52, "signal": "NONE"})
    
    print("\n=== EXPECTED OUTPUT FORMAT ===")
    print("[AI] Testing basic logging")
    print("[AI] Spot: 22450 | PCR: 0.83 | RSI: 50 | Gamma: NEUTRAL")
    print("[AI] Confidence: 52 | Signal: NONE")
    print("[AI] Fetching market data...")
    print("[AI] Decision result {'spot': 22450, 'confidence': 52, 'signal': 'NONE'}")
    
    print("\n✅ Clean logging test completed!")

if __name__ == "__main__":
    test_clean_logging()
