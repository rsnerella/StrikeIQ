import asyncio
import websockets
import json
import signal
import sys

async def monitor_gex():
    uri = "ws://localhost:8000/ws"
    print(f"Connecting to {uri}...")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected. Subscribing to NIFTY...")
            
            # Subscribe to NIFTY
            await websocket.send(json.dumps({
                "type": "subscribe",
                "symbol": "NIFTY"
            }))
            
            non_zero_received = False
            count = 0
            
            while count < 20:
                message = await websocket.recv()
                data = json.loads(message)
                
                msg_type = data.get("type")
                if msg_type in ["market_update", "chart_analysis"]:
                    payload = data.get("data", {})
                    
                    if msg_type == "market_update":
                        net_gex = payload.get("net_gex")
                        gex_flip = payload.get("gex_flip")
                        regime = payload.get("regime")
                        print(f"[MARKET_UPDATE] GEX: {net_gex}, Flip: {gex_flip}, Regime: {regime}")
                    else:
                        ga = payload.get("gamma_analysis", {})
                        net_gex = ga.get("net_gex")
                        gex_flip = ga.get("gex_flip")
                        dist = ga.get("dist_to_flip")
                        print(f"[CHART_ANALYSIS] GEX: {net_gex}, Flip: {gex_flip}, Dist: {dist}")
                    
                    if net_gex and float(net_gex) != 0:
                        print("SUCCESS: Non-zero GEX detected!")
                        non_zero_received = True
                        break
                
                count += 1
            
            if not non_zero_received:
                print("FAILURE: No non-zero GEX received in 20 messages.")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(monitor_gex())
