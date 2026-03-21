import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from .upstox_client import UpstoxClient
from .types import MarketData, MarketStatus, AuthRequiredResponse, AuthenticationError, TokenExpiredError, APIResponseError, MarketClosedError
from ..upstox_auth_service import get_upstox_auth_service

logger = logging.getLogger(__name__)

class MarketDataCache:
    """In-memory cache for market data"""
    
    def __init__(self, ttl_seconds: int = 30):
        self._cache: Dict[str, MarketData] = {}
        self._timestamps: Dict[str, datetime] = {}
        self._ttl = timedelta(seconds=ttl_seconds)
    
    def get(self, symbol: str) -> Optional[MarketData]:
        """Get cached market data"""
        if symbol not in self._cache:
            return None
        
        # Check if cache entry is still valid
        if datetime.now(timezone.utc) - self._timestamps[symbol] > self._ttl:
            self.invalidate(symbol)
            return None
        
        logger.info(f"Cache hit for {symbol}")
        return self._cache[symbol]
    
    def set(self, symbol: str, data: MarketData):
        """Set market data in cache"""
        self._cache[symbol] = data
        self._timestamps[symbol] = datetime.now(timezone.utc)
        logger.info(f"Cached data for {symbol}")
    
    def invalidate(self, symbol: str):
        """Invalidate cache entry"""
        self._cache.pop(symbol, None)
        self._timestamps.pop(symbol, None)
        logger.info(f"Invalidated cache for {symbol}")
    
    def clear(self):
        """Clear all cache"""
        self._cache.clear()
        self._timestamps.clear()
        logger.info("Cache cleared")

