import time
import logging
from typing import List, Dict

from app.proto.MarketDataFeedV3_pb2 import FeedResponse
from app.services.instrument_registry import get_instrument_registry

logger = logging.getLogger(__name__)


async def decode_protobuf_message(message: bytes, tick_queue=None) -> List[Dict]:

    ticks: List[Dict] = []

    try:

        response = FeedResponse()
        response.ParseFromString(message)

        feeds = response.feeds

        if not feeds:
            return []

        registry = get_instrument_registry()
        now = time.time()

        for entry in feeds:

            instrument_key = entry.key
            feed = entry.value

            try:

                # -----------------------------
                # DEFAULT VALUES
                # -----------------------------

                ltp = None
                oi = 0
                oi_change = 0
                volume = 0

                bid = 0.0
                ask = 0.0
                bid_qty = 0
                ask_qty = 0

                iv = 0.0
                delta = 0.0
                theta = 0.0
                gamma = 0.0
                vega = 0.0

                # -----------------------------
                # DETERMINE FEED TYPE
                # -----------------------------

                data_type = feed.WhichOneof("data")

                # --------------------------------
                # DIRECT LTPC FEED
                # --------------------------------

                if data_type == "ltpc":

                    if feed.HasField("ltpc"):
                        ltp = feed.ltpc.ltp

                # --------------------------------
                # FULL FEED WRAPPER
                # --------------------------------

                elif data_type == "ff":

                    ff = feed.ff
                    ff_type = ff.WhichOneof("data")

                    # INDEX FEED
                    if ff_type == "indexFF":

                        index = ff.indexFF

                        if index.HasField("ltpc"):
                            ltp = index.ltpc.ltp

                    # OPTION / FUTURE FEED
                    elif ff_type == "marketFF":

                        market = ff.marketFF

                        # LTP
                        if market.HasField("ltpc"):
                            ltp = market.ltpc.ltp

                        # ---------------------
                        # OI / VOLUME
                        # ---------------------

                        if market.HasField("eFeedDetails"):

                            details = market.eFeedDetails

                            oi = details.openInterest
                            oi_change = details.openInterestChange
                            volume = details.volume

                        # ---------------------
                        # BID / ASK
                        # ---------------------

                        if market.HasField("marketLevel"):

                            level = market.marketLevel

                            bid = level.bid
                            ask = level.ask
                            bid_qty = level.bidQty
                            ask_qty = level.askQty

                        # ---------------------
                        # GREEKS
                        # ---------------------

                        if market.HasField("optionGreeks"):

                            greeks = market.optionGreeks

                            iv = greeks.iv
                            delta = greeks.delta
                            theta = greeks.theta
                            gamma = greeks.gamma
                            vega = greeks.vega

                # --------------------------------
                # ALLOW OI UPDATES WITHOUT LTP
                # --------------------------------

                if ltp is None and oi == 0 and volume == 0 and oi_change == 0:
                    continue

                # --------------------------------
                # RESOLVE INSTRUMENT
                # --------------------------------

                if instrument_key.startswith("NSE_INDEX"):

                    if "Nifty Bank" in instrument_key:
                        symbol = "BANKNIFTY"
                    else:
                        symbol = "NIFTY"

                    strike = 0.0
                    right = ""
                    expiry = None
                    segment = "INDEX"

                else:

                    parts = instrument_key.split("|")
                    token = parts[1] if len(parts) > 1 else instrument_key

                    instrument = (
                        registry.get_by_token(token)
                        or registry.get_option_meta(instrument_key)
                    )

                    if not instrument:

                        logger.warning(
                            "COULD NOT RESOLVE INSTRUMENT → %s",
                            instrument_key
                        )
                        continue

                    symbol = instrument.get("symbol")
                    strike = instrument.get("strike", 0.0)
                    right = instrument.get("option_type")
                    expiry = instrument.get("expiry")
                    segment = "FO"

                # --------------------------------
                # NORMALIZED TICK
                # --------------------------------

                tick = {
                    "instrument_key": instrument_key,
                    "symbol": symbol,
                    "type": "option" if segment == "FO" else "index",
                    "data": {
                        "strike": strike,
                        "right": right,
                        "expiry": expiry,
                        "ltp": float(ltp) if ltp is not None else 0.0,
                        "oi": int(oi),
                        "oi_change": int(oi_change),
                        "volume": int(volume),
                        "bid": bid,
                        "ask": ask,
                        "bid_qty": bid_qty,
                        "ask_qty": ask_qty,
                        "iv": iv,
                        "delta": delta,
                        "theta": theta,
                        "gamma": gamma,
                        "vega": vega,
                        "timestamp": now
                    }
                }

                ticks.append(tick)

                # --------------------------------
                # DEBUG LOGGING
                # --------------------------------

                if oi > 0 or volume > 0:
                    logger.debug(
                        "OPTION FEED DETAILS → %s strike=%s oi=%s vol=%s",
                        symbol,
                        strike,
                        oi,
                        volume
                    )

                if segment == "FO":
                    logger.debug(
                        "OPTION TICK → %s strike=%s ltp=%s oi=%s",
                        symbol,
                        strike,
                        ltp,
                        oi
                    )

                if tick_queue:
                    await tick_queue.put(tick)

            except Exception as e:

                logger.error(
                    "FEED PROCESSING ERROR for %s: %s",
                    instrument_key,
                    e,
                    exc_info=True
                )
                continue

    except Exception as e:

        logger.error(
            "PROTOBUF DECODE ERROR: %s",
            e,
            exc_info=True
        )
        return []

    return ticks