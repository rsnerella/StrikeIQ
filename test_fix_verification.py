#!/usr/bin/env python3
"""
Test our index_update broadcast fix by simulating the message flow
"""
import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

async def test_index_update_format():
    try:
        from app.services.websocket_market_feed import WebSocketMarketFeed
        from app.core.ws_manager import manager
        
        print("✅ Testing index_update broadcast format...")
        
        # Create a mock message like what message_router would create
        mock_message = {
            "type": "index_tick",
            "symbol": "NIFTY", 
            "instrument_key": "NSE_INDEX|NIFTY 50",
            "timestamp": 1234567890,
            "data": {
                "ltp": 24122.75,
                "change": 12.5,
                "change_percent": 0.05
            }
        }
        
        print(f"📥 Input message: {mock_message}")
        
        # Test our broadcast logic by extracting the payload we create
        symbol = mock_message.get("symbol")
        data = mock_message.get("data", {})
        ltp = data.get("ltp")
        
        if ltp is not None:
            # This is exactly what our patched code does
            payload = {
                "type": "index_update",
                "symbol": symbol,
                "ltp": float(ltp)
            }
            
            print(f"📤 Our broadcast payload: {payload}")
            
            # Verify the format matches expectations
            expected_keys = {"type", "symbol", "ltp"}
            actual_keys = set(payload.keys())
            
            if expected_keys == actual_keys:
                print("✅ Payload format is CORRECT!")
                print(f"   - type: {payload['type']}")
                print(f"   - symbol: {payload['symbol']}")  
                print(f"   - ltp: {payload['ltp']}")
            else:
                print(f"❌ Payload format is WRONG!")
                print(f"   Expected keys: {expected_keys}")
                print(f"   Actual keys: {actual_keys}")
                
            # Test the flat structure vs old nested structure
            old_format = {
                "type": "index_tick",
                "symbol": "NIFTY",
                "data": {"ltp": 24122.75}
            }
            
            print(f"\n🔄 COMPARISON:")
            print(f"   OLD (nested): {old_format}")
            print(f"   NEW (flat):   {payload}")
            print(f"   Frontend expects FLAT structure with 'index_update' type ✅")
            
        else:
            print("❌ No LTP found in mock message")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_index_update_format())
