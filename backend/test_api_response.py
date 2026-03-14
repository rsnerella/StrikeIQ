#!/usr/bin/env python3
"""
Test script to analyze Upstox API response structure
"""

import asyncio
import httpx
import json
from app.services.token_manager import token_manager

async def test_api_response():
    """Test the actual API response structure"""
    
    try:
        # Get authentication token
        token = await token_manager.get_token()
        if not token:
            print("❌ No token available")
            return
        
        print(f"✅ Token obtained: {token[:20]}...")
        
        # Test with a known option instrument
        instrument_key = "NSE_FO|57690"
        
        async with httpx.AsyncClient(timeout=10.0) as session:
            url = f"https://api.upstox.com/v2/market-quote/quotes"
            params = {"instrument_key": instrument_key}
            headers = {
                "accept": "application/json",
                "Authorization": f"Bearer {token}"
            }
            
            print(f"📡 Making API call for {instrument_key}")
            response = await session.get(url, params=params, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ API Response Status: {data.get('status')}")
                print(f"📊 Full Response Structure:")
                print(json.dumps(data, indent=2))
                
                # Analyze the data structure
                if data.get("status") == "success" and data.get("data"):
                    quote_data = data["data"]
                    print(f"\n🔍 Available Fields in quote data:")
                    for key, value in quote_data.items():
                        print(f"  {key}: {value}")
                        
                    print(f"\n📈 Specific Market Data Fields:")
                    print(f"  bidPrice: {quote_data.get('bidPrice', 'NOT FOUND')}")
                    print(f"  askPrice: {quote_data.get('askPrice', 'NOT FOUND')}")
                    print(f"  bidQuantity: {quote_data.get('bidQuantity', 'NOT FOUND')}")
                    print(f"  askQuantity: {quote_data.get('askQuantity', 'NOT FOUND')}")
                    print(f"  openInterest: {quote_data.get('openInterest', 'NOT FOUND')}")
                    print(f"  totalTradedVolume: {quote_data.get('totalTradedVolume', 'NOT FOUND')}")
                    print(f"  impliedVolatility: {quote_data.get('impliedVolatility', 'NOT FOUND')}")
                    print(f"  delta: {quote_data.get('delta', 'NOT FOUND')}")
                    print(f"  theta: {quote_data.get('theta', 'NOT FOUND')}")
                    print(f"  gamma: {quote_data.get('gamma', 'NOT FAILED')}")
                    print(f"  vega: {quote_data.get('vega', 'NOT FOUND')}")
                    
            else:
                print(f"❌ API Error: {response.status_code}")
                print(f"Response: {response.text}")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_api_response())
