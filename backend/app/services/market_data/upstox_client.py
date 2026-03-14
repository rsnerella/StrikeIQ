import threading
import asyncio
import httpx
import logging
import json
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from ...core.config import settings
from .types import InstrumentInfo, APIResponseError, AuthenticationError
from app.utils.upstox_retry import retry_on_upstox_401
from fastapi import HTTPException
from app.services.token_manager import token_manager

logger = logging.getLogger(__name__)

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class UpstoxClient:

    _instance: Optional["UpstoxClient"] = None
    _instance_lock = threading.Lock()

    def __new__(cls, *args, **kwargs):

        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)

        return cls._instance

    def __init__(self):

        if getattr(self, "_initialized", False):
            return

        self.base_url_v2 = "https://api.upstox.com/v2"
        self.base_url_v3 = "https://api.upstox.com/v3"

        self._client: Optional[httpx.AsyncClient] = None

        self._rate_limit = asyncio.Semaphore(5)
        self._last_request_time = 0
        self._min_delay = 0.25

        self._memory_cache = {}
        self._cache_timestamps = {}

        self._expiry_cache_ttl = 3600
        self._contracts_cache_ttl = 1800

        self.INSTRUMENT_MAP = {
            "NIFTY": "NSE_INDEX|Nifty 50",
            "BANKNIFTY": "NSE_INDEX|Nifty Bank",
            "FINNIFTY": "NSE_INDEX|Nifty Fin Service",
        }

        self._initialized = True

    # --------------------------------------------------
    # CACHE
    # --------------------------------------------------

    def _get_cache_key(self, symbol: str, data_type: str):

        return f"upstox:{data_type}:{symbol.lower()}"

    def _is_cache_valid(self, cache_key):

        if cache_key not in self._cache_timestamps:
            return False

        cache_time = self._cache_timestamps[cache_key]

        ttl = (
            self._expiry_cache_ttl
            if "expiry" in cache_key
            else self._contracts_cache_ttl
        )

        return (time.time() - cache_time) < ttl

    def _set_cache(self, cache_key, data):

        self._memory_cache[cache_key] = data
        self._cache_timestamps[cache_key] = time.time()

    def _get_cache(self, cache_key):

        if cache_key in self._memory_cache and self._is_cache_valid(cache_key):

            logger.debug(f"Cache hit {cache_key}")
            return self._memory_cache[cache_key]

        if cache_key in self._memory_cache:
            del self._memory_cache[cache_key]
            self._cache_timestamps.pop(cache_key, None)

        return None

    # --------------------------------------------------
    # HTTP CLIENT
    # --------------------------------------------------

    async def _get_client(self, access_token):

        auth_header = f"Bearer {access_token}"

        if (
            self._client is None
            or self._client.headers.get("Authorization") != auth_header
        ):

            if self._client:
                await self._client.aclose()

            self._client = httpx.AsyncClient(
                headers={"Authorization": auth_header},
                timeout=30,
            )

        return self._client

    async def close(self):

        if self._client:
            await self._client.aclose()
            self._client = None

    # --------------------------------------------------
    # SAFE REQUEST
    # --------------------------------------------------

    @retry_on_upstox_401
    async def _make_request(self, method, url, **kwargs):

        async with self._rate_limit:

            try:

                now = time.time()

                diff = now - self._last_request_time

                if diff < self._min_delay:
                    await asyncio.sleep(self._min_delay - diff)

                self._last_request_time = time.time()

                token = await token_manager.get_valid_token()

                client = await self._get_client(token)

                request_fn = getattr(client, method.lower())

                response = await request_fn(url, **kwargs)

                if response.status_code == 401:
                    raise HTTPException(
                        status_code=401,
                        detail="Upstox authentication required",
                    )

                if response.status_code == 429:
                    await asyncio.sleep(1)
                    response = await request_fn(url, **kwargs)

                return response

            except httpx.RequestError as e:

                logger.error(f"Upstox request error {e}")
                raise APIResponseError(str(e))

    # --------------------------------------------------
    # OPTION EXPIRIES
    # --------------------------------------------------

    async def get_option_expiries(self, symbol):

        cache_key = self._get_cache_key(symbol, "expiry")

        cached = self._get_cache(cache_key)

        if cached:
            return cached

        instrument_key = self.INSTRUMENT_MAP.get(symbol.upper())

        if not instrument_key:
            raise APIResponseError(f"Unknown symbol {symbol}")

        response = await self._make_request(
            "get",
            f"{self.base_url_v2}/option/contract",
            params={"instrument_key": instrument_key},
        )

        data = response.json()

        contracts = data.get("data", [])

        expiries = []

        for item in contracts:

            if isinstance(item, str):
                expiries.append(item)

            elif isinstance(item, dict):
                exp = item.get("expiry")
                if exp:
                    expiries.append(exp)

        expiries = sorted(expiries)

        self._set_cache(cache_key, expiries)

        return expiries

    # --------------------------------------------------
    # MARKET QUOTE
    # --------------------------------------------------

    async def get_market_quote(self, instrument_key):

        response = await self._make_request(
            "get",
            f"{self.base_url_v2}/market-quote/ltp",
            params={"instrument_key": instrument_key},
        )

        data = response.json()

        if not isinstance(data, dict):
            raise APIResponseError("Invalid response")

        if "data" not in data:
            raise APIResponseError("Missing data")

        return data

    # --------------------------------------------------
    # LTP
    # --------------------------------------------------

    async def get_ltp(self, instrument_key):

        try:

            response = await self.get_market_quote(instrument_key)

            if not response or "data" not in response:
                return None

            keys = list(response["data"].keys())

            if not keys:
                return None

            key = keys[0]

            ltp = response["data"][key].get("last_price")

            if ltp:
                return float(ltp)

            return None

        except Exception as e:

            logger.error(f"LTP fetch error {e}")

            return None

    # --------------------------------------------------
    # LOG RESPONSE
    # --------------------------------------------------

    async def _log_final_response(self, data):

        logger.info("=== BACKEND RESPONSE ===")
        logger.info(json.dumps(data, indent=2))
        logger.info("=== END RESPONSE ===")