"""
Message Router for StrikeIQ
Routes parsed protobuf ticks to appropriate processors
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class MessageRouter:
    """Routes market data ticks to appropriate processors"""

    def __init__(self):
        # Track last prices for index change calculation
        self.last_index_prices: Dict[str, float] = {}

    # ---------------------------------------------------------
    # MAIN ROUTER
    # ---------------------------------------------------------

    def route_tick(self, tick: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Route a single tick to appropriate message type
        """

        try:

            instrument_key = tick.get("instrument_key")

            if not instrument_key:
                logger.warning(f"Tick missing instrument_key: {tick}")
                return None

            # -------------------------------------------------
            # SAFE NUMERIC CONVERSION
            # -------------------------------------------------

            raw_ltp = tick.get("ltp")
            raw_oi = tick.get("oi")
            raw_volume = tick.get("volume")

            if raw_ltp is None:
                logger.warning(f"Invalid tick data (missing LTP): {tick}")
                return None

            try:
                ltp = float(raw_ltp)
            except Exception:
                logger.warning(f"Invalid LTP value: {tick}")
                return None

            try:
                oi = int(raw_oi or 0)
            except Exception:
                oi = 0

            try:
                volume = int(raw_volume or 0)
            except Exception:
                volume = 0

            # Update normalized values
            tick["ltp"] = ltp
            tick["oi"] = oi
            tick["volume"] = volume

            logger.info(
                f"ROUTING TICK → {instrument_key} LTP={ltp} OI={oi} VOL={volume}"
            )

            # -------------------------------------------------
            # PARSE INSTRUMENT KEY
            # -------------------------------------------------

            parsed = self._parse_instrument_key(instrument_key)

            if not parsed:
                logger.warning(f"Could not parse instrument key: {instrument_key}")
                return None

            symbol = parsed["symbol"]
            instrument_type = parsed["type"]

            timestamp = int(datetime.utcnow().timestamp())

            # -------------------------------------------------
            # ROUTE BASED ON TYPE
            # -------------------------------------------------

            if instrument_type == "INDEX":
                return self._create_index_tick(symbol, ltp, timestamp)

            elif instrument_type == "OPTION":
                return self._create_option_tick(
                    symbol,
                    parsed,
                    ltp,
                    oi,
                    volume,
                    timestamp
                )

            else:
                logger.warning(f"Unknown instrument type: {instrument_type}")
                return None

        except Exception as e:
            logger.error(f"Error routing tick: {e}", exc_info=True)
            return None

    # ---------------------------------------------------------
    # INSTRUMENT KEY PARSER
    # ---------------------------------------------------------

    def _parse_instrument_key(self, instrument_key: str) -> Optional[Dict[str, Any]]:
        """Parse instrument key to extract symbol and type"""

        try:

            if "|" not in instrument_key:
                return None

            segment, token = instrument_key.split("|", 1)

            # -------------------------------------------------
            # INDEX INSTRUMENTS
            # -------------------------------------------------

            if segment == "NSE_INDEX":

                if "Nifty 50" in token:
                    return {"symbol": "NIFTY", "type": "INDEX"}

                elif "Nifty Bank" in token:
                    return {"symbol": "BANKNIFTY", "type": "INDEX"}

                else:
                    logger.debug(f"Unknown index symbol: {token}")
                    return None

            # -------------------------------------------------
            # OPTION / FUTURE TOKENS
            # -------------------------------------------------

            if segment == "NSE_FO":

                # Upstox V3 sends numeric instrument token
                try:
                    instrument_id = int(token)
                except ValueError:
                    logger.warning(f"Invalid option token: {token}")
                    return None

                # Symbol resolved later by option chain builder
                return {
                    "symbol": "UNKNOWN",
                    "type": "OPTION",
                    "instrument_id": instrument_id
                }

            return None

        except Exception as e:
            logger.error(f"Error parsing instrument key {instrument_key}: {e}")
            return None

    # ---------------------------------------------------------
    # INDEX TICK CREATION
    # ---------------------------------------------------------

    def _create_index_tick(
        self,
        symbol: str,
        ltp: float,
        timestamp: int
    ) -> Dict[str, Any]:

        last_price = self.last_index_prices.get(symbol, ltp)

        change = ltp - last_price

        change_percent = (change / last_price * 100) if last_price > 0 else 0

        # Update last price
        self.last_index_prices[symbol] = ltp

        return {
            "type": "index_tick",
            "symbol": symbol,
            "timestamp": timestamp,
            "data": {
                "ltp": ltp,
                "change": round(change, 2),
                "change_percent": round(change_percent, 2)
            }
        }

    # ---------------------------------------------------------
    # OPTION TICK CREATION
    # ---------------------------------------------------------

    def _create_option_tick(
        self,
        symbol: str,
        parsed: Dict[str, Any],
        ltp: float,
        oi: int,
        volume: int,
        timestamp: int
    ) -> Dict[str, Any]:

        return {
            "type": "option_tick",
            "symbol": symbol,
            "timestamp": timestamp,
            "data": {
                "instrument_id": parsed.get("instrument_id"),
                "ltp": ltp,
                "oi": oi,
                "volume": volume
            }
        }


# ---------------------------------------------------------
# GLOBAL ROUTER INSTANCE
# ---------------------------------------------------------

message_router = MessageRouter()