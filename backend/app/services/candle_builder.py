"""
candle_builder.py — StrikeIQ Chart Intelligence Layer

Converts real-time price ticks into OHLC candles.

Supports:
  • 1-minute candles
  • 5-minute candles

Design:
  - All state held in bounded deque buffers (maxlen=200 per timeframe)
  - O(1) tick ingestion — no list scans
  - Thread-safe: sync-only writes (called from asyncio single-threaded context)
  - Completed candles are returned to callers (e.g. analytics_broadcaster, chart_signal_engine)
"""

import logging
import time
from collections import deque
from typing import Dict, List, Optional, Tuple, Any

logger = logging.getLogger(__name__)

# ── OHLC Candle structure ──────────────────────────────────────────────────────

class Candle:
    __slots__ = ("open", "high", "low", "close", "volume", "ts_open", "ts_close", "interval")

    def __init__(self, price: float, volume: float, ts: float, interval: int):
        self.open: float = price
        self.high: float = price
        self.low: float = price
        self.close: float = price
        self.volume: float = volume
        self.ts_open: float = ts          # epoch seconds of candle open
        self.ts_close: float = ts + interval  # expected close epoch
        self.interval: int = interval     # candle size in seconds

    def update(self, price: float, volume: float) -> None:
        if price > self.high:
            self.high = price
        if price < self.low:
            self.low = price
        self.close = price
        self.volume += volume

    def to_dict(self) -> Dict[str, Any]:
        return {
            "open":     round(self.open, 2),
            "high":     round(self.high, 2),
            "low":      round(self.low, 2),
            "close":    round(self.close, 2),
            "volume":   round(self.volume, 0),
            "ts":       int(self.ts_open),
            "interval": self.interval,
        }

    def body_size(self) -> float:
        return abs(self.close - self.open)

    def range_size(self) -> float:
        return self.high - self.low

    def is_bullish(self) -> bool:
        return self.close >= self.open

    def is_bearish(self) -> bool:
        return self.close < self.open


# ── Per-symbol candle state ────────────────────────────────────────────────────

class _CandleState:
    """Holds the current forming candle + completed history for one (symbol, interval)."""

    MAX_HISTORY = 200  # deque cap

    def __init__(self, interval: int):
        self.interval = interval
        self.current: Optional[Candle] = None
        self.history: deque = deque(maxlen=self.MAX_HISTORY)

    def push_tick(self, price: float, volume: float, ts: float) -> Optional[Candle]:
        """
        Feed one tick. Returns the completed Candle if a new interval started,
        otherwise returns None.
        """
        if self.current is None:
            # Start fresh
            self.current = Candle(price, volume, self._align(ts), self.interval)
            return None

        # Check if this tick belongs to the current candle
        if ts < self.current.ts_close:
            self.current.update(price, volume)
            return None

        # Candle closed — move to history
        completed = self.current
        self.history.append(completed)

        # Start new candle aligned to interval boundary
        aligned_ts = self._align(ts)
        self.current = Candle(price, volume, aligned_ts, self.interval)

        return completed

    def get_history(self, n: int = 50) -> List[Candle]:
        """Return last N completed candles (oldest-first)."""
        hist = list(self.history)
        return hist[-n:] if len(hist) > n else hist

    def _align(self, ts: float) -> float:
        """Floor timestamp to interval boundary."""
        return float(int(ts) // self.interval * self.interval)


# ── CandleBuilder singleton ────────────────────────────────────────────────────

INTERVALS = {
    "1m":  60,
    "5m":  300,
}


class CandleBuilder:
    """
    Receives index ticks and maintains OHLC candles for configured intervals.

    Usage:
        candle_builder.push_tick("NIFTY", price=22450.0, volume=1500.0)
        candles_1m = candle_builder.get_candles("NIFTY", "1m", n=50)
    """

    def __init__(self):
        # { symbol: { interval_key: _CandleState } }
        self._states: Dict[str, Dict[str, _CandleState]] = {}
        # Subscribers: callables notified on candle close
        self._on_close_callbacks: List = []

    def push_tick(
        self,
        symbol: str,
        price: float,
        volume: float = 0.0,
        ts: Optional[float] = None,
    ) -> None:
        """
        O(1) tick ingestion. Call this on every index tick.
        Fires on_close callbacks when a candle completes.
        """
        if price <= 0:
            return

        ts = ts or time.time()

        if symbol not in self._states:
            self._states[symbol] = {k: _CandleState(v) for k, v in INTERVALS.items()}

        for key, state in self._states[symbol].items():
            completed = state.push_tick(price, volume, ts)
            if completed:
                logger.debug(
                    "CANDLE CLOSED [%s %s] O=%.2f H=%.2f L=%.2f C=%.2f",
                    symbol, key, completed.open, completed.high, completed.low, completed.close
                )
                for cb in self._on_close_callbacks:
                    try:
                        cb(symbol, key, completed)
                    except Exception as e:
                        logger.error("Candle close callback error: %s", e)

    def get_candles(self, symbol: str, interval: str = "1m", n: int = 50) -> List[Candle]:
        """Return last N completed candles for symbol+interval."""
        try:
            return self._states[symbol][interval].get_history(n)
        except KeyError:
            return []

    def get_candles_as_dicts(self, symbol: str, interval: str = "1m", n: int = 50) -> List[Dict]:
        return [c.to_dict() for c in self.get_candles(symbol, interval, n)]

    def get_current_candle(self, symbol: str, interval: str = "1m") -> Optional[Dict]:
        """Return the currently forming (incomplete) candle as dict."""
        try:
            c = self._states[symbol][interval].current
            return c.to_dict() if c else None
        except KeyError:
            return None

    def register_on_close(self, callback) -> None:
        """Register a callback(symbol, interval_key, Candle) called on candle close."""
        self._on_close_callbacks.append(callback)


# ── Global singleton ───────────────────────────────────────────────────────────
candle_builder = CandleBuilder()
