from __future__ import annotations

import asyncio
import aiohttp
import gzip
import json
import logging
from datetime import datetime, date
from typing import Optional, Dict, Any

from app.core.redis_client import redis_client

logger = logging.getLogger(__name__)

UPSTOX_CDN = "https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz"


def normalize_expiry(exp) -> Optional[str]:

    if isinstance(exp, int):
        return datetime.utcfromtimestamp(exp / 1000).date().isoformat()

    if isinstance(exp, str):

        if "-" in exp:
            return exp

        return datetime.strptime(exp, "%Y%m%d").date().isoformat()

    return None


class InstrumentRegistry:

    def __init__(self):

        self._ready_event = asyncio.Event()
        self._local_lock = asyncio.Lock()

        # OPTIONS
        self.options: Dict[str, Dict[str, Dict[int, Dict[str, str]]]] = {}

        # FUTURES
        self.futidx: Dict[str, Dict[str, str]] = {}

        # REVERSE LOOKUP
        self.instrument_map: Dict[str, Dict[str, Any]] = {}

        # TOKEN LOOKUP
        self.token_map: Dict[str, str] = {}

    # --------------------------------------------------
    # LOAD REGISTRY
    # --------------------------------------------------

    async def load(self):

        if self._ready_event.is_set():
            return

        lock = redis_client.lock("instrument_registry_lock", timeout=120)

        await lock.acquire()

        try:

            if self._ready_event.is_set():
                return

            print("🔥 Loading Instrument Registry from Upstox CDN...")

            async with self._local_lock:

                async with aiohttp.ClientSession() as session:

                    async with session.get(UPSTOX_CDN) as response:
                        gz = await response.read()

                raw = gzip.decompress(gz)
                data = json.loads(raw)

                if isinstance(data, dict) and "data" in data:
                    data = data["data"]

                for inst in data:

                    if inst.get("segment") != "NSE_FO":
                        continue

                    name = inst.get("name")
                    itype = inst.get("instrument_type")

                    if name not in ("NIFTY", "BANKNIFTY", "FINNIFTY"):
                        continue

                    expiry = normalize_expiry(inst.get("expiry"))

                    if not expiry:
                        continue

                    # OPTIONS
                    if itype in ("CE", "PE"):

                        strike = int(inst["strike_price"])

                        self.options \
                            .setdefault(name, {}) \
                            .setdefault(expiry, {}) \
                            .setdefault(strike, {})[itype] = inst["instrument_key"]

                    # FUTURES
                    elif itype == "FUT":

                        self.futidx \
                            .setdefault(name, {})[expiry] = inst["instrument_key"]

                print("🟢 Instrument Registry Loaded Successfully")
                print(f"Available Symbols: {list(self.options.keys())}")

                self._build_reverse_maps()

                self._ready_event.set()

        finally:
            lock.release()

    # --------------------------------------------------
    # BUILD REVERSE LOOKUPS
    # --------------------------------------------------

    def _build_reverse_maps(self):

        self.instrument_map = {}
        self.token_map = {}

        for symbol, expiries in self.options.items():

            for expiry, strikes in expiries.items():

                for strike, opt in strikes.items():

                    ce = opt.get("CE")
                    pe = opt.get("PE")

                    if ce:

                        self.instrument_map[ce] = {
                            "symbol": symbol,
                            "expiry": expiry,
                            "strike": strike,
                            "option_type": "CE"
                        }

                        token = ce.partition("|")[2]

                        if token:
                            self.token_map[token] = ce

                    if pe:

                        self.instrument_map[pe] = {
                            "symbol": symbol,
                            "expiry": expiry,
                            "strike": strike,
                            "option_type": "PE"
                        }

                        token = pe.partition("|")[2]

                        if token:
                            self.token_map[token] = pe

        logger.info(
            "Instrument reverse map built → %d FO entries",
            len(self.instrument_map)
        )

    # --------------------------------------------------
    # LOCAL CACHE FALLBACK
    # --------------------------------------------------

    async def _load_from_local_cache(self):

        from pathlib import Path

        cache_file = Path("data/instruments.json")

        if not cache_file.exists():
            raise FileNotFoundError("Local cache file not found")

        print(f"📦 Loading from local cache: {cache_file}")

        with open(cache_file, "r", encoding="utf-8") as f:
            raw = json.load(f)

        if isinstance(raw, dict) and "instruments" in raw:
            data = raw["instruments"]
        else:
            data = raw

        for inst in data:

            if inst.get("segment") != "NSE_FO":
                continue

            name = inst.get("name")
            itype = inst.get("instrument_type")

            if name not in ("NIFTY", "BANKNIFTY", "FINNIFTY"):
                continue

            expiry = normalize_expiry(inst.get("expiry"))

            if not expiry:
                continue

            if itype in ("CE", "PE"):

                strike = int(inst["strike_price"])

                self.options \
                    .setdefault(name, {}) \
                    .setdefault(expiry, {}) \
                    .setdefault(strike, {})[itype] = inst["instrument_key"]

            elif itype == "FUT":

                self.futidx \
                    .setdefault(name, {})[expiry] = inst["instrument_key"]

        print("🟢 Instrument Registry Loaded from Local Cache")

        self._build_reverse_maps()

        self._ready_event.set()

    # --------------------------------------------------
    # READY WAIT
    # --------------------------------------------------

    async def wait_until_ready(self):

        await self._ready_event.wait()

    # --------------------------------------------------
    # ACCESSORS
    # --------------------------------------------------

    def get_options(self, symbol: str, expiry):

        if isinstance(expiry, date):
            expiry = expiry.isoformat()

        return self.options.get(symbol, {}).get(expiry)

    def get_future(self, symbol: str, expiry):

        if isinstance(expiry, date):
            expiry = expiry.isoformat()

        return self.futidx.get(symbol, {}).get(expiry)

    def get_expiries(self, symbol: str):

        if symbol not in self.options:
            return []

        return sorted(self.options[symbol].keys())

    def get_option_instruments(self, symbol: str):

        if symbol not in self.options:
            return []

        instruments = []

        for expiry in self.options[symbol]:

            for strike in self.options[symbol][expiry]:

                for option_type in ("CE", "PE"):

                    ikey = self.options[symbol][expiry][strike].get(option_type)

                    if ikey:
                        instruments.append(ikey)

        return instruments

    def get_option_meta(self, instrument_key):

        return self.instrument_map.get(instrument_key)

    def get_by_token(self, token: str):

        ikey = self.token_map.get(token)

        if ikey:
            return self.instrument_map.get(ikey)

        return None


# --------------------------------------------------
# SINGLETON
# --------------------------------------------------

_registry_instance: InstrumentRegistry | None = None


def get_instrument_registry() -> InstrumentRegistry:

    global _registry_instance

    if _registry_instance is None:
        _registry_instance = InstrumentRegistry()

    return _registry_instance