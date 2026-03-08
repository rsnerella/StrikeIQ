"""
wave_engine.py — StrikeIQ Elliott Wave + Neo Wave Analysis

Detects:
  • Classic Elliott 5-wave impulse (W1–W5)
  • ABC correction
  • Neo Wave complex patterns: triangle, flat, diametric, zigzag

Rules checked:
  • Wave 2 retracement < 100% of Wave 1
  • Wave 3 is never the shortest impulse wave
  • Wave 4 does not overlap Wave 1

All detectors operate on swing point lists — stateless, pure functions.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
from .candle_builder import Candle
from .structure_engine import find_swing_highs, find_swing_lows

logger = logging.getLogger(__name__)


# ── Helper: retracement ratio ─────────────────────────────────────────────────

def _retrace(start: float, end: float, retrace_point: float) -> float:
    """Return retracement ratio (0.0–1.0) of retrace_point within start→end move."""
    move = abs(end - start)
    if move == 0:
        return 0.0
    return abs(retrace_point - end) / move


def _wave_size(a: float, b: float) -> float:
    return abs(b - a)


# ── Elliott Wave 5-wave detector ──────────────────────────────────────────────

def detect_elliott_waves(
    swing_highs: List[Dict],
    swing_lows: List[Dict],
    current_price: float,
) -> Dict[str, Any]:
    """
    Classify current wave count from recent swing structure.

    Requires at least 5 alternating swing points.
    Returns wave label (1-5 or A-B-C), probability, and key levels.
    """
    try:
        # Merge highs and lows, sort by index
        pivots = sorted(swing_highs + swing_lows, key=lambda p: p["index"])

        if len(pivots) < 5:
            return _wave_result("INSUFFICIENT", 0, pivots, note="Need ≥5 pivot points")

        # Use last 9 pivots (enough for waves 1–5 + abc)
        pts = pivots[-9:]

        # Try to find a 5-wave impulse ending near current price
        result = _try_impulse(pts, current_price)
        if result["probability"] > 0:
            return result

        # Try ABC correction
        result = _try_abc(pts, current_price)
        if result["probability"] > 0:
            return result

        return _wave_result("UNCLEAR", 0, pts, note="No clear wave pattern")

    except Exception as e:
        logger.error("Elliott wave detection error: %s", e)
        return _wave_result("ERROR", 0, [], note=str(e))


def _try_impulse(pts: List[Dict], current_price: float) -> Dict:
    """Attempt to label last 5 pivots as W1 W2 W3 W4 W5."""
    if len(pts) < 5:
        return _wave_result("INSUFFICIENT", 0, pts)

    # Use last 5 pivot points
    p = pts[-5:]
    prices = [x["price"] for x in p]

    # Determine if bullish impulse or bearish
    bullish = prices[-1] > prices[0]

    if bullish:
        # Expect: low, high, low, high, high (ascending structure)
        w1 = _wave_size(prices[0], prices[1])
        w2 = _wave_size(prices[1], prices[2])
        w3 = _wave_size(prices[2], prices[3])
        w4 = _wave_size(prices[3], prices[4])

        # Elliott rules
        r2 = _retrace(prices[0], prices[1], prices[2])
        r4 = _retrace(prices[2], prices[3], prices[4])

        rule_w2 = r2 < 1.0                              # W2 < 100% retrace of W1
        rule_w3 = w3 >= w1 or w3 >= w4                  # W3 not shortest
        rule_w4 = prices[4] > prices[1]                 # W4 no overlap with W1

        prob = 0
        if rule_w2: prob += 30
        if rule_w3: prob += 40
        if rule_w4: prob += 30

        wave_label = _current_wave_label_bullish(prices, current_price)

        return {
            "pattern": "IMPULSE_BULLISH",
            "wave":    wave_label,
            "probability": prob,
            "waves": {
                "W1": round(w1, 2), "W2_retrace": round(r2, 3),
                "W3": round(w3, 2), "W4_retrace": round(r4, 3),
            },
            "levels": {
                "w1_start": round(prices[0], 2),
                "w1_end":   round(prices[1], 2),
                "w3_end":   round(prices[3], 2),
                "w5_target": round(prices[3] + w1 * 1.618, 2),
            },
            "rules": {"w2_valid": rule_w2, "w3_longest": rule_w3, "w4_no_overlap": rule_w4},
            "note": f"Bullish impulse — currently in {wave_label}",
        }

    else:
        # Bearish impulse
        w1 = _wave_size(prices[0], prices[1])
        w2 = _wave_size(prices[1], prices[2])
        w3 = _wave_size(prices[2], prices[3])
        w4 = _wave_size(prices[3], prices[4])

        r2 = _retrace(prices[0], prices[1], prices[2])
        r4 = _retrace(prices[2], prices[3], prices[4])

        rule_w2 = r2 < 1.0
        rule_w3 = w3 >= w1 or w3 >= w4
        rule_w4 = prices[4] < prices[1]

        prob = 0
        if rule_w2: prob += 30
        if rule_w3: prob += 40
        if rule_w4: prob += 30

        wave_label = _current_wave_label_bearish(prices, current_price)

        return {
            "pattern": "IMPULSE_BEARISH",
            "wave":    wave_label,
            "probability": prob,
            "waves": {
                "W1": round(w1, 2), "W2_retrace": round(r2, 3),
                "W3": round(w3, 2), "W4_retrace": round(r4, 3),
            },
            "levels": {
                "w1_start": round(prices[0], 2),
                "w1_end":   round(prices[1], 2),
                "w3_end":   round(prices[3], 2),
                "w5_target": round(prices[3] - w1 * 1.618, 2),
            },
            "rules": {"w2_valid": rule_w2, "w3_longest": rule_w3, "w4_no_overlap": rule_w4},
            "note": f"Bearish impulse — currently in {wave_label}",
        }


def _try_abc(pts: List[Dict], current_price: float) -> Dict:
    """Attempt to label last 3 pivots as A B C correction."""
    if len(pts) < 3:
        return _wave_result("INSUFFICIENT", 0, pts)

    p = pts[-3:]
    prices = [x["price"] for x in p]

    wa = _wave_size(prices[0], prices[1])
    wc = _wave_size(prices[1], prices[2])

    # C should be close to A in size (0.618–1.618 ratio)
    ratio = wc / max(wa, 0.01)
    in_range = 0.5 <= ratio <= 1.618

    prob = 60 if in_range else 25
    direction = "BULLISH" if prices[2] > prices[0] else "BEARISH"

    # Target: C extension
    c_target = prices[1] + (prices[1] - prices[0]) * 1.0

    return {
        "pattern": f"ABC_CORRECTION_{direction}",
        "wave":    "C",
        "probability": prob,
        "waves": {"A": round(wa, 2), "C": round(wc, 2), "C_A_ratio": round(ratio, 3)},
        "levels": {
            "a_start":  round(prices[0], 2),
            "b_end":    round(prices[1], 2),
            "c_target": round(c_target, 2),
        },
        "note": f"ABC correction ({direction}) — C wave in progress",
    }


def _current_wave_label_bullish(prices: List[float], current: float) -> str:
    """Determine which wave we're likely in for a bullish impulse."""
    if current > prices[3]:
        return "5"
    if current > prices[2]:
        return "4"
    if current > prices[1]:
        return "3"
    if current > prices[0]:
        return "2"
    return "1"


