import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from .types import MarketData, MarketStatus, APIResponseError

logger = logging.getLogger(__name__)

class DashboardFormatter:
    """Service for formatting market data responses"""
    
    @staticmethod
    def format_market_data(
        symbol: str,
        api_response: Dict[str, Any],
        market_status: MarketStatus,
        timestamp: Optional[datetime] = None
    ) -> MarketData:
        """Format API response into standardized MarketData"""
        
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        
        try:
            # Extract data from API response according to Upstox schema
            data_field = api_response.get("data", {})
            
            if not isinstance(data_field, dict):
                raise APIResponseError(f"Expected data to be dict, got {type(data_field)}")
            
            # Extract LTP (last traded price)
            spot_price = None
            if "last_price" in data_field:
                spot_price = float(data_field["last_price"])
            elif "ltp" in data_field:
                spot_price = float(data_field["ltp"])
            
            # Extract previous close
            previous_close = None
            if "previous_close" in data_field:
                previous_close = float(data_field["previous_close"])
            
            # Calculate change and change percent
            change = None
            change_percent = None
            
            if spot_price is not None and previous_close is not None and previous_close > 0:
                change = spot_price - previous_close
                change_percent = (change / previous_close) * 100
            
            # Extract exchange timestamp if available
            exchange_timestamp = None
            if "timestamp" in data_field:
                try:
                    # Assuming timestamp is in milliseconds since epoch
                    exchange_timestamp = datetime.fromtimestamp(
                        data_field["timestamp"] / 1000,
                        tz=timezone.utc
                    )
                except (ValueError, TypeError):
                    logger.warning(f"Invalid timestamp in API response: {data_field.get('timestamp')}")
            
            return MarketData(
                symbol=symbol,
                last_price=spot_price,
                previous_close=previous_close,
                change=change,
                change_percent=change_percent,
                volume=0,  # Volume not available in API response
                timestamp=timestamp,
                market_status=market_status,
                exchange_timestamp=exchange_timestamp
            )
            
        except (ValueError, TypeError) as e:
            logger.error(f"Error parsing API response for {symbol}: {e}")
            raise APIResponseError(f"Invalid data format: {e}")
        except Exception as e:
            logger.error(f"Unexpected error formatting data for {symbol}: {e}")
            raise APIResponseError(f"Formatting error: {e}")
    
    @staticmethod
    def format_error_response(
        symbol: str,
        error: Exception,
        market_status: MarketStatus = MarketStatus.ERROR
    ) -> MarketData:
        """Format error response"""
        
        return MarketData(
            symbol=symbol,
            last_price=None,
            change=0,
            change_percent=0,
            volume=0,
            timestamp=datetime.now(timezone.utc),
            market_status=market_status
        )
    
    @staticmethod
    def format_market_closed_response(symbol: str) -> MarketData:
        """Format market closed response"""
        
        return MarketData(
            symbol=symbol,
            last_price=None,
            change=0,
            change_percent=0,
            volume=0,
            timestamp=datetime.now(timezone.utc),
            market_status=MarketStatus.CLOSED
        )
    
    @staticmethod
    def to_dict(market_data: MarketData) -> Dict[str, Any]:
        """Convert MarketData to dictionary for API response"""
        
        result = {
            "symbol": market_data.symbol,
            "last_price": market_data.last_price,
            "previous_close": market_data.previous_close,
            "change": market_data.change,
            "change_percent": market_data.change_percent,
            "timestamp": market_data.timestamp.isoformat(),
            "market_status": str(market_data.market_status)
        }
        
        if market_data.exchange_timestamp:
            result["exchange_timestamp"] = market_data.exchange_timestamp.isoformat()
        
        return result
