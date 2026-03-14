"""
Option Chain Snapshot Service
Fetches complete option chain data via REST API to supplement WebSocket LTP data
"""

import asyncio
import logging
import httpx
from typing import Dict, Optional
from datetime import datetime
from ..services.token_manager import token_manager

logger = logging.getLogger(__name__)

class OptionChainSnapshot:
    """Fetches and caches option chain snapshots from REST API"""
    
    def __init__(self):
        self.cache: Dict[str, Dict] = {}
        self.last_fetch: Dict[str, datetime] = {}
        self.api_client = None  # Will be injected
        
        # Standardized cache structure
        self.option_chain_cache = {}
        
    def set_api_client(self, api_client):
        """Set the Upstox API client"""
        self.api_client = api_client
    
    async def fetch_option_chain(self, symbol: str) -> Optional[Dict]:
        """
        Fetch full option chain snapshot for symbol
        
        Args:
            symbol: Symbol name (e.g., "NIFTY")
            
        Returns:
            Normalized option chain data or None if failed
        """
        if not self.api_client:
            logger.warning("API client not set for option chain snapshot")
            return None
            
        try:
            logger.info(f"FETCHING OPTION SNAPSHOT → {symbol}")
            
            # Use async httpx client
            async with httpx.AsyncClient(timeout=10) as client:
                token = await token_manager.get_token()
                if not token:
                    logger.error("No access token available for option chain snapshot")
                    return {}
                
                # Map symbol to instrument key
                instrument_key = "NSE_INDEX|Nifty 50" if symbol == "NIFTY" else f"NSE_INDEX|{symbol}"
                
                # Get current expiry (use next Thursday as default)
                from datetime import datetime, timedelta
                today = datetime.now()
                days_until_thursday = (3 - today.weekday()) % 7
                if days_until_thursday == 0:
                    days_until_thursday = 7
                expiry_date = (today + timedelta(days=days_until_thursday)).strftime("%Y-%m-%d")
                
                logger.info(f"OPTION SNAPSHOT API CALL → {symbol} instrument_key={instrument_key} expiry={expiry_date}")
                
                response = await client.get(
                    "https://api.upstox.com/v2/option/chain",
                    params={
                        "instrument_key": instrument_key,
                        "expiry_date": expiry_date
                    },
                    headers={"Authorization": f"Bearer {token}"}
                )
                
                if response.status_code != 200:
                    logger.warning(f"No option chain data for {symbol} - HTTP {response.status_code}")
                    return None
                
                data = response.json()
                
                logger.info(f"OPTION SNAPSHOT RESPONSE RECEIVED → {symbol}")
                logger.info(f"API RESPONSE STRUCTURE → {list(data.keys()) if data else 'None'}")
                if data and 'data' in data:
                    logger.info(f"API RESPONSE DATA LENGTH → {len(data['data'])} items")
                    if data['data']:
                        sample_item = data['data'][0]
                        logger.info(f"API RESPONSE SAMPLE ITEM → {list(sample_item.keys())}")
                    else:
                        logger.warning("API RESPONSE DATA ARRAY IS EMPTY")
                else:
                    logger.warning(f"API RESPONSE MISSING 'data' key → {data}")
                
                if not data or 'data' not in data:
                    logger.warning(f"No option chain data for {symbol}")
                    return None
                
                # Normalize data
                normalized_chain = {}
                
                for strike_data in data['data']:
                    strike = strike_data.get('strike')
                    if not strike:
                        continue
                        
                    normalized_chain[strike] = {
                        "oi": int(strike_data.get('oi', 0)),
                        "volume": int(strike_data.get('volume', 0)),
                        "bid": float(strike_data.get('bid', 0.0)),
                        "ask": float(strike_data.get('ask', 0.0)),
                        "iv": float(strike_data.get('iv', 0.0))
                    }
                
                # Update cache
                self.cache[symbol] = normalized_chain
                self.option_chain_cache[symbol] = normalized_chain
                self.last_fetch[symbol] = datetime.now()
                
                logger.info(f"OPTION SNAPSHOT UPDATED → {symbol} ({len(normalized_chain)} strikes)")
                return normalized_chain
                
        except Exception as e:
            logger.error(f"OPTION SNAPSHOT ERROR → {symbol}: {e}")
            return {}
    
    def get_cached_chain(self, symbol: str) -> Optional[Dict]:
        """Get cached option chain for symbol"""
        return self.option_chain_cache.get(symbol)
    
    def is_cache_fresh(self, symbol: str, max_age_seconds: int = 10) -> bool:
        """Check if cached data is fresh"""
        if symbol not in self.last_fetch:
            return False
            
        age = (datetime.now() - self.last_fetch[symbol]).total_seconds()
        return age < max_age_seconds

# Global instance
option_chain_snapshot = OptionChainSnapshot()