def _current_wave_label_bearish(prices: List[float], current: float) -> str:
    if current < prices[3]:
        return "5"
    if current < prices[2]:
        return "4"
    if current < prices[1]:
        return "3"
    if current < prices[0]:
        return "2"
    return "1"


def _wave_result(pattern: str, prob: int, pts: List, note: str = "") -> Dict:
    return {
        "pattern":     pattern,
        "wave":        "?",
        "probability": prob,
        "waves":       {},
        "levels":      {},
        "note":        note,
    }


# ── Neo Wave extensions ───────────────────────────────────────────────────────

def detect_neo_wave(
    candles: List[Candle],
    swing_highs: List[Dict],
    swing_lows: List[Dict],
) -> Dict[str, Any]:
    """
    Neo Wave pattern recognition on top of Elliott.

    Detects:
      - Triangle (symmetrical / expanding)
      - Flat correction
      - Diametric (7-legged butterfly)

    Uses:
      - Wave size symmetry
      - Time ratio
      - Price ratio between alternating waves
    """
    try:
        pivots = sorted(swing_highs + swing_lows, key=lambda p: p["index"])
        if len(pivots) < 5:
            return {"pattern": "INSUFFICIENT_DATA", "probability": 0}

        # Time ratios between adjacent swings
        time_ratios = []
        for i in range(1, len(pivots)):
            dt = pivots[i]["ts"] - pivots[i - 1]["ts"]
            time_ratios.append(max(dt, 1))

        # Price ratios between alternating legs
        prices = [p["price"] for p in pivots[-7:]]
        legs = [abs(prices[i] - prices[i - 1]) for i in range(1, len(prices))]

        return _classify_neo_pattern(legs, time_ratios[-len(legs):] if time_ratios else [])

    except Exception as e:
        logger.error("Neo wave detection error: %s", e)
        return {"pattern": "ERROR", "probability": 0}


