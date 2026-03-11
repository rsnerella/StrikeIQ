import logging
import asyncio
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class MarketContextEngine:
    def __init__(self):
        self.market_context: Dict[str, Dict[str, float]] = {}
        self._initialized = False

    async def initialize(self):
        """Fetch previous day close using historical API during startup"""
        if self._initialized:
            return

        try:
            from app.services.market_data.upstox_client import UpstoxClient
            client = UpstoxClient()
            
            # Map of internal symbols to Upstox Instrument Keys
            instruments = {
                "NIFTY": "NSE_INDEX|Nifty 50",
                "BANKNIFTY": "NSE_INDEX|Nifty Bank"
            }
            
            # Use Upstox OHLC quote API to get Previous Day Close
            for symbol, instrument_key in instruments.items():
                try:
                    response = await client._make_request(
                        'get',
                        f"https://api.upstox.com/v2/market-quote/ohlc",
                        params={"instrument_key": instrument_key}
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        if data.get("status") == "success" and "data" in data:
                            instrument_data = data["data"].get(instrument_key, {})
                            ohlc = instrument_data.get("ohlc", {})
                            close_price = ohlc.get("close")
                            open_price = ohlc.get("open")
                            
                            if close_price:
                                self.market_context[symbol] = {
                                    "previous_day_close": float(close_price),
                                    "open_price": float(open_price) if open_price else float(close_price)
                                }
                                logger.info(f"Market Context: {symbol} PDC loaded = {close_price}")
                except Exception as e:
                    logger.error(f"Failed to fetch historical context for {symbol}: {e}")
                    
            self._initialized = True
            
        except Exception as e:
            logger.error(f"Failed to initialize MarketContextEngine: {e}")

    def get_previous_day_close(self, symbol: str) -> Optional[float]:
        context = self.market_context.get(symbol)
        return context["previous_day_close"] if context else None

    def calculate_percent_change(self, symbol: str, spot: float) -> Optional[float]:
        pdc = self.get_previous_day_close(symbol)
        if pdc and pdc > 0:
            return ((spot - pdc) / pdc) * 100
        return None

    def detect_gap(self, symbol: str) -> Optional[float]:
        """Calculates gap up/down as a percentage from PDC"""
        context = self.market_context.get(symbol)
        if not context:
            return None
            
        pdc = context.get("previous_day_close")
        open_price = context.get("open_price")
        
        if pdc and open_price and pdc > 0 and open_price > 0:
            return ((open_price - pdc) / pdc) * 100
        return 0.0

market_context_engine = MarketContextEngine()
