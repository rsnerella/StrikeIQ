import asyncio
import logging
import httpx
from datetime import datetime
from typing import Dict, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..models.market_data import MarketSnapshot, OptionChainSnapshot
from ..models.database import AsyncSessionLocal

from app.services.token_manager import token_manager
from app.utils.upstox_retry import retry_on_upstox_401
from app.core.diagnostics import diag, increment_counter
from app.services.websocket_market_feed import get_market_feed

logger = logging.getLogger(__name__)


class PollerService:

    def __init__(self):

        self.base_url_v2 = "https://api.upstox.com/v2"
        self.base_url_v3 = "https://api.upstox.com/v3"

        self.symbol_map = {
            "NIFTY": "NSE_INDEX|Nifty 50",
            "BANKNIFTY": "NSE_INDEX|Nifty Bank"
        }

        self.active_symbol = "NIFTY"
        self.active_expiry: Optional[str] = None

        # shared http client
        self.http_client = httpx.AsyncClient(timeout=10)

    # ================= SUBSCRIPTION UPDATE =================

    def update_subscription(self, symbol: str, expiry: Optional[str] = None):

        if symbol not in self.symbol_map:
            logger.warning(f"Invalid symbol subscription: {symbol}")
            return

        self.active_symbol = symbol
        self.active_expiry = expiry

        logger.info(f"POLLER SUBSCRIPTION UPDATED → {symbol} {expiry}")

    # ================= TOKEN =================

    async def get_token(self) -> Optional[str]:

        try:
            return await token_manager.get_token()
        except Exception as e:
            logger.error(f"Token fetch failed: {e}")
            return None

    # ================= MAIN POLLER =================

    async def poll_market_data(self):

        logger.info("Starting market data poll")

        diag("POLLER", "Polling option chain snapshot")

        # ---- FIX: skip poller if WS feed active ----
        try:
            ws_feed = get_market_feed()
            if ws_feed and ws_feed.is_connected():
                logger.info("Skipping poller because WS feed active")
                return
        except Exception:
            pass

        async with AsyncSessionLocal() as db:

            try:

                token = await self.get_token()

                logger.info(
                    f"POLLER TOKEN CHECK → {'FOUND' if token else 'MISSING'}"
                )

                if not token:

                    logger.warning(
                        "Poller waiting for Upstox access token..."
                    )

                    await asyncio.sleep(5)
                    return

                symbol = self.active_symbol

                await self._poll_symbol(symbol, token, db)

                await db.commit()

                logger.info("Market data poll completed")

            except Exception as e:

                logger.error(f"Poller error: {e}")

                await db.rollback()

                await asyncio.sleep(5)

    # ================= SYMBOL POLLING =================

    async def _poll_symbol(
        self,
        symbol: str,
        token: str,
        db: AsyncSession
    ):

        instrument_key = self.symbol_map.get(symbol)

        if not instrument_key:
            logger.error(f"Unknown symbol {symbol}")
            return

        spot_price_data = await self._fetch_spot_price(
            symbol,
            instrument_key,
            token
        )

        if not spot_price_data:
            return

        diag("DB_SAVE", "Saving market snapshot")

        snapshot = MarketSnapshot(
            symbol=symbol,
            spot_price=spot_price_data.get("last_price"),
            vwap=spot_price_data.get("vwap"),
            change=spot_price_data.get("change"),
            change_percent=spot_price_data.get("change_percent"),
            market_status="OPEN",
            timestamp=datetime.utcnow()
        )

        db.add(snapshot)

        await db.flush()

        await self._poll_option_chain(
            symbol,
            instrument_key,
            snapshot.id,
            token,
            db
        )

    # ================= FETCH SPOT =================

    @retry_on_upstox_401
    async def _fetch_spot_price(
        self,
        symbol: str,
        instrument_key: str,
        token: str
    ) -> Optional[Dict[str, Any]]:

        try:

            response = await self.http_client.get(
                f"{self.base_url_v3}/market-quote/ltp",
                params={"instrument_key": instrument_key},
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json"
                }
            )

            if response.status_code != 200:
                return None

            data = response.json().get("data", {})

            for _, val in data.items():
                return val

        except Exception as e:

            logger.error(
                f"Spot price fetch failed for {symbol}: {e}"
            )

        return None

    # ================= OPTION CHAIN =================

    @retry_on_upstox_401
    async def _poll_option_chain(
        self,
        symbol: str,
        instrument_key: str,
        snapshot_id: int,
        token: str,
        db: AsyncSession
    ):

        try:

            expiry_response = await self.http_client.get(
                f"{self.base_url_v2}/option/contract",
                params={"instrument_key": instrument_key},
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json"
                }
            )

            if expiry_response.status_code != 200:
                return

            expiries = expiry_response.json().get("data", [])

            if not expiries:
                logger.warning(f"No expiries for {symbol}")
                return

            expiry_list = sorted(
                [e.get("expiry") for e in expiries if e.get("expiry")],
                key=lambda x: datetime.strptime(x, "%Y-%m-%d")
            )

            if self.active_expiry and self.active_expiry not in expiry_list:
                logger.warning("Frontend expiry not available, fallback")
                self.active_expiry = None

            if self.active_expiry:
                nearest_expiry = datetime.strptime(
                    self.active_expiry, "%Y-%m-%d"
                ).date()
            else:
                nearest_expiry = datetime.strptime(
                    expiry_list[0], "%Y-%m-%d"
                ).date()

            logger.info(
                f"Fetching option chain {symbol} expiry {nearest_expiry}"
            )

            chain_response = await self.http_client.get(
                f"{self.base_url_v2}/option/chain",
                params={
                    "instrument_key": instrument_key,
                    "expiry_date": nearest_expiry
                },
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json"
                }
            )

            if chain_response.status_code != 200:
                return

            chain_data = chain_response.json().get("data", [])

            for item in chain_data:

                strike = float(item.get("strike_price") or 0)

                if strike == 0:
                    continue

                call = item.get("call_options")
                put = item.get("put_options")

                if call:

                    await self._add_option_to_db(
                        snapshot_id,
                        strike,
                        "CE",
                        nearest_expiry,
                        call,
                        db
                    )

                if put:

                    await self._add_option_to_db(
                        snapshot_id,
                        strike,
                        "PE",
                        nearest_expiry,
                        put,
                        db
                    )

        except Exception as e:

            logger.error(
                f"Option chain polling failed for {symbol}: {e}"
            )

    # ================= SAVE OPTION =================

    async def _add_option_to_db(
        self,
        snapshot_id: int,
        strike: float,
        option_type: str,
        expiry,
        data: Dict[str, Any],
        db: AsyncSession
    ):

        try:

            opt = OptionChainSnapshot(
                market_snapshot_id=snapshot_id,
                symbol=self.active_symbol,
                strike=strike,
                option_type=option_type,
                expiry=str(expiry),  # FIX: date → string
                oi=int(data.get("market_data", {}).get("oi") or 0),
                ltp=data.get("market_data", {}).get("ltp", 0),
                iv=data.get("market_data", {}).get("iv", 0),
                volume=int(data.get("market_data", {}).get("volume") or 0),
                delta=data.get("option_greeks", {}).get("delta"),
                theta=data.get("option_greeks", {}).get("theta"),
                gamma=data.get("option_greeks", {}).get("gamma"),
                vega=data.get("option_greeks", {}).get("vega")
            )

            db.add(opt)

            increment_counter("db_saves")

        except Exception as e:

            logger.error(f"DB insert failed: {e}")

            raise

    # ================= SHUTDOWN =================

    async def shutdown(self):
        await self.http_client.aclose()


# ================= SINGLETON =================

_poller_service = None


def get_poller_service():

    global _poller_service

    if _poller_service is None:
        _poller_service = PollerService()

    return _poller_service