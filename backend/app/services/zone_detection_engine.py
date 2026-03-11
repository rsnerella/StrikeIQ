"""
zone_detection_engine.py — StrikeIQ Supply/Demand Zone Detector

Detects:
  • Supply zones  (origin of strong bearish moves)
  • Demand zones  (origin of strong bullish moves)
  • Order blocks  (last consolidation candle before impulse)
  • Liquidity pools (equal highs / equal lows)

Uses:
  • Impulse candle body size relative to ATR
  • Volume spike detection
  • Structure break confirmation

Output: price zones annotated with strength and type.
"""

import logging
from typing import Any, Dict, List
from .candle_builder import Candle

logger = logging.getLogger(__name__)

# ── ATR helper ─────────────────────────────────────────────────────────────────

def _atr(candles: List[Candle], period: int = 14) -> float:
    """Simple ATR using candle ranges."""
    if len(candles) < 2:
        return 1.0
    ranges = [c.range_size() for c in candles[-period:]]
    return sum(ranges) / max(len(ranges), 1)


# ── Impulse detection ──────────────────────────────────────────────────────────

def _is_impulse(candle: Candle, atr: float, multiplier: float = 1.5) -> bool:
    """Return True if candle body is at least multiplier × ATR."""
    return candle.body_size() >= multiplier * atr


# ── Zone structures ────────────────────────────────────────────────────────────

def _make_zone(
    zone_type: str,
    top: float,
    bottom: float,
    ts: float,
    strength: float,
    note: str = "",
) -> Dict[str, Any]:
    return {
        "type":     zone_type,
        "top":      round(top, 2),
        "bottom":   round(bottom, 2),
        "mid":      round((top + bottom) / 2, 2),
        "ts":       int(ts),
        "strength": round(min(100.0, strength), 1),
        "note":     note,
    }


# ── Supply Zone Detection ──────────────────────────────────────────────────────

def detect_supply_zones(candles: List[Candle], atr: float) -> List[Dict]:
    """
    A supply zone is formed by the last consolidation candle(s) before
    a strong bearish impulse move downward.
    """
    zones = []
    if len(candles) < 5:
        return zones

    for i in range(2, len(candles) - 2):
        curr = candles[i]
        prev = candles[i - 1]
        next1 = candles[i + 1]
        next2 = candles[i + 2]

        # Origin candle: bearish, large body
        if curr.is_bearish() and _is_impulse(curr, atr):
            # Confirm: next candle continues down
            if next1.close < curr.close:
                # Zone top = high of the consolidation candle before origin
                zone_top = prev.high
                zone_bot = curr.open
                strength = min(100.0, curr.body_size() / max(atr, 1) * 30)
                zones.append(_make_zone("SUPPLY", zone_top, zone_bot, curr.ts_open, strength,
                                        f"Supply zone: strong bearish impulse @ {curr.close:.0f}"))

    return zones[-5:]  # keep last 5 zones


def detect_demand_zones(candles: List[Candle], atr: float) -> List[Dict]:
    """
    A demand zone is formed by the last consolidation candle(s) before
    a strong bullish impulse move upward.
    """
    zones = []
    if len(candles) < 5:
        return zones

    for i in range(2, len(candles) - 2):
        curr = candles[i]
        prev = candles[i - 1]
        next1 = candles[i + 1]

        if curr.is_bullish() and _is_impulse(curr, atr):
            if next1.close > curr.close:
                zone_bot = prev.low
                zone_top = curr.open
                strength = min(100.0, curr.body_size() / max(atr, 1) * 30)
                zones.append(_make_zone("DEMAND", zone_top, zone_bot, curr.ts_open, strength,
                                        f"Demand zone: strong bullish impulse @ {curr.close:.0f}"))

    return zones[-5:]


# ── Order Block Detection ──────────────────────────────────────────────────────

