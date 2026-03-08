"""
structure_engine.py — StrikeIQ Market Structure Analysis

Identifies:
  • Swing Highs / Swing Lows from candles
  • Higher Highs (HH), Higher Lows (HL)
  • Lower Highs (LH), Lower Lows (LL)
  • Break of Structure (BOS)
  • Market Structure Shift (MSS)

Pure functions — no I/O, no side effects. Safe for hot-path use.
"""

import logging
from typing import Any, Dict, List, Optional
from .candle_builder import Candle

logger = logging.getLogger(__name__)

# ── Swing point detection ──────────────────────────────────────────────────────

def find_swing_highs(candles: List[Candle], lookback: int = 3) -> List[Dict]:
    """
    Return list of swing high candles.
    A candle is a swing high if its high is the highest within lookback bars on each side.
    """
    if len(candles) < 2 * lookback + 1:
        return []

    swings = []
    for i in range(lookback, len(candles) - lookback):
        pivot = candles[i]
        left  = candles[i - lookback : i]
        right = candles[i + 1 : i + lookback + 1]
        if all(pivot.high >= c.high for c in left) and all(pivot.high >= c.high for c in right):
            swings.append({"index": i, "price": pivot.high, "ts": pivot.ts_open, "type": "HIGH"})
    return swings


def find_swing_lows(candles: List[Candle], lookback: int = 3) -> List[Dict]:
    """Return list of swing low candles."""
    if len(candles) < 2 * lookback + 1:
        return []

    swings = []
    for i in range(lookback, len(candles) - lookback):
        pivot = candles[i]
        left  = candles[i - lookback : i]
        right = candles[i + 1 : i + lookback + 1]
        if all(pivot.low <= c.low for c in left) and all(pivot.low <= c.low for c in right):
            swings.append({"index": i, "price": pivot.low, "ts": pivot.ts_open, "type": "LOW"})
    return swings


# ── Structure classification ───────────────────────────────────────────────────

def classify_structure(
    swing_highs: List[Dict],
    swing_lows: List[Dict],
) -> Dict[str, Any]:
    """
    Compare last 2 swing highs and last 2 swing lows to classify market structure.

    Returns:
        {
            "trend":   "BULLISH" | "BEARISH" | "CHOPPY" | "INSUFFICIENT_DATA",
            "pattern": "HH_HL" | "LH_LL" | "HH_LL" | "LH_HL" | "CHOPPY",
            "hh": bool, "hl": bool, "lh": bool, "ll": bool,
            "last_high": float, "last_low": float,
        }
    """
    if len(swing_highs) < 2 or len(swing_lows) < 2:
        return {
            "trend": "INSUFFICIENT_DATA",
            "pattern": "INSUFFICIENT_DATA",
            "hh": False, "hl": False, "lh": False, "ll": False,
            "last_high": 0.0, "last_low": 0.0,
        }

    h1, h2 = swing_highs[-2]["price"], swing_highs[-1]["price"]
    l1, l2 = swing_lows[-2]["price"],  swing_lows[-1]["price"]

    hh = h2 > h1
    hl = l2 > l1
    lh = h2 < h1
    ll = l2 < l1

    if hh and hl:
        trend, pattern = "BULLISH", "HH_HL"
    elif lh and ll:
        trend, pattern = "BEARISH", "LH_LL"
    elif hh and ll:
        trend, pattern = "CHOPPY", "HH_LL"
    elif lh and hl:
        trend, pattern = "CHOPPY", "LH_HL"
    else:
        trend, pattern = "CHOPPY", "CHOPPY"

    return {
        "trend": trend,
        "pattern": pattern,
        "hh": hh, "hl": hl, "lh": lh, "ll": ll,
        "last_high": round(h2, 2),
        "last_low":  round(l2, 2),
        "prev_high": round(h1, 2),
        "prev_low":  round(l1, 2),
    }


# ── Break of Structure detection ───────────────────────────────────────────────