class MarketDashboardService:
    """Production-grade market data service with centralized auth handling"""
    
    def __init__(self, db):
        self.db = db
        # Use singleton UpstoxClient instance
        from .upstox_client import UpstoxClient
        self.client = UpstoxClient()
        self.cache = MarketDataCache(ttl_seconds=120)
        self.auth_service = get_upstox_auth_service()
    
    async def get_dashboard_data(self, symbol: str) -> Dict[str, Any]:
        """Get market data for a symbol with centralized auth handling"""
        
        try:
            logger.info(f"Fetching dashboard data for {symbol}")
            
            # Check cache first (disabled for testing)
            # cached_data = self.cache.get(symbol.upper())
            # if cached_data:
            #     logger.info(f"Returning cached data for {symbol}")
            #     return self._format_market_data_response(cached_data)
            
            # Check authentication first
            logger.info("Checking authentication...")
            auth_status = await self._check_authentication()
            logger.info(f"Auth status result: {auth_status}")
            
            if not auth_status["authenticated"]:
                logger.info("Authentication failed, creating auth required response")
                auth_response = self._create_auth_required_response()
                logger.info(f"Auth response: {auth_response}")
                return auth_response
            
            # Get access token
            token = auth_status["token"]
            if not token:
                logger.info("No token available, creating auth required response")
                return self._create_auth_required_response()
            
            # Fetch market data
            logger.info(f"Fetching market data with token: {token[:20] if token else 'None'}...")
            market_data = await self._fetch_market_data(symbol, token)
            
            # Cache the result
            self.cache.set(symbol.upper(), market_data)
            
            logger.info(f"Successfully fetched data for {symbol}: {market_data.spot_price}")
            return self._format_market_data_response(market_data)
            
        except TokenExpiredError as e:
            logger.warning(f"Token expired for {symbol}: {e}")
            return self._create_auth_required_response()
        
        except AuthenticationError as e:
            logger.error(f"Authentication error for {symbol}: {e}")
            return self._create_auth_required_response()
        
        except MarketClosedError as e:
            logger.info(f"Market closed for {symbol}: {e}")
            market_data = self._create_market_closed_response(symbol)
            self.cache.set(symbol.upper(), market_data)
            return self._format_market_data_response(market_data)
        
        except APIResponseError as e:
            logger.error(f"API error for {symbol}: {e}")
            # Check if this is an auth error
            error_str = str(e).lower()
            if "401" in error_str or "unauthorized" in error_str or "token" in error_str:
                logger.warning(f"Detected authentication error in API response: {e}")
                return self._create_auth_required_response()
            market_data = self._create_error_response(symbol, str(e))
            return self._format_market_data_response(market_data)
        
        except Exception as e:
            logger.error(f"Unexpected error for {symbol}: {type(e).__name__}: {e}")
            # Check if this is an auth error
            error_str = str(e).lower()
            if "401" in error_str or "unauthorized" in error_str or "token" in error_str:
                logger.warning(f"Detected authentication error in exception: {e}")
                return self._create_auth_required_response()
            market_data = self._create_error_response(symbol, f"Unexpected error: {e}")
            return self._format_market_data_response(market_data)
    
    async def _check_authentication(self) -> Dict[str, Any]:
        """
        Clean authentication check with actual API validation.
        Tests token validity with Upstox API.
        """

        logger.info("Starting authentication check...")

        try:
            logger.info("Getting valid access token...")
            token = await self.auth_service.get_valid_access_token()
            logger.info(f"Token retrieved: {token[:20] if token else 'None'}...")

            if not token:
                logger.warning("No valid token available")
                return {"authenticated": False, "token": None}

            logger.info("Testing token with Upstox API...")

            # Test token with Upstox API (same as auth status endpoint)
            try:
                import httpx
                logger.info(f"Making API call to Upstox with token: {token[:20]}...")
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.get(
                        'https://api.upstox.com/v3/market-quote/ltp',
                        params={'instrument_key': 'NSE_INDEX|Nifty 50'},
                        headers={'Authorization': f'Bearer {token}'}
                    )

                    logger.info(f"Upstox API response status: {response.status_code}")

                    if response.status_code == 200:
                        logger.info("Authentication successful - token validated with Upstox")
                        return {"authenticated": True, "token": token}
                    else:
                        logger.warning(f"Token validation failed with Upstox: {response.status_code} - {response.text}")
                        return {"authenticated": False, "token": None}
            except Exception as e:
                logger.warning(f"Token validation error: {e}")
                return {"authenticated": False, "token": None}

        except Exception:
            logger.exception("Authentication check crashed")
            return {"authenticated": False, "token": None}
    
    def _create_auth_required_response(self) -> Dict[str, Any]:
        """Create standardized auth required response"""
        from ..upstox_auth_service import get_upstox_auth_service
        
        # Get the actual Upstox authorization URL
        auth_service = get_upstox_auth_service()
        state = auth_service.generate_signed_state()
        upstox_url = auth_service.get_authorization_url(state)
        
        return {
            "session_type": "AUTH_REQUIRED",
            "mode": "AUTH",
            "message": "Upstox authentication required",
            "login_url": "http://localhost:8000/api/v1/auth/upstox",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def _fetch_market_data(self, symbol: str, token: str) -> MarketData:
        """Fetch market data from Upstox API"""
        # This would integrate with instrument service and market status service
        # For now, simplified implementation
        try:
            # Try to get instrument key (simplified)
            instrument_key = await self._get_instrument_key(symbol, token)
            logger.info(f"Using instrument key: {instrument_key}")
            
            # Fetch quote
            try:
                api_response = await self.client.get_market_quote(token, instrument_key)
                logger.info(f"API response from Upstox: {api_response}")
            except TokenExpiredError as e:
                logger.warning(f"Token expired during market data fetch: {e}")
                raise  # Re-raise to trigger auth required response
            except APIResponseError as e:
                logger.error(f"API error during market data fetch: {e}")
                # Check if this is an auth error
                if "401" in str(e) or "unauthorized" in str(e).lower():
                    raise TokenExpiredError("Token appears to be revoked")
                raise  # Re-raise as API error
            except Exception as e:
                logger.error(f"Unexpected error during market data fetch: {e}")
                # Check if this is an auth error
                if "401" in str(e) or "unauthorized" in str(e).lower():
                    raise TokenExpiredError("Token appears to be revoked")
                raise APIResponseError(f"Failed to fetch market data: {e}")
            
            # Parse response
            return self._parse_market_data(symbol, api_response)
            
        except Exception as e:
            logger.error(f"Error fetching market data for {symbol}: {e}")
            raise APIResponseError(f"Failed to fetch market data: {e}")
    
    # Instrument key mapping for Upstox API v2/v3
    INSTRUMENT_MAP = {
        "NIFTY": "NSE_INDEX|Nifty 50",
        "BANKNIFTY": "NSE_INDEX|Nifty Bank"
    }
    
    async def get_nearest_expiry(self, symbol: str, token: str) -> str:
        """Get nearest expiry date for symbol"""
        try:
            # Get instrument key first
            instrument_key = await self._get_instrument_key(symbol, token)
            
            # Fetch available expiry dates
            client = await self._get_client(token, "v2")
            response = await client.get("/option/contract", params={"instrument_key": instrument_key})
            
            if response.status_code == 401:
                raise TokenExpiredError("Access token expired")
            elif response.status_code != 200:
                logger.error(f"Upstox contract API error: {response.status_code} - {response.text}")
                raise APIResponseError(f"HTTP {response.status_code}: {response.text}")
            
            data = response.json()
            contracts = data.get("data", [])
            logger.info(f"Found {len(contracts)} contracts for {instrument_key}")
            
            # Validate response
            if not isinstance(data, dict) or "data" not in data:
                raise APIResponseError("Invalid contract response")
            
            contracts = data["data"]
            if not isinstance(contracts, list) or len(contracts) == 0:
                raise APIResponseError("No expiry dates available")
            
            # Extract unique expiry dates and sort
            expiry_dates = []
            for contract in contracts:
                if "expiry" in contract:
                    expiry_dates.append(contract["expiry"])
            
            if not expiry_dates:
                raise APIResponseError("No expiry dates found")
            
            # Sort dates and return nearest future expiry
            from datetime import datetime, timezone
            current_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            future_expiries = [d for d in expiry_dates if d > current_date]
            
            if not future_expiries:
                # If no future expiries, return the latest one
                future_expiries = sorted(expiry_dates)
            
            nearest_expiry = sorted(future_expiries)[0]
            logger.info(f"Selected nearest expiry for {symbol}: {nearest_expiry}")
            return nearest_expiry
            
        except Exception as e:
            logger.error(f"Error getting expiry for {symbol}: {e}")
            raise APIResponseError(f"Failed to get expiry: {e}")

    async def _get_instrument_key(self, symbol: str, token: str) -> str:
        """Get instrument key for symbol"""
        symbol_upper = symbol.upper()
        if symbol_upper not in self.INSTRUMENT_MAP:
            raise APIResponseError(f"Unknown symbol: {symbol}")
        
        instrument_key = self.INSTRUMENT_MAP[symbol_upper]
        logger.info(f"Mapped {symbol} to instrument key: {instrument_key}")
        return instrument_key
    
    async def _get_client(self, token: str, version: str = "v2"):
        """Get HTTP client for API calls"""
        import httpx
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        }
        
        base_urls = {
            "v2": "https://api.upstox.com/v2",
            "v3": "https://api.upstox.com/v3"
        }
        
        base_url = base_urls.get(version, base_urls["v2"])
        return httpx.AsyncClient(base_url=base_url, headers=headers, timeout=10.0)
    
    def _parse_market_data(self, symbol: str, api_response: Dict[str, Any]) -> MarketData:
        """Parse API response into MarketData"""
        try:
            # Validate Upstox response
            if api_response.get("status") != "success":
                logger.error(f"Upstox API error: {api_response}")
                # Check if this is an authentication error
                if "401" in str(api_response) or "unauthorized" in str(api_response).lower():
                    raise TokenExpiredError("Token appears to be revoked")
                raise APIResponseError(f"Upstox API error: {api_response}")
            
            data = api_response.get("data", {})
            
            if not data:
                logger.error(f"Empty LTP response: {api_response}")
                return self._build_no_data_response(symbol)
            
            # Extract nested instrument data
            instrument_data = next(iter(data.values()), None)
            
            if not instrument_data:
                logger.error(f"No instrument data in response: {api_response}")
                return self._build_no_data_response(symbol)
            
            ltp = instrument_data.get("last_price")
            
            if ltp is None:
                logger.error(f"No last_price in instrument data: {instrument_data}")
                return self._build_no_data_response(symbol)
            
            # Fix market_status logic
            market_status = MarketStatus.OPEN
            
            logger.info(f"Successfully parsed spot price for {symbol}: {ltp}")
            
            return MarketData(
                symbol=symbol,
                last_price=ltp,
                change=0,
                change_percent=0,
                volume=0,
                timestamp=datetime.now(timezone.utc)
            )
            
        except Exception as e:
            logger.error(f"Error parsing market data for {symbol}: {e}")
            raise APIResponseError(f"Failed to parse market data: {e}")
    
    def _build_no_data_response(self, symbol: str) -> MarketData:
        """Build no data response"""
        return MarketData(
            symbol=symbol,
            last_price=None,
            change=0,
            change_percent=0,
            volume=0,
            timestamp=datetime.now(timezone.utc),
            market_status=MarketStatus.NO_DATA
        )
    
    def _get_market_status(self) -> MarketStatus:
        """Get actual market status based on NSE trading hours"""
        from datetime import datetime, timezone
        
        # Get current time in IST (UTC+5:30)
        now_utc = datetime.now(timezone.utc)
        now_ist = now_utc + timedelta(hours=5, minutes=30)
        
        # NSE trading hours: 9:15 AM - 3:30 PM IST, Monday-Friday
        current_time = now_ist.time()
        current_day = now_ist.weekday()  # Monday=0, Sunday=6
        
        # Check if it's a weekday
        if current_day >= 5:  # Saturday (5) or Sunday (6)
            logger.info(f"Market closed: Weekend (Day {current_day})")
            return MarketStatus.CLOSED
        
        # Check if within trading hours (9:15 AM - 3:30 PM)
        market_open = datetime.strptime("09:15", "%H:%M").time()
        market_close = datetime.strptime("15:30", "%H:%M").time()
        
        if market_open <= current_time <= market_close:
            logger.info(f"Market open: {current_time} within trading hours")
            return MarketStatus.OPEN
        else:
            logger.info(f"Market closed: {current_time} outside trading hours (09:15-15:30)")
            return MarketStatus.CLOSED
    
    def _create_market_closed_response(self, symbol: str) -> MarketData:
        """Create market closed response"""
        return MarketData(
            symbol=symbol,
            last_price=None,
            change=0,
            change_percent=0,
            volume=0,
            timestamp=datetime.now(timezone.utc),
            market_status=MarketStatus.CLOSED
        )
    
    def _create_error_response(self, symbol: str, error_message: str) -> MarketData:
        """Create error response"""
        return MarketData(
            symbol=symbol,
            last_price=None,
            change=0,
            change_percent=0,
            volume=0,
            timestamp=datetime.now(timezone.utc),
            market_status=MarketStatus.ERROR
        )
    
    def _format_market_data_response(self, market_data: MarketData) -> Dict[str, Any]:
        """Format MarketData for API response"""
        return {
            "symbol": market_data.symbol,
            "last_price": market_data.last_price,
            "previous_close": market_data.previous_close,
            "change": market_data.change,
            "change_percent": market_data.change_percent,
            "timestamp": market_data.timestamp.isoformat(),
            "market_status": str(market_data.market_status)
        }
    
    async def close(self):
        """Close all services"""
        await self.client.close()
        self.cache.clear()
        logger.info("MarketDashboardService closed")
