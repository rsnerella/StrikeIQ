"""
Message Router for StrikeIQ
Routes parsed protobuf ticks to appropriate processors
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from app.services.instrument_registry import get_instrument_registry
from app.services.option_chain_builder import option_chain_builder

logger = logging.getLogger(__name__)


class MessageRouter:
    """Routes market data ticks to appropriate processors"""

    def __init__(self):

        # cache registry (avoid lookup per tick)
        self.registry = get_instrument_registry()

        # Track last prices for change calculation
        self.last_index_prices: Dict[str, float] = {}

    # ---------------------------------------------------------
    # MAIN ROUTER
    # ---------------------------------------------------------

    def route_tick(self, tick: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Route a single tick to appropriate message type"""

        try:

            instrument_key = tick.get("instrument_key")
            
            # STAGE 6: VERIFY ROUTER INPUT
            logger.info("ROUTER RECEIVED → %s", tick)

            if not instrument_key:
                logger.debug("Tick missing instrument_key")
                return None

            # Handle Stage 5 nested structure
            data = tick.get("data", {})
            raw_ltp = data.get("ltp") if data else tick.get("ltp")
            raw_oi = data.get("oi") if data else tick.get("oi")
            raw_volume = data.get("volume") if data else tick.get("volume")

            if raw_ltp is None:
                ltp = 0.0
            else:
                try:
                    ltp = float(raw_ltp)
                except Exception:
                    ltp = 0.0

            try:
                oi = int(raw_oi or 0)
            except Exception:
                oi = 0

            try:
                volume = int(raw_volume or 0)
            except Exception:
                volume = 0

            tick["ltp"] = ltp
            tick["oi"] = oi
            tick["volume"] = volume

            # -------------------------------------------------
            # PARSE INSTRUMENT KEY
            # -------------------------------------------------

            parsed = self._parse_instrument_key(instrument_key)

            if not parsed:
                return None

            symbol = parsed["symbol"]
            instrument_type = parsed["type"]

            timestamp = int(datetime.utcnow().timestamp())

            # -------------------------------------------------
            # ROUTE BASED ON TYPE
            # -------------------------------------------------

            if instrument_type == "INDEX":
                
                # STAGE 3: ROUTER TYPE
                logger.info("ROUTER TYPE → index_tick")

                # push price history
                if ltp > 0:
                    try:
                        from app.services.advanced_strategies_engine import push_price
                        push_price(symbol, ltp)
                    except Exception:
                        pass

                # candle builder
                if ltp > 0:
                    try:
                        from app.services.candle_builder import candle_builder
                        candle_builder.push_tick(symbol, ltp, volume=volume)
                    except Exception:
                        pass

                # 🔥 CRITICAL FIX
                # Forward index price to option chain builder
                if ltp > 0:
                    try:
                        option_chain_builder.update_index_price(symbol, ltp)
                    except Exception as e:
                        logger.error(f"Index price forward failed: {e}")

                if ltp <= 0:
                    return None

                message = self._create_index_tick(
                    symbol,
                    ltp,
                    timestamp,
                    instrument_key=instrument_key
                )
                
                # STAGE 6: ROUTER TYPE LOG
                logger.info(
                    "ROUTER TYPE → %s",
                    message.get("type") if message else "None"
                )
                
                return message

            # -------------------------------------------------
            # OPTION ROUTING
            # -------------------------------------------------

            elif instrument_type == "OPTION":

                meta = self.registry.get_option_meta(instrument_key)

                if not meta:
                    logger.debug(f"OPTION META NOT FOUND → {instrument_key}")
                    return None

                # direct call (NO async task creation)
                try:

                    message = {
                        "type": "option_tick",
                        "symbol": meta["symbol"],
                        "data": {
                            "strike": meta["strike"],
                            "option_type": meta["option_type"],
                            "ltp": ltp,
                            "oi": oi,
                            "timestamp": timestamp
                        }
                    }

                    # STAGE 6: ROUTER TYPE LOG
                    logger.info(
                        "ROUTER TYPE → %s",
                        message.get("type") if message else "None"
                    )

                    option_chain_builder.update_option_tick(
                        symbol=meta["symbol"],
                        strike=meta["strike"],
                        right=meta["option_type"],
                        ltp=ltp,
                        oi=oi,
                        volume=volume
                    )

                except Exception as e:
                    logger.error(f"Option tick forward failed: {e}")

                return {
                    "type": "option_tick",
                    "symbol": meta["symbol"],
                    "timestamp": timestamp,
                    "data": {
                        "strike": meta["strike"],
                        "right": meta["option_type"],
                        "ltp": ltp,
                        "oi": oi,
                        "volume": volume
                    }
                }

            else:
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

                token_upper = token.upper()

                if "NIFTY 50" in token_upper or "NIFTY50" in token_upper:
                    return {"symbol": "NIFTY", "type": "INDEX"}

                elif "NIFTY BANK" in token_upper or "BANKNIFTY" in token_upper:
                    return {"symbol": "BANKNIFTY", "type": "INDEX"}

                elif "FINNIFTY" in token_upper or "FIN NIFTY" in token_upper:
                    return {"symbol": "FINNIFTY", "type": "INDEX"}

                return None

            # -------------------------------------------------
            # OPTION TOKENS
            # -------------------------------------------------

            if segment == "NSE_FO":

                try:
                    instrument_id = int(token)
                except ValueError:
                    return None

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
        timestamp: int,
        instrument_key: str = None
    ) -> Dict[str, Any]:

        if symbol not in self.last_index_prices:

            self.last_index_prices[symbol] = ltp
            change = 0

        else:

            last_price = self.last_index_prices[symbol]
            change = ltp - last_price
            self.last_index_prices[symbol] = ltp

        change_percent = (
            change / self.last_index_prices[symbol] * 100
            if self.last_index_prices[symbol] > 0 else 0
        )

        return {
            "type": "index_tick",
            "symbol": symbol,
            "instrument_key": instrument_key,
            "timestamp": timestamp,
            "data": {
                "ltp": ltp,
                "change": round(change, 2),
                "change_percent": round(change_percent, 2)
            }
        }


# ---------------------------------------------------------
# GLOBAL ROUTER INSTANCE
# ---------------------------------------------------------

message_router = MessageRouter()