from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any
from app.services.market_data.market_dashboard_service import MarketDashboardService
from app.services.market_status_service import get_market_status
from app.models.database import get_db
from app.services.instrument_registry import get_instrument_registry
import logging
from datetime import datetime, timedelta
import httpx
import os
from app.services.token_manager import token_manager

router = APIRouter(tags=["market"])
logger = logging.getLogger(__name__)

def get_market_service():
    """Dependency injection for MarketDashboardService"""
    return MarketDashboardService(get_db())

@router.get("/ltp/{symbol}", response_model=Dict[str, Any])
async def get_ltp(
    symbol: str,
    service: MarketDashboardService = Depends(get_market_service),
    db: Session = Depends(get_db)
):
    """Get LTP for a symbol"""
    try:
        logger.info(f"API request: LTP for {symbol}")
        
        # Validate symbol
        if symbol.upper() not in ["NIFTY", "BANKNIFTY"]:
            raise HTTPException(status_code=400, detail="Invalid symbol. Must be NIFTY or BANKNIFTY")
        
        # Get market data
        data = await service.get_dashboard_data(symbol.upper())
        
        return {
            "status": "success",
            "data": {
                "symbol": symbol.upper(),
                "spot_price": data.spot_price,
                "market_status": str(data.market_status) if data.market_status else None,
                "timestamp": data.timestamp.isoformat() if data.timestamp else None,
                "session_type": data.session_type.value if data.session_type else None
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in LTP API: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def market_status():
    """Get current market status"""
    try:
        logger.info("API request: Market status")

        status = await get_market_status()

        return {
            "status": status
        }

    except Exception as e:
        logger.error(f"Error in market status API: {e}")
        raise HTTPException(status_code=500, detail="Failed to get market status")

@router.get("/dashboard", response_model=Dict[str, Any])
async def get_market_dashboard(
    symbol: str = "NIFTY",
    service: MarketDashboardService = Depends(get_market_service),
    db: Session = Depends(get_db)
):
    """Get market dashboard data with spot, PCR, OI"""
    try:
        logger.info(f"API request: Market dashboard for {symbol}")
        
        # Get market snapshot data
        from ai.ai_db import ai_db
        ai_db.connect()
        
        query = """
            SELECT spot_price, pcr, total_call_oi, total_put_oi, timestamp
            FROM market_snapshot
            WHERE symbol = %s
            ORDER BY timestamp DESC
            LIMIT 1
        """
        
        result = ai_db.fetch_one(query, (symbol.upper(),))
        
        if result:
            dashboard_data = {
                "symbol": symbol.upper(),
                "spot": result[0],
                "pcr": result[1],
                "total_call_oi": result[2],
                "total_put_oi": result[3],
                "timestamp": result[4].isoformat() if result[4] else None
            }
            logger.info(f"Dashboard data found: spot={result[0]}, pcr={result[1]}, oi_call={result[2]}, oi_put={result[3]}")
        else:
            # Fallback to live data if no snapshot
            logger.warning("No market snapshot found, fetching live data")
            live_data = await service.get_dashboard_data(symbol.upper())
            dashboard_data = {
                "symbol": symbol.upper(),
                "spot": live_data.get("last_price", 0),
                "pcr": 0,  # Not available from live API
                "total_call_oi": 0,  # Not available from live API
                "total_put_oi": 0,  # Not available from live API
                "timestamp": live_data.get("timestamp")
            }
        
        ai_db.disconnect()
        
        return {
            "status": "success",
            "data": dashboard_data,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in market dashboard API: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/expiries")
async def get_expiries(symbol: str):

    try:

        registry = get_instrument_registry()

        if not registry:
            return []

        expiries = registry.get_expiries(symbol)

        if not expiries:
            return []

        return expiries

    except Exception as e:

        print("EXPIRY API ERROR:", e)

        return []

@router.get("/candles")
async def get_historical_candles(
    symbol: str, 
    tf: str = "1m", 
    limit: int = 300,
    service: MarketDashboardService = Depends(get_market_service)
):
    """Get historical candles for chart rendering"""
    try:
        # Map tf to Upstox interval
        interval_map = {
            '1m': '1minute',
            '5m': '5minute',
            '15m': '15minute',
            '1h': '30minute',  # Upstox doesn't have 1h, use 30m
            '4h': 'day',
            '1d': 'day'
        }
        interval = interval_map.get(tf, '1minute')
        
        # Map symbol to Upstox instrument key
        instrument_map = {
            'NIFTY': 'NSE_INDEX|Nifty 50',
            'BANKNIFTY': 'NSE_INDEX|Nifty Bank',
            'FINNIFTY': 'NSE_INDEX|Nifty Fin Service',
        }.get(symbol.upper(), 'NSE_INDEX|Nifty 50')

        logger.info(f"Fetching candles for {symbol} ({tf})")

        # Get token
        token = os.getenv("UPSTOX_TOKEN")
        if not token:
            raise HTTPException(status_code=401, detail="No valid upstox token")

        async with httpx.AsyncClient() as client:
            # 1. Fetch Intraday Candles
            url_intra = f"https://api.upstox.com/v2/historical-candle/intraday/{instrument_map}/{interval}"
            resp_intra = await client.get(url_intra, headers={"Authorization": f"Bearer {token}", "Accept": "application/json"})
            intraday_data = resp_intra.json().get('data', {}).get('candles', [])
            
            # 2. Fetch Historical Candles (last 5 days)
            from datetime import date, timedelta
            from_date = (date.today() - timedelta(days=5)).strftime('%Y-%m-%d')
            to_date   = date.today().strftime('%Y-%m-%d')
            url_hist = f"https://api.upstox.com/v2/historical-candle/{instrument_map}/{interval}/{to_date}/{from_date}"
            resp_hist = await client.get(url_hist, headers={"Authorization": f"Bearer {token}", "Accept": "application/json"})
            historical_data = resp_hist.json().get('data', {}).get('candles', [])
            
            # 3. Merge and deduplicate
            unique_candles = {}
            # Combined list, newest data first
            for c in (intraday_data + historical_data):
                ts = c[0]
                if ts not in unique_candles:
                    unique_candles[ts] = c
            
            # Sort descending (newest first)
            data = sorted(unique_candles.values(), key=lambda x: x[0], reverse=True)
            logger.info(f"Candles loaded: {len(data)} total")

            # 4. Failsafe fallback using live spot price
            if len(data) == 0:
                logger.warning(f"No candles found for {symbol}, using spot price fallback")
                from app.services.option_chain_builder import option_chain_builder
                snapshot = option_chain_builder.get_latest_snapshot(symbol)
                if snapshot:
                    spot_price = snapshot.spot
                    now_str = datetime.now().isoformat()
                    # Upstox format: [timestamp, open, high, low, close, volume, oi]
                    data = [[now_str, spot_price, spot_price, spot_price, spot_price, 0]]

            # Convert to frontend format and apply limit (take newest 'limit' candles)
            candles = []
            for c in data[:limit]:
                # Upstox returns: [timestamp, open, high, low, close, volume, oi]
                dt = datetime.fromisoformat(c[0])
                unix_time = int(dt.timestamp())
                candles.append({
                    'time': unix_time,
                    'open': c[1],
                    'high': c[2],
                    'low': c[3],
                    'close': c[4],
                    'volume': c[5] if len(c) > 5 else 0
                })
            
            logger.info(f"Returning {len(candles)} candles for {symbol} ({tf})")

            return {
                'symbol': symbol.upper(), 
                'tf': tf, 
                'candles': candles
            }

    except Exception as e:
        logger.error(f"Candles fetch error for {symbol} ({tf}): {e}")
        return {"symbol": symbol, "tf": tf, "candles": [], "error": str(e)}
