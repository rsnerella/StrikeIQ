import logging
from fastapi import APIRouter
from app.services.websocket_market_feed import get_market_feed
from app.services.option_chain_builder import option_chain_builder

router = APIRouter(prefix="/api/v1/diagnostics", tags=["Diagnostics"])
logger = logging.getLogger(__name__)


@router.get("/pipeline-status")
async def get_pipeline_status():
    """
    Real-time pipeline health check.
    Use this endpoint to verify data flows correctly after fixes.

    Expected healthy response (Upstox Plus active, full_d30 mode):
      has_ltp: true
      has_oi: true
      has_greeks: true
      message: Full data flowing

    If has_ltp=true but has_oi=false, the protobuf parser is still
    reading indexFF instead of marketFF. Check subscription mode.
    """
    feed = get_market_feed()

    pipeline_info = {
        "ws_connected":     False,
        "feeds_received":   0,
        "ticks_processed":  0,
        "dropped_ticks":    0,
        "queue_size":       0,
        "active_symbol":    None,
        "active_expiry":    None,
        "subscribed_count": 0,
        "subscription_mode": "full_d30",
    }

    if feed:
        pipeline_info.update({
            "ws_connected":     feed._is_connected,
            "feeds_received":   feed.feeds_received_count,
            "ticks_processed":  feed.processed_ticks,
            "dropped_ticks":    feed.dropped_ticks,
            "queue_size":       feed._message_queue.qsize(),
            "active_symbol":    feed.active_symbol,
            "active_expiry":    feed.active_expiry,
            "subscribed_count": len(feed.subscribed_instruments),
        })

    # Sample the chain to assess data quality
    data_quality = {
        "has_ltp":     False,
        "has_oi":      False,
        "has_greeks":  False,
        "has_bid_ask": False,
        "total_strikes_with_ltp":    0,
        "total_strikes_with_oi":     0,
        "total_strikes_with_greeks": 0,
        "message": "",
    }

    chain_sample = {}

    try:
        symbol = (feed.active_symbol if feed and feed.active_symbol else "NIFTY")
        chain  = option_chain_builder.chains.get(symbol, {})

        if chain:
            for strike, sides in chain.items():
                for side, opt_data in sides.items():
                    ltp_val   = opt_data.ltp
                    oi_val    = opt_data.oi
                    delta_val = opt_data.delta
                    bid_val   = opt_data.bid

                    if ltp_val   > 0:  data_quality["total_strikes_with_ltp"]    += 1
                    if oi_val    > 0:  data_quality["total_strikes_with_oi"]     += 1
                    if delta_val != 0: data_quality["total_strikes_with_greeks"] += 1
                    if bid_val   > 0:  data_quality["has_bid_ask"] = True

            data_quality["has_ltp"]     = data_quality["total_strikes_with_ltp"]    > 0
            data_quality["has_oi"]      = data_quality["total_strikes_with_oi"]     > 0
            data_quality["has_greeks"]  = data_quality["total_strikes_with_greeks"] > 0

            # Sample 3 strikes for response
            for strike, sides in list(chain.items())[:3]:
                for side, opt_data in sides.items():
                    chain_sample[f"{strike}_{side}"] = {
                        "ltp":   opt_data.ltp,
                        "oi":    opt_data.oi,
                        "iv":    opt_data.iv,
                        "delta": opt_data.delta,
                        "bid":   opt_data.bid,
                        "ask":   opt_data.ask,
                    }

        # Determine message
        if data_quality["has_ltp"] and data_quality["has_oi"] and data_quality["has_greeks"]:
            data_quality["message"] = (
                "✅ FULL DATA FLOWING — LTP + OI + Greeks all active. "
                "Upstox Plus + full_d30 working correctly."
            )
        elif data_quality["has_ltp"] and not data_quality["has_oi"]:
            data_quality["message"] = (
                "⚠️ LTP flowing but OI=0. Parser may still be reading indexFF "
                "instead of marketFF. Verify subscription mode is full_d30 "
                "and protobuf parser fix (Prompt 1) was applied correctly."
            )
        elif not data_quality["has_ltp"]:
            data_quality["message"] = (
                "⏳ No data yet. WebSocket may still be connecting or "
                "no ticks received. Check ws_connected and feeds_received."
            )
        else:
            data_quality["message"] = "⚠️ Partial data. Check logs for errors."

    except Exception as e:
        data_quality["message"] = f"Chain read error: {str(e)}"
        logger.error("Diagnostics chain read failed: %s", e)

    return {
        "pipeline":     pipeline_info,
        "data_quality": data_quality,
        "chain_sample": chain_sample,
    }
