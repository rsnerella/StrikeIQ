
import asyncio
import time
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.ai.ai_orchestrator import ai_orchestrator

async def test_performance():
    print("🚀 Starting AI Orchestrator Performance Test...")
    
    mock_snapshot = {
        "symbol": "NIFTY",
        "spot": 22450.50,
        "atm_strike": 22450,
        "strikes": [],
        "pcr": 1.05,
        "timestamp": time.time()
    }
    
    # Warm up
    await ai_orchestrator.run_cycle("NIFTY", mock_snapshot)
    
    runs = 10
    total_time = 0
    
    for i in range(runs):
        start = time.time()
        result = await ai_orchestrator.run_cycle("NIFTY", mock_snapshot)
        elapsed = (time.time() - start) * 1000
        total_time += elapsed
        print(f"Run {i+1}: {elapsed:.2f}ms (Status: {result.get('status')})")
    
    avg_time = total_time / runs
    print("-" * 30)
    print(f"Average Cycle Time: {avg_time:.2f}ms")
    
    if avg_time < 100:
        print("✅ PERFORMANCE CHECK PASSED (< 100ms)")
    else:
        print("❌ PERFORMANCE CHECK FAILED (> 100ms)")

if __name__ == "__main__":
    asyncio.run(test_performance())
