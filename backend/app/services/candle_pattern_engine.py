"""
candle_pattern_engine.py — StrikeIQ Candlestick Pattern Recognition

Detects:
  • Bullish Engulfing
  • Bearish Engulfing
  • Pin Bar (Hammer / Shooting Star)
  • Inside Bar
  • Morning Star
  • Evening Star
  • Doji

All functions are pure and stateless — safe for O(1) hot path.
"""

import logging
from typing import Any, Dict, List, Optional
from .candle_builder import Candle

logger = logging.getLogger(__name__)


# ── Pattern helpers ────────────────────────────────────────────────────────────

def _upper_shadow(c: Candle) -> float:
    return c.high - max(c.open, c.close)

def _lower_shadow(c: Candle) -> float:
    return min(c.open, c.close) - c.low

def _is_doji(c: Candle) -> bool:
    return c.body_size() <= c.range_size() * 0.1 and c.range_size() > 0

def _result(name: str, direction: str, strength: float, note: str = "") -> Dict[str, Any]:
    return {
        "pattern":   name,
        "direction": direction,          # BULLISH | BEARISH | NEUTRAL
        "strength":  round(min(100.0, strength), 1),
        "signal":    "BUY" if direction == "BULLISH" else "SELL" if direction == "BEARISH" else "WAIT",
        "note":      note or name,
    }


# ── Two-candle patterns ────────────────────────────────────────────────────────

def _bullish_engulfing(prev: Candle, curr: Candle) -> Optional[Dict]:
    """Bullish engulfing: curr is bullish and fully engulfs prev bearish body."""
    if prev.is_bearish() and curr.is_bullish():
        if curr.open <= prev.close and curr.close >= prev.open:
            strength = min(100, curr.body_size() / max(prev.body_size(), 0.01) * 50)
            return _result("Bullish Engulfing", "BULLISH", strength)
    return None


def _bearish_engulfing(prev: Candle, curr: Candle) -> Optional[Dict]:
    """Bearish engulfing: curr is bearish and fully engulfs prev bullish body."""
    if prev.is_bullish() and curr.is_bearish():
        if curr.open >= prev.close and curr.close <= prev.open:
            strength = min(100, curr.body_size() / max(prev.body_size(), 0.01) * 50)
            return _result("Bearish Engulfing", "BEARISH", strength)
    return None


def _inside_bar(prev: Candle, curr: Candle) -> Optional[Dict]:
    """Inside bar: curr is completely inside prev's high-low range."""
    if curr.high < prev.high and curr.low > prev.low:
        direction = "BULLISH" if prev.is_bullish() else "BEARISH"
        return _result("Inside Bar", direction, 55, "Inside bar — potential breakout setup")
    return None


# ── Single-candle patterns ─────────────────────────────────────────────────────

def _pin_bar(c: Candle) -> Optional[Dict]:
    """
    Pin bar (Hammer / Shooting Star).
    Hammer:        long lower shadow, small body at top
    Shooting Star: long upper shadow, small body at bottom
    """
    body = c.body_size()
    rng  = c.range_size()
    if rng == 0:
        return None

    body_ratio = body / rng

    # Hammer: lower shadow ≥ 2× body, small upper shadow
    lower = _lower_shadow(c)
    upper = _upper_shadow(c)
    if lower >= body * 2 and upper <= body * 0.5 and body_ratio < 0.4:
        return _result("Hammer (Pin Bar)", "BULLISH", 70, "Bullish pin bar — rejection of lows")

    # Shooting star: upper shadow ≥ 2× body, small lower shadow
    if upper >= body * 2 and lower <= body * 0.5 and body_ratio < 0.4:
        return _result("Shooting Star (Pin Bar)", "BEARISH", 70, "Bearish pin bar — rejection of highs")

    return None


def _doji(c: Candle) -> Optional[Dict]:
    if _is_doji(c):
        return _result("Doji", "NEUTRAL", 40, "Market indecision — wait for confirmation")
    return None


# ── Three-candle patterns ─────────────────────────────────────────────────────

def _morning_star(a: Candle, b: Candle, c: Candle) -> Optional[Dict]:
    """
    Morning Star: bearish candle, small-body middle, bullish candle.
    The third candle must close above the midpoint of the first candle.
    """
    if (a.is_bearish() and b.body_size() < a.body_size() * 0.5 and
            c.is_bullish() and c.close > (a.open + a.close) / 2):
        return _result("Morning Star", "BULLISH", 80, "Morning star — bullish reversal")
    return None


def _evening_star(a: Candle, b: Candle, c: Candle) -> Optional[Dict]:
    """
    Evening Star: bullish candle, small-body middle, bearish candle.
    The third candle must close below the midpoint of the first candle.
    """
    if (a.is_bullish() and b.body_size() < a.body_size() * 0.5 and
            c.is_bearish() and c.close < (a.open + a.close) / 2):
        return _result("Evening Star", "BEARISH", 80, "Evening star — bearish reversal")
    return None


# ── Main detector ─────────────────────────────────────────────────────────────

def detect_candle_patterns(candles: List[Candle]) -> List[Dict[str, Any]]:
    """
    Run all pattern detectors on the last few candles.

    Args:
        candles: List of completed Candle objects (at least 3 recommended)

    Returns:
        List of detected pattern dicts, most recent first.
    """
    if not candles:
        return []

    patterns = []

    # Single-candle on last bar
    last = candles[-1]
    p = _pin_bar(last)
    if p:
        patterns.append(p)
    d = _doji(last)
    if d:
        patterns.append(d)

    # Two-candle on last two
    if len(candles) >= 2:
        prev = candles[-2]
        be = _bullish_engulfing(prev, last)
        if be:
            patterns.append(be)
        beare = _bearish_engulfing(prev, last)
        if beare:
            patterns.append(beare)
        ib = _inside_bar(prev, last)
        if ib:
            patterns.append(ib)

    # Three-candle on last three
    if len(candles) >= 3:
        a, b, c = candles[-3], candles[-2], candles[-1]
        ms = _morning_star(a, b, c)
        if ms:
            patterns.append(ms)
        es = _evening_star(a, b, c)
        if es:
            patterns.append(es)

    return patterns


class CandlePatternEngine:
    """
    Wrapper that runs pattern detection and returns the strongest signal.
    Called by chart_signal_engine each analytics cycle.
    """

    def analyze(self, symbol: str, candles: List[Candle]) -> Dict[str, Any]:
        try:
            patterns = detect_candle_patterns(candles)

            if not patterns:
                return {"symbol": symbol, "patterns": [], "primary": None}

            # Pick strongest by strength
            primary = max(patterns, key=lambda p: p["strength"])

            return {
                "symbol":   symbol,
                "patterns": patterns,
                "primary":  primary,
            }

        except Exception as e:
            logger.error("CandlePatternEngine.analyze error for %s: %s", symbol, e)
            return {"symbol": symbol, "patterns": [], "primary": None}


# ── Global singleton ───────────────────────────────────────────────────────────
candle_pattern_engine = CandlePatternEngine()
