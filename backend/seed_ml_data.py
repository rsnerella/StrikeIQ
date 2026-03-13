import asyncio
import os
import sys
import random
from datetime import datetime, timedelta

# Add backend to path
sys.path.append(os.getcwd())

from ai.ai_db import ai_db

async def seed_ml_data():
    try:
        print("Seeding synthetic ML data...")
        
        symbols = ["NIFTY", "BANKNIFTY"]
        signals = ["BUY", "SELL"]
        waves = ["W1", "W2", "W3", "W4", "W5", "ABC"]
        trends = ["UP", "DOWN", "SIDEWAYS"]
        results = ["WIN", "LOSS"]
        
        for i in range(25):
            symbol = random.choice(symbols)
            signal = random.choice(signals)
            spot_price = random.uniform(22000, 23000)
            confidence = random.uniform(0.5, 0.9)
            
            metadata = {
                "pcr": random.uniform(0.6, 1.4),
                "gamma": random.uniform(-1000000, 1000000),
                "oi_velocity": random.uniform(-5000, 5000),
                "wave": random.choice(waves),
                "trend": random.choice(trends)
            }
            
            # Insert signal log
            log_query = """
                INSERT INTO ai_signal_logs (symbol, signal, confidence, spot_price, metadata, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            """
            ts = datetime.now() - timedelta(minutes=random.randint(60, 1440))
            import json
            params = (symbol, signal, confidence, spot_price, json.dumps(metadata), ts)
            
            res = await ai_db.fetch_one(log_query, params)
            signal_id = res[0]
            
            # Insert outcome
            result = random.choice(results)
            outcome_query = """
                INSERT INTO signal_outcomes (signal_id, result, outcome_type, outcome_value, timestamp)
                VALUES (%s, %s, %s, %s, %s)
            """
            outcome_params = (signal_id, result, "15m", random.uniform(-100, 100), ts + timedelta(minutes=15))
            await ai_db.execute_query(outcome_query, outcome_params)
            
        print("Successfully seeded 25 records.")
            
    except Exception as e:
        print(f"Error seeding data: {e}")

if __name__ == "__main__":
    asyncio.run(seed_ml_data())
