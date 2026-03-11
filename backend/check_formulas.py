
import asyncio
from ai.ai_db import ai_db
import json

async def main():
    formulas = await ai_db.fetch_query("SELECT id, formula_name, is_active FROM formula_master")
    print(f"Formulas: {formulas}")
    
    # Check if we have at least one active formula. If not, create one.
    active = [f for f in formulas if f[2]]
    if not active:
        print("No active formulas found. Creating a test formula...")
        conditions = {
            "pcr_threshold": 1.2,
            "gamma_threshold": 1000000
        }
        await ai_db.execute_query("""
            INSERT INTO formula_master (formula_name, formula_type, conditions, confidence_threshold, is_active)
            VALUES ('TEST_BULLISH_REVERSAL', 'BULLISH', %s, 0.7, TRUE)
        """, (json.dumps(conditions),))
        print("Created TEST_BULLISH_REVERSAL")

if __name__ == "__main__":
    asyncio.run(main())
