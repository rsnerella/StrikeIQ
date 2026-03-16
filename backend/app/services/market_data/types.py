from dataclasses import dataclass
from typing import Dict, Any, Optional
from datetime import datetime
from enum import Enum


class MarketStatus(Enum):
    """Market status enumeration"""
    OPEN = "open"
    CLOSED = "closed"
    NO_DATA = "no_data"
    ERROR = "error"


@dataclass
class MarketData:
    """Market data structure"""
    symbol: str
    last_price: float
    change: float
    change_percent: float
    volume: int
    timestamp: datetime
    bid: Optional[float] = None
    ask: Optional[float] = None
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    previous_close: Optional[float] = None
    market_status: Optional[MarketStatus] = None


@dataclass
class InstrumentInfo:
    """Instrument information"""
    symbol: str
    name: str
    exchange: str
    instrument_type: str
    lot_size: Optional[int] = None
    tick_size: Optional[float] = None
    expiry: Optional[datetime] = None
    strike: Optional[float] = None
    option_type: Optional[str] = None


@dataclass
class AuthRequiredResponse:
    """Response when authentication is required"""
    requires_auth: bool = True
    message: str = "Authentication required"
    auth_url: Optional[str] = None


# Exception classes
class MarketDataError(Exception):
    """Base exception for market data errors"""
    pass


class AuthenticationError(MarketDataError):
    """Authentication related errors"""
    pass


class TokenExpiredError(AuthenticationError):
    """Token has expired"""
    pass


class InstrumentNotFoundError(MarketDataError):
    """Instrument not found error"""
    pass


class APIResponseError(MarketDataError):
    """API response error"""
    pass


class MarketClosedError(MarketDataError):
    """Market is closed error"""
    pass