def detect_order_blocks(candles: List[Candle], atr: float) -> List[Dict]:
    """
    Order block: the last opposite-direction candle before a strong impulse.
    Bullish OB: last bearish candle before bullish impulse (demand OB).
    Bearish OB: last bullish candle before bearish impulse (supply OB).
    """
    obs = []
    if len(candles) < 4:
        return obs

    for i in range(1, len(candles) - 2):
        curr  = candles[i]
        next1 = candles[i + 1]
        next2 = candles[i + 2] if i + 2 < len(candles) else None

        # Bullish OB: curr is bearish, followed by strong bullish move
        if curr.is_bearish() and next1.is_bullish() and _is_impulse(next1, atr):
            obs.append(_make_zone("BULLISH_OB", curr.high, curr.low, curr.ts_open,
                                  min(100, next1.body_size() / max(atr, 1) * 40),
                                  f"Bullish Order Block @ {curr.low:.0f}–{curr.high:.0f}"))

        # Bearish OB: curr is bullish, followed by strong bearish move
        if curr.is_bullish() and next1.is_bearish() and _is_impulse(next1, atr):
            obs.append(_make_zone("BEARISH_OB", curr.high, curr.low, curr.ts_open,
                                  min(100, next1.body_size() / max(atr, 1) * 40),
                                  f"Bearish Order Block @ {curr.low:.0f}–{curr.high:.0f}"))

    return obs[-5:]


# ── Liquidity Pool Detection ───────────────────────────────────────────────────

def detect_liquidity_pools(candles: List[Candle], tolerance_pct: float = 0.002) -> List[Dict]:
    """
    Liquidity pools: clusters of equal highs or equal lows within tolerance.
    These are targets for smart money stop-hunts.
    """
    pools = []
    if len(candles) < 5:
        return pools

    highs = [(c.high, c.ts_open) for c in candles[-30:]]
    lows  = [(c.low,  c.ts_open) for c in candles[-30:]]

    def _find_clusters(levels, label):
        clusters = []
        used = set()
        for i, (price_i, ts_i) in enumerate(levels):
            if i in used:
                continue
            group = [(price_i, ts_i)]
            for j, (price_j, ts_j) in enumerate(levels):
                if j != i and j not in used:
                    if abs(price_i - price_j) / max(price_i, 1) <= tolerance_pct:
                        group.append((price_j, ts_j))
                        used.add(j)
            if len(group) >= 2:
                lvl = sum(p for p, _ in group) / len(group)
                clusters.append(_make_zone(
                    f"LIQUIDITY_{label}", lvl + lvl * 0.001, lvl - lvl * 0.001,
                    min(t for _, t in group),
                    min(100, len(group) * 20),
                    f"{label} liquidity pool @ {lvl:.0f} ({len(group)} touches)"
                ))
        return clusters

    pools += _find_clusters(highs, "EQUAL_HIGH")
    pools += _find_clusters(lows,  "EQUAL_LOW")
    return pools


# ── ZoneDetectionEngine ───────────────────────────────────────────────────────

class ZoneDetectionEngine:
    """
    Runs full zone detection on candle history.
    Returns supply, demand, order blocks, and liquidity pools.
    """

    def analyze(self, symbol: str, candles: List[Candle], current_price: float) -> Dict[str, Any]:
        try:
            if len(candles) < 10:
                return {"symbol": symbol, "supply": [], "demand": [], "order_blocks": [], "liquidity_pools": [], "nearest_supply": None, "nearest_demand": None}

            atr = _atr(candles)

            supply  = detect_supply_zones(candles, atr)
            demand  = detect_demand_zones(candles, atr)
            obs     = detect_order_blocks(candles, atr)
            pools   = detect_liquidity_pools(candles)

            # Find nearest zones to current price
            above = [z for z in supply + [z for z in obs if z["type"] == "BEARISH_OB"] if z["bottom"] > current_price]
            below = [z for z in demand + [z for z in obs if z["type"] == "BULLISH_OB"]  if z["top"] < current_price]

            nearest_supply = min(above, key=lambda z: z["bottom"] - current_price) if above else None
            nearest_demand = max(below, key=lambda z: current_price - z["top"])    if below else None

            return {
                "symbol":          symbol,
                "atr":             round(atr, 2),
                "supply":          supply,
                "demand":          demand,
                "order_blocks":    obs,
                "liquidity_pools": pools,
                "all_zones": supply + demand + obs + pools,
                "nearest_supply":  nearest_supply,
                "nearest_demand":  nearest_demand,
            }

        except Exception as e:
            logger.error("ZoneDetectionEngine.analyze error for %s: %s", symbol, e)
            return {"symbol": symbol, "supply": [], "demand": [], "order_blocks": [], "liquidity_pools": [], "nearest_supply": None, "nearest_demand": None}


# ── Global singleton ───────────────────────────────────────────────────────────
zone_detection_engine = ZoneDetectionEngine()
