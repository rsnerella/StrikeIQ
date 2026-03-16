#!/usr/bin/env python3
"""
Test script for Chart Intelligence Engine
Verifies pattern detection and overlay object generation.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from app.chart_intelligence.engine import chart_intelligence_engine

def generate_test_candles(num_bars: int = 100):
    """Generate realistic test candle data"""
    import random
    import math
    
    candles = []
    base_price = 20000
    
    for i in range(num_bars):
        # Simulate price movement with trend and noise
        trend = i * 2  # Upward trend
        noise = random.uniform(-50, 50)
        cycle = math.sin(i * 0.1) * 30
        
        close = base_price + trend + noise + cycle
        high = close + random.uniform(10, 30)
        low = close - random.uniform(10, 30)
        open_price = close + random.uniform(-20, 20)
        volume = random.uniform(1000000, 5000000)
        
        candle = {
            'timestamp': 1640995200 + i * 60,  # Unix timestamps
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        }
        candles.append(candle)
    
    return candles

def generate_test_options_data():
    """Generate test options data"""
    return {
        'call_wall': 20200,
        'put_wall': 19800,
        'pcr_ratio': 1.2,
        'gex_flip_level': 20000,
        'net_gamma': 50000,
        'total_call_oi': 1000000,
        'total_put_oi': 1200000,
        'max_pain': 20050,
        'iv_atm': 0.22
    }

def test_chart_intelligence():
    """Test the Chart Intelligence Engine"""
    print("🧠 Testing Chart Intelligence Engine...")
    
    # Generate test data
    candles = generate_test_candles(150)
    options_data = generate_test_options_data()
    
    print(f"📊 Generated {len(candles)} test candles")
    print(f"📈 Test options data: PCR={options_data['pcr_ratio']}, Call Wall={options_data['call_wall']}")
    
    # Run analysis
    try:
        result = chart_intelligence_engine.analyze(candles, options_data)
        
        print("\n✅ Chart Intelligence Analysis Complete!")
        print(f"📊 Market Structure: {result.market_structure}")
        print(f"🎯 Primary Pattern: {result.pattern_detected}")
        print(f"🔍 Overall Confidence: {result.confidence:.2f}")
        print(f"⏱️ Processing Time: {result.processing_time_ms:.2f}ms")
        
        print(f"\n🎨 Generated {len(result.overlay_objects)} overlay objects:")
        for i, overlay in enumerate(result.overlay_objects[:10]):  # Show first 10
            print(f"  {i+1}. {overlay.type}: {overlay.label} (confidence: {overlay.confidence:.2f})")
        
        if len(result.overlay_objects) > 10:
            print(f"  ... and {len(result.overlay_objects) - 10} more")
        
        print(f"\n📋 Analysis Summary:")
        summary = result.analysis_summary
        if 'market_structure' in summary:
            ms = summary['market_structure']
            print(f"  Structure: {ms['type']} (confidence: {ms['confidence']:.2f})")
        
        if 'patterns' in summary:
            patterns = summary['patterns']
            print(f"  Patterns Found:")
            for pattern_type, count in patterns.items():
                if count > 0:
                    print(f"    - {pattern_type.replace('_', ' ').title()}: {count}")
        
        if result.options_context:
            print(f"\n📊 Options Context Available:")
            if 'gamma_regime' in result.options_context:
                gr = result.options_context['gamma_regime']
                print(f"  Gamma Regime: {gr['regime']} ({gr['bias']})")
            if 'significant_levels' in result.options_context:
                levels = result.options_context['significant_levels']
                print(f"  Significant Levels: {len(levels)}")
        
        # Performance check
        if result.processing_time_ms > 50:
            print(f"\n⚠️ Performance Warning: Processing took {result.processing_time_ms:.2f}ms (>50ms target)")
        else:
            print(f"\n✅ Performance Target Met: {result.processing_time_ms:.2f}ms (<50ms)")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Chart Intelligence Analysis Failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_edge_cases():
    """Test edge cases"""
    print("\n🧪 Testing Edge Cases...")
    
    # Test with insufficient data
    try:
        result = chart_intelligence_engine.analyze([], None)
        print(f"✅ Empty data handled: {result.market_structure}")
    except Exception as e:
        print(f"❌ Empty data failed: {e}")
    
    # Test with minimal data
    try:
        minimal_candles = generate_test_candles(5)
        result = chart_intelligence_engine.analyze(minimal_candles, None)
        print(f"✅ Minimal data handled: {result.market_structure}")
    except Exception as e:
        print(f"❌ Minimal data failed: {e}")
    
    # Test without options data
    try:
        candles = generate_test_candles(100)
        result = chart_intelligence_engine.analyze(candles, None)
        print(f"✅ No options data handled: {result.pattern_detected}")
    except Exception as e:
        print(f"❌ No options data failed: {e}")

if __name__ == "__main__":
    print("🚀 Starting Chart Intelligence Engine Tests")
    print("=" * 50)
    
    success = test_chart_intelligence()
    test_edge_cases()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 Chart Intelligence Engine Tests PASSED!")
    else:
        print("💥 Chart Intelligence Engine Tests FAILED!")
        sys.exit(1)
