import asyncio
import os
import sys

# Add backend to path
sys.path.append(os.getcwd())

from ai.ai_db import ai_db

async def check_ml_data():
    try:
        print("Checking ML dataset availability...")
        
        # Count signal logs
        signal_count = await ai_db.fetch_one("SELECT COUNT(*) FROM ai_signal_logs")
        print(f"Total entries in ai_signal_logs: {signal_count[0]}")
        
        # Count outcomes
        outcome_count = await ai_db.fetch_one("SELECT COUNT(*) FROM signal_outcomes")
        print(f"Total entries in signal_outcomes: {outcome_count[0]}")
        
        # Count labeled data
        labeled_query = """
            SELECT COUNT(*) 
            FROM ai_signal_logs l
            JOIN signal_outcomes o ON l.id = o.signal_id
            WHERE o.result IS NOT NULL
        """
        labeled_count = await ai_db.fetch_one(labeled_query)
        print(f"Total labeled dataset size (signals with outcomes): {labeled_count[0]}")
        
        # Label distribution
        distribution_query = """
            SELECT o.result, COUNT(*) 
            FROM signal_outcomes o
            GROUP BY o.result
        """
        distribution = await ai_db.fetch_query(distribution_query)
        print("\nLabel Distribution:")
        for row in distribution:
            print(f"- {row[0]}: {row[1]}")
            
    except Exception as e:
        print(f"Error checking ML data: {e}")

if __name__ == "__main__":
    asyncio.run(check_ml_data())
