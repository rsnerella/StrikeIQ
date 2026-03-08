import asyncio
import logging
import httpx
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from ..models.market_data import MarketSnapshot, OptionChainSnapshot
from ..models.database import AsyncSessionLocal
from .upstox_auth_service import get_upstox_auth_service
from app.utils.upstox_retry import retry_on_upstox_401

class PollerService:
    def __init__(self):
        self.auth_service = get_upstox_auth_service()
        self.base_url_v2 = "https://api.upstox.com/v2"
        self.base_url_v3 = "https://api.upstox.com/v3"
        
    async def get_token(self) -> Optional[str]:
        if self.auth_service.is_authenticated():
            return await self.auth_service.get_valid_access_token()
        return None

    async def poll_market_data(self):
        """Main polling task run by scheduler"""
        logging.info("Starting market data poll...")
        async with AsyncSessionLocal() as db:
            try:
                token = await self.get_token()
                if not token:
                    logging.warning("Poller: No access token available")
                    return

                symbols = ["NIFTY", "BANKNIFTY"]
                for symbol in symbols:
                    await self._poll_symbol(symbol, token, db)
                    
                await db.commit()
                logging.info("Market data poll completed successfully")
            except Exception as e:
                logging.error(f"Error during market data poll: {e}")
                await db.rollback()

    async def _poll_symbol(self, symbol: str, token: str, db: AsyncSession):
        """Poll specific symbol and its option chain"""
        # 1. Fetch Spot Price (v3)
        spot_price_data = await self._fetch_spot_price(symbol, token=token)
        if not spot_price_data:
            return

        # Create Market Snapshot
        snapshot = MarketSnapshot(
            symbol=symbol,
            spot_price=spot_price_data.get('last_price'),
            vwap=spot_price_data.get('vwap'),
            change=spot_price_data.get('change'),
            change_percent=spot_price_data.get('change_percent'),
            market_status="OPEN",
            timestamp=datetime.now()
        )
        db.add(snapshot)
        await db.flush() # Get snapshot ID

        # 2. Fetch Option Chain (v2)
        # For simplicity, we'll try to get the nearest expiry first
        # In a real system, we'd fetch expiries from /option/contract
        # For now, we'll implement a basic expiry detection or fetch all
        await self._poll_option_chain(symbol, snapshot.id, token=token, db=db)

    @retry_on_upstox_401
    async def _fetch_spot_price(self, symbol: str, token: str) -> Optional[Dict[str, Any]]:
        # Map symbol to Upstox key
        mapping = {
            "NIFTY": "NSE_INDEX|Nifty 50",
            "BANKNIFTY": "NSE_INDEX|Nifty Bank"
        }
        instrument_key = mapping.get(symbol)
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url_v3}/market-quote/ltp",
                    params={"instrument_key": instrument_key},
                    headers={"Authorization": f"Bearer {token}", "Accept": "application/json"}
                )
                if response.status_code == 200:
                    data = response.json().get('data', {})
                    # Upstox returns { "NSE_INDEX:Nifty 50": { ... } }
                    for key, val in data.items():
                        return val
            except Exception as e:
                logging.error(f"Error fetching spot price for {symbol}: {e}")
        return None

    @retry_on_upstox_401
    async def _poll_option_chain(self, symbol: str, snapshot_id: int, token: str, db: AsyncSession):
        """Fetch option chain for the symbol"""
        mapping = {
            "NIFTY": "NSE_INDEX|Nifty 50",
            "BANKNIFTY": "NSE_INDEX|Nifty Bank"
        }
        underlying_key = mapping.get(symbol)
        
        # We need expiry_date. Let's try to get it from the instrument list or meta
        # For this implementation, we'll assume we need to fetch it.
        # Minimalist approach: fetch all and take the closest expiry
        
        async with httpx.AsyncClient() as client:
            try:
                # First, get available expiries for the underlying
                # Endpoint: /option/contract?instrument_key=...
                expiry_response = await client.get(
                    f"{self.base_url_v2}/option/contract",
                    params={"instrument_key": underlying_key},
                    headers={"Authorization": f"Bearer {token}", "Accept": "application/json"}
                )
                
                if expiry_response.status_code == 200:
                    expiries = expiry_response.json().get('data', [])
                    if not expiries:
                        logging.warning(f"No expiries found for {symbol}")
                        return
                    
                    # Take the first expiry (nearest)
                    nearest_expiry = expiries[0].get('expiry')
                    logging.info(f"Fetching option chain for {symbol} expiry: {nearest_expiry}")
                    
                    # Now fetch the chain
                    chain_response = await client.get(
                        f"{self.base_url_v2}/option/chain",
                        params={"instrument_key": underlying_key, "expiry_date": nearest_expiry},
                        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"}
                    )
                    
                    if chain_response.status_code == 200:
                        chain_data = chain_response.json().get('data', [])
                        for item in chain_data:
                            # Item contains both call_options and put_options usually or is a list of strikes
                            # Upstox v2 Chain response: list of { strike_price, call_options: {...}, put_options: {...} }
                            strike = item.get('strike_price')
                            
                            # Save Call
                            call = item.get('call_options')
                            if call:
                                await self._add_option_to_db(snapshot_id, strike, "CE", nearest_expiry, call, db)
                                
                            # Save Put
                            put = item.get('put_options')
                            if put:
                                await self._add_option_to_db(snapshot_id, strike, "PE", nearest_expiry, put, db)
            except Exception as e:
                logging.error(f"Error polling option chain for {symbol}: {e}")

    async def _add_option_to_db(self, snapshot_id: int, strike: float, option_type: str, expiry: str, data: Dict[str, Any], db: AsyncSession):
        opt = OptionChainSnapshot(
            market_snapshot_id=snapshot_id,
            strike=strike,
            option_type=option_type,
            expiry=expiry,
            oi=data.get('market_data', {}).get('oi', 0),
            ltp=data.get('market_data', {}).get('ltp', 0),
            iv=data.get('market_data', {}).get('iv', 0),
            volume=data.get('market_data', {}).get('volume', 0),
            delta=data.get('option_greeks', {}).get('delta'),
            theta=data.get('option_greeks', {}).get('theta'),
            gamma=data.get('option_greeks', {}).get('gamma'),
            vega=data.get('option_greeks', {}).get('vega')
        )
        db.add(opt)

_poller_service = None

def get_poller_service():
    global _poller_service
    if _poller_service is None:
        _poller_service = PollerService()
    return _poller_service