def detect_bos(
    candles: List[Candle],
    swing_highs: List[Dict],
    swing_lows: List[Dict],
    current_price: float,
) -> Dict[str, Any]:
    """
    Break of Structure: price closes beyond the most recent swing high/low.

    Returns:
        { "detected": bool, "direction": "BULLISH"|"BEARISH"|"NONE",
          "broken_level": float, "strength": float }
    """
    result = {"detected": False, "direction": "NONE", "broken_level": 0.0, "strength": 0.0}

    if not swing_highs or not swing_lows or current_price <= 0:
        return result

    last_sh = swing_highs[-1]["price"]
    last_sl = swing_lows[-1]["price"]

    if current_price > last_sh:
        strength = round((current_price - last_sh) / max(last_sh, 1) * 100, 2)
        return {"detected": True, "direction": "BULLISH", "broken_level": round(last_sh, 2), "strength": strength}

    if current_price < last_sl:
        strength = round((last_sl - current_price) / max(last_sl, 1) * 100, 2)
        return {"detected": True, "direction": "BEARISH", "broken_level": round(last_sl, 2), "strength": strength}

    return result


# ── Market Structure Shift ─────────────────────────────────────────────────────

def detect_mss(
    prev_structure: Optional[Dict],
    current_structure: Dict,
) -> Dict[str, Any]:
    """
    Market Structure Shift: when trend changes from previous to current.
    """
    if not prev_structure:
        return {"detected": False, "from": "UNKNOWN", "to": current_structure.get("trend", "UNKNOWN")}

    prev_trend = prev_structure.get("trend", "UNKNOWN")
    curr_trend = current_structure.get("trend", "UNKNOWN")

    if prev_trend == curr_trend or "INSUFFICIENT" in prev_trend or "INSUFFICIENT" in curr_trend:
        return {"detected": False, "from": prev_trend, "to": curr_trend}

    if prev_trend == "BULLISH" and curr_trend == "BEARISH":
        return {"detected": True, "from": prev_trend, "to": curr_trend, "significance": "MAJOR"}
    if prev_trend == "BEARISH" and curr_trend == "BULLISH":
        return {"detected": True, "from": prev_trend, "to": curr_trend, "significance": "MAJOR"}
    if "CHOPPY" in (prev_trend, curr_trend):
        return {"detected": True, "from": prev_trend, "to": curr_trend, "significance": "MINOR"}

    return {"detected": False, "from": prev_trend, "to": curr_trend}


# ── Main analyzer ──────────────────────────────────────────────────────────────

class StructureEngine:
    """
    Stateful market structure analyzer.
    Maintains previous structure for MSS detection.
    """

    def __init__(self, lookback: int = 3):
        self.lookback = lookback
        self._prev_structure: Dict[str, Optional[Dict]] = {}  # keyed by symbol

    def analyze(self, symbol: str, candles: List[Candle], current_price: float) -> Dict[str, Any]:
        """
        Full structure analysis for one symbol.

        Args:
            symbol:        e.g. "NIFTY"
            candles:       List of completed Candle objects (1m recommended)
            current_price: Latest spot price

        Returns:
            Structured analysis dict consumed by chart_signal_engine.
        """
        try:
            if len(candles) < 10:
                return {"symbol": symbol, "trend": "INSUFFICIENT_DATA", "bos": {"detected": False}, "mss": {"detected": False}}

            sh = find_swing_highs(candles, self.lookback)
            sl = find_swing_lows(candles, self.lookback)

            structure = classify_structure(sh, sl)
            bos       = detect_bos(candles, sh, sl, current_price)
            mss       = detect_mss(self._prev_structure.get(symbol), structure)

            self._prev_structure[symbol] = structure

            return {
                "symbol":     symbol,
                "trend":      structure["trend"],
                "pattern":    structure["pattern"],
                "hh": structure["hh"], "hl": structure["hl"],
                "lh": structure["lh"], "ll": structure["ll"],
                "last_high":  structure.get("last_high", 0),
                "last_low":   structure.get("last_low",  0),
                "swing_highs": [s["price"] for s in sh[-3:]],
                "swing_lows":  [s["price"] for s in sl[-3:]],
                "bos":         bos,
                "mss":         mss,
            }

        except Exception as e:
            logger.error("StructureEngine.analyze error for %s: %s", symbol, e)
            return {"symbol": symbol, "trend": "ERROR", "bos": {"detected": False}, "mss": {"detected": False}}


# ── Global singleton ───────────────────────────────────────────────────────────
structure_engine = StructureEngine()