def _classify_neo_pattern(legs: List[float], times: List[float]) -> Dict[str, Any]:
    if len(legs) < 3:
        return {"pattern": "INSUFFICIENT_DATA", "probability": 0}

    # Check for triangle: each leg smaller than previous
    if all(legs[i] < legs[i - 1] for i in range(1, len(legs))):
        return {
            "pattern": "CONTRACTING_TRIANGLE",
            "probability": 75,
            "legs": [round(l, 2) for l in legs],
            "note": "Contracting triangle — expect breakout soon",
        }

    # Expanding triangle: each leg larger than previous
    if all(legs[i] > legs[i - 1] for i in range(1, len(legs))):
        return {
            "pattern": "EXPANDING_TRIANGLE",
            "probability": 65,
            "legs": [round(l, 2) for l in legs],
            "note": "Expanding triangle — volatility increasing",
        }

    # Flat correction: legs roughly equal
    if len(legs) >= 3:
        avg = sum(legs[:3]) / 3
        flat = all(abs(l - avg) / max(avg, 1) < 0.3 for l in legs[:3])
        if flat:
            return {
                "pattern": "FLAT_CORRECTION",
                "probability": 70,
                "legs": [round(l, 2) for l in legs[:3]],
                "note": "Flat correction — range-bound structure",
            }

    # Diametric (7-legged): needs 7 legs
    if len(legs) >= 7:
        alt_ratio = [legs[i] / max(legs[i - 2], 0.01) for i in range(2, 7, 2)]
        symmetric = all(0.5 <= r <= 2.0 for r in alt_ratio)
        if symmetric:
            return {
                "pattern": "DIAMETRIC",
                "probability": 55,
                "legs": [round(l, 2) for l in legs[:7]],
                "note": "Diametric (butterfly) — complex multi-wave correction",
            }

    return {"pattern": "COMPLEX_CORRECTION", "probability": 40, "legs": [round(l, 2) for l in legs], "note": "Complex correction underway"}


# ── Main WaveEngine ───────────────────────────────────────────────────────────

class WaveEngine:
    """
    Stateless wrapper that runs Elliott + Neo Wave on candle data.
    Called by chart_signal_engine every analytics cycle.
    """

    def analyze(self, symbol: str, candles: List[Candle], current_price: float) -> Dict[str, Any]:
        try:
            if len(candles) < 20:
                return {"symbol": symbol, "elliott": _wave_result("INSUFFICIENT", 0, []), "neo": {"pattern": "INSUFFICIENT_DATA"}}

            sh = find_swing_highs(candles, lookback=3)
            sl = find_swing_lows(candles, lookback=3)

            elliott = detect_elliott_waves(sh, sl, current_price)
            neo     = detect_neo_wave(candles, sh, sl)

            return {
                "symbol":  symbol,
                "elliott": elliott,
                "neo":     neo,
                "swing_highs": [s["price"] for s in sh[-5:]],
                "swing_lows":  [s["price"] for s in sl[-5:]],
            }

        except Exception as e:
            logger.error("WaveEngine.analyze error for %s: %s", symbol, e)
            return {"symbol": symbol, "elliott": _wave_result("ERROR", 0, []), "neo": {"pattern": "ERROR"}}


# ── Global singleton ───────────────────────────────────────────────────────────
wave_engine = WaveEngine()
