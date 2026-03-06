import asyncio

from app.proto.MarketDataFeedV3_pb2 import FeedResponse
from app.services.upstox_protobuf_parser_v3 import decode_protobuf_message


async def run_test():

    response = FeedResponse()

    feed = response.feeds.add()
    feed.key = "NSE_FO|45467"

    market = feed.value.ff.marketFF

    # mock market data
    market.ltpc.ltp = 196.6
    market.eFeedDetails.oi = 1823450
    market.eFeedDetails.vtt = 25341

    message = response.SerializeToString()

    ticks = await decode_protobuf_message(message)

    print("\nPARSED TICKS:")
    print(ticks)

    # -----------------------------
    # VALIDATION
    # -----------------------------

    assert len(ticks) == 1, "Parser returned no ticks"

    tick = ticks[0]

    assert tick["ltp"] == 196.6, "LTP parsing failed"
    assert tick["oi"] == 1823450, "OI parsing failed"
    assert tick["volume"] == 25341, "Volume parsing failed"

    print("\n✅ PROTOBUF PARSER TEST PASSED")


if __name__ == "__main__":
    asyncio.run(run_test())
