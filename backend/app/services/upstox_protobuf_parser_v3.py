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

                # DEFAULT VALUES
                # Never rely on truthiness for protobuf numeric fields.
                # Protobuf int/float always exist and default to 0/0.0.
                # Zero is a valid real value — do not treat it as missing.
                ltp       = None
                oi        = 0
                oi_change = 0
                volume    = 0
                bid       = 0.0
                ask       = 0.0
                bid_qty   = 0
                ask_qty   = 0
                iv        = 0.0
                delta     = 0.0
                theta     = 0.0
                gamma     = 0.0
                vega      = 0.0

                data_type = feed.WhichOneof("data")

                # LTPC ONLY MODE
                if data_type == "ltpc":
                    if feed.HasField("ltpc"):
                        ltp = feed.ltpc.ltp

                # FULL FEED WRAPPER (ff)
                elif data_type == "ff":

                    ff      = feed.ff
                    ff_type = ff.WhichOneof("data")

                    # INDEX INSTRUMENTS (NSE_INDEX|Nifty 50 etc)
                    # indexFF only carries ltpc — no OI or Greeks
                    if ff_type == "indexFF":
                        index = ff.indexFF
                        if index.HasField("ltpc"):
                            ltp = index.ltpc.ltp

                    # OPTION AND FUTURE INSTRUMENTS (NSE_FO|...)
                    # marketFF is only present with Upstox Plus + full_d30 mode
                    # Contains: ltpc, marketLevel (depth), optionGreeks, marketOHLC,
                    #           oi, iv, vtt, atp, tbq, tsq
                    elif ff_type == "marketFF":

                        market = ff.marketFF

                        # LTP
                        if market.HasField("ltpc"):
                            ltp = market.ltpc.ltp

                        # OI
                        # FIX: use int(market.oi) directly — never use truthiness.
                        # market.oi = 0 is a valid value at market open or
                        # for illiquid strikes. "if market.oi" would drop it.
                        try:
                            oi = int(market.oi)
                        except Exception:
                            oi = 0

                        # OI fallback via eFeedDetails
                        if oi == 0:
                            try:
                                if market.HasField("eFeedDetails"):
                                    details   = market.eFeedDetails
                                    oi        = int(details.openInterest)
                                    oi_change = int(details.openInterestChange)
                            except Exception:
                                pass

                        # VOLUME
                        # FIX: use market.vtt (volume traded today — integer field).
                        # DO NOT use marketOHLC[0].vol — that is a STRING ("196455805")
                        # on the daily candle object and causes int conversion errors.
                        try:
                            volume = int(market.vtt) if market.vtt else 0
                        except Exception:
                            volume = 0

                        # Volume fallback via daily OHLC if vtt missing
                        if volume == 0:
                            try:
                                if market.HasField("marketOHLC"):
                                    for candle in market.marketOHLC.ohlc:
                                        if candle.interval == "1d":
                                            raw_vol = candle.vol
                                            volume  = int(raw_vol) if raw_vol else 0
                                            break
                            except Exception:
                                pass

                        # BID / ASK from first level of market depth
                        try:
                            if market.HasField("marketLevel"):
                                quotes = list(market.marketLevel.bidAskQuote)
                                if quotes:
                                    q       = quotes[0]
                                    bid     = float(q.bidP)
                                    ask     = float(q.askP)
                                    # bidQ and askQ are STRING fields in V3 proto
                                    bid_qty = int(q.bidQ) if q.bidQ else 0
                                    ask_qty = int(q.askQ) if q.askQ else 0
                        except Exception:
                            pass

                        # GREEKS
                        # FIX: ALWAYS use HasField + read from optionGreeks sub-message.
                        # NEVER use:
                        #   "if market.delta" — delta=0.5 is truthy but delta=0.0 is falsy
                        #   "if market.iv and market.delta" — same problem
                        #   "elif market.HasField('optionGreeks')" after hasattr checks
                        #     — the elif never fires because hasattr is always True
                        #     on protobuf message objects.
                        # The correct pattern is HasField on the sub-message directly.
                        try:
                            if market.HasField("optionGreeks"):
                                greeks = market.optionGreeks
                                iv     = float(greeks.iv)
                                delta  = float(greeks.delta)
                                theta  = float(greeks.theta)
                                gamma  = float(greeks.gamma)
                                vega   = float(greeks.vega)
                        except Exception:
                            pass

                        # IV top-level fallback
                        # Some proto versions also expose iv directly on marketFF
                        if iv == 0.0:
                            try:
                                raw_iv = market.iv
                                if raw_iv and raw_iv > 0:
                                    iv = float(raw_iv)
                            except Exception:
                                pass

                # SKIP ticks with absolutely no useful data
                # Allow OI-only ticks (ltp=None but oi>0) — needed for PCR
                if ltp is None and oi == 0 and volume == 0 and oi_change == 0:
                    continue

                # RESOLVE INSTRUMENT METADATA
                if instrument_key.startswith("NSE_INDEX"):

                    if "Nifty Bank" in instrument_key:
                        symbol = "BANKNIFTY"
                    elif "Nifty Fin" in instrument_key:
                        symbol = "FINNIFTY"
                    elif "MIDCPNIFTY" in instrument_key:
                        symbol = "MIDCPNIFTY"
                    else:
                        symbol = "NIFTY"

                    strike  = 0.0
                    right   = ""
                    expiry  = None
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

                    symbol  = instrument.get("symbol")
                    strike  = instrument.get("strike", 0.0)
                    right   = instrument.get("option_type")
                    expiry  = instrument.get("expiry")
                    segment = "FO"

                # BUILD NORMALIZED TICK
                tick = {
                    "instrument_key": instrument_key,
                    "symbol":         symbol,
                    "type":           "option" if segment == "FO" else "index",
                    "data": {
                        "strike":    strike,
                        "right":     right,
                        "expiry":    expiry,
                        "ltp":       float(ltp) if ltp is not None else 0.0,
                        "oi":        int(oi),
                        "oi_change": int(oi_change),
                        "volume":    int(volume),
                        "bid":       float(bid),
                        "ask":       float(ask),
                        "bid_qty":   int(bid_qty),
                        "ask_qty":   int(ask_qty),
                        "iv":        float(iv),
                        "delta":     float(delta),
                        "theta":     float(theta),
                        "gamma":     float(gamma),
                        "vega":      float(vega),
                        "timestamp": now,
                    }
                }

                ticks.append(tick)

                # STRUCTURED DEBUG LOG
                if segment == "FO":
                    logger.info(
                        "PARSED OPTION TICK → %s %s strike=%s "
                        "ltp=%.2f oi=%d vol=%d bid=%.2f ask=%.2f "
                        "iv=%.4f delta=%.4f gamma=%.6f theta=%.4f vega=%.4f",
                        symbol, right, strike,
                        float(ltp) if ltp is not None else 0.0,
                        oi, volume, bid, ask,
                        iv, delta, gamma, theta, vega
                    )
                else:
                    logger.debug(
                        "PARSED INDEX TICK → %s ltp=%.2f",
                        symbol,
                        float(ltp) if ltp is not None else 0.0
                    )

                if tick_queue:
                    await tick_queue.put(tick)

            except Exception as e:
                logger.error(
                    "FEED PROCESSING ERROR for %s: %s",
                    instrument_key, e,
                    exc_info=True
                )
                continue

    except Exception as e:
        logger.error(
            "PROTOBUF DECODE ERROR: %s", e,
            exc_info=True
        )
        return []

    return ticks