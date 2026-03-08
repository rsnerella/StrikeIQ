"""
advanced_strategies_engine.py — StrikeIQ Step 14

Detects institutional trading patterns:
  • Smart Money Concepts (SMC): liquidity sweeps, BOS, order blocks, FVG
  • ICT Concepts: kill zones, liquidity grabs, premium/discount zones, MSS
  • CRT Model: consolidation, range expansion, trend continuation
  • MSNR: higher highs/lows, trend exhaustion, reversals

Uses real-time data from option_chain_builder / price ticks.
All detectors are stateless (safe for async calls) and return structured dicts.
"""

import logging
import time
from typing import Any, Dict, List, Tuple
from datetime import datetime, timezone, timedelta
from collections import deque

logger = logging.getLogger(__name__)

# ── Price history buffer (shared, symbol-keyed) ───────────────────────────────
_price_history: Dict[str, deque] = {}   # symbol → deque of (timestamp, price, vol)
_MAX_BARS = 60                            # keep last 60 ticks for structure detection

def push_price(symbol: str, price: float, volume: float = 0.0) -> None:
    """Called by message_router on every index_tick. O(1), no heap allocations."""
    if symbol not in _price_history:
        _price_history[symbol] = deque(maxlen=_MAX_BARS)
    _price_history[symbol].append((time.monotonic(), price, volume))

def _prices(symbol: str) -> List[float]:
    return [b[1] for b in _price_history.get(symbol, [])]

def _vols(symbol: str) -> List[float]:
    return [b[2] for b in _price_history.get(symbol, [])]


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 14-A  Smart Money Concepts (SMC)
# ═══════════════════════════════════════════════════════════════════════════════

def detect_smc(symbol: str, chain_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Detect SMC patterns from option chain + price history.
    Returns structured dict consumed by signal_scoring_engine.
    """
    try:
        prices = _prices(symbol)
        spot = chain_data.get("spot", 0)
        strikes = chain_data.get("strikes", [])

        # ── Liquidity Sweep ───────────────────────────────────────────────────
        sweep = _detect_liquidity_sweep(prices, spot)

        # ── Break of Structure ────────────────────────────────────────────────
        bos = _detect_break_of_structure(prices)

        # ── Order Block ───────────────────────────────────────────────────────
        order_block = _detect_order_block(prices, strikes)

        # ── Fair Value Gap ────────────────────────────────────────────────────
        fvg = _detect_fvg(prices)

        # ── Aggregate SMC bias ────────────────────────────────────────────────
        bullish_signals = sum([
            sweep.get("direction") == "bullish",
            bos.get("direction") == "bullish",
            order_block.get("type") == "bullish",
            fvg.get("direction") == "bullish",
        ])
        bearish_signals = sum([
            sweep.get("direction") == "bearish",
            bos.get("direction") == "bearish",
            order_block.get("type") == "bearish",
            fvg.get("direction") == "bearish",
        ])

        if bullish_signals > bearish_signals:
            smc_bias = "bullish"
        elif bearish_signals > bullish_signals:
            smc_bias = "bearish"
        else:
            smc_bias = "neutral"

        confidence = min(100, max(bullish_signals, bearish_signals) * 25)

        return {
            "liquidity_sweep": sweep,
            "break_of_structure": bos,
            "order_block": order_block,
            "fair_value_gap": fvg,
            "smc_bias": smc_bias,
            "confidence": confidence,
            "signals_count": bullish_signals + bearish_signals,
        }

    except Exception as e:
        logger.error(f"SMC detection error for {symbol}: {e}")
        return {"smc_bias": "neutral", "confidence": 0, "error": str(e)}


def _detect_liquidity_sweep(prices: List[float], spot: float) -> Dict[str, Any]:
    """Detect if price has swept a recent high/low and reversed."""
    if len(prices) < 10:
        return {"detected": False, "direction": "neutral", "swept_level": 0}
    try:
        window = prices[-20:] if len(prices) >= 20 else prices
        high = max(window[:-3])
        low = min(window[:-3])
        recent = prices[-3:]
        recent_high = max(recent)
        recent_low = min(recent)

        # Bullish sweep: price briefly dipped below recent low then recovered
        if recent_low < low and prices[-1] > low:
            return {
                "detected": True,
                "direction": "bullish",
                "swept_level": round(low, 2),
                "confidence": min(100, int(abs(recent_low - low) / max(spot * 0.001, 1) * 100))
            }
        # Bearish sweep: price briefly exceeded recent high then reversed
        if recent_high > high and prices[-1] < high:
            return {
                "detected": True,
                "direction": "bearish",
                "swept_level": round(high, 2),
                "confidence": min(100, int(abs(recent_high - high) / max(spot * 0.001, 1) * 100))
            }
        return {"detected": False, "direction": "neutral", "swept_level": 0, "confidence": 0}
    except Exception:
        return {"detected": False, "direction": "neutral", "swept_level": 0, "confidence": 0}


def _detect_break_of_structure(prices: List[float]) -> Dict[str, Any]:
    """Break of structure: price breaks above/below a swing high/low."""
    if len(prices) < 8:
        return {"detected": False, "direction": "neutral", "level": 0}
    try:
        mid = prices[-8:-4]
        recent = prices[-4:]
        swing_high = max(mid)
        swing_low = min(mid)
        current = prices[-1]

        if current > swing_high:
            strength = min(100, int((current - swing_high) / max(swing_high * 0.001, 1) * 100))
            return {"detected": True, "direction": "bullish", "level": round(swing_high, 2), "strength": strength}
        if current < swing_low:
            strength = min(100, int((swing_low - current) / max(swing_low * 0.001, 1) * 100))
            return {"detected": True, "direction": "bearish", "level": round(swing_low, 2), "strength": strength}
        return {"detected": False, "direction": "neutral", "level": 0, "strength": 0}
    except Exception:
        return {"detected": False, "direction": "neutral", "level": 0, "strength": 0}


def _detect_order_block(prices: List[float], strikes: List[Dict]) -> Dict[str, Any]:
    """
    Order block: a consolidation zone before a strong move.
    Use option OI concentration as proxy for institutional interest zones.
    """
    try:
        if not strikes or len(prices) < 6:
            return {"detected": False, "type": "neutral", "level": 0, "oi": 0}

        # Find strike with max OI concentration (call or put)
        max_call_oi = 0
        max_put_oi = 0
        max_call_strike = 0
        max_put_strike = 0

        for s in strikes:
            c_oi = s.get("call_oi", 0)
            p_oi = s.get("put_oi", 0)
            if c_oi > max_call_oi:
                max_call_oi = c_oi
                max_call_strike = s.get("strike", 0)
            if p_oi > max_put_oi:
                max_put_oi = p_oi
                max_put_strike = s.get("strike", 0)

        spot = prices[-1] if prices else 0

        # Call OI wall = bearish order block (resistance)
        # Put OI wall = bullish order block (support)
        if max_put_strike and spot > 0 and max_put_strike < spot:
            return {
                "detected": True,
                "type": "bullish",
                "level": max_put_strike,
                "oi": max_put_oi,
                "label": "Put OI Wall — Institutional Support"
            }
        if max_call_strike and spot > 0 and max_call_strike > spot:
            return {
                "detected": True,
                "type": "bearish",
                "level": max_call_strike,
                "oi": max_call_oi,
                "label": "Call OI Wall — Institutional Resistance"
            }
        return {"detected": False, "type": "neutral", "level": 0, "oi": 0}
    except Exception:
        return {"detected": False, "type": "neutral", "level": 0, "oi": 0}


def _detect_fvg(prices: List[float]) -> Dict[str, Any]:
    """
    Fair Value Gap: a 3-candle pattern where middle candle gaps leaves unfilled space.
    With tick data, simulate with 3-tick windows.
    """
    if len(prices) < 5:
        return {"detected": False, "direction": "neutral", "gap_size": 0}
    try:
        # Use last 5 ticks
        p = prices[-5:]
        # Bullish FVG: p[-3] high < p[-1] low (upward gap)
        # simplified: p[-3] < p[-2] and p[-3] < p[-1] (two-bar run up with gap)
        if p[-3] < p[-2] * 0.9985 and p[-2] < p[-1] * 0.9985:
            gap = round(p[-1] - p[-3], 2)
            return {
                "detected": True,
                "direction": "bullish",
                "gap_size": gap,
                "fill_level": round(p[-3], 2),
                "confidence": min(100, int(gap / max(p[-3] * 0.0005, 0.01) * 100))
            }
        if p[-3] > p[-2] * 1.0015 and p[-2] > p[-1] * 1.0015:
            gap = round(p[-3] - p[-1], 2)
            return {
                "detected": True,
                "direction": "bearish",
                "gap_size": gap,
                "fill_level": round(p[-3], 2),
                "confidence": min(100, int(gap / max(p[-1] * 0.0005, 0.01) * 100))
            }
        return {"detected": False, "direction": "neutral", "gap_size": 0}
    except Exception:
        return {"detected": False, "direction": "neutral", "gap_size": 0}


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 14-B  ICT Concepts
# ═══════════════════════════════════════════════════════════════════════════════

_ICT_KILL_ZONES = {
    # IST times (UTC+5:30)
    "Asian Kill Zone":   (("23:00", "02:00"), "Asia"),   # 4:30–7:30 IST
    "London Kill Zone":  (("03:30", "06:00"), "London"), # 9:00–11:30 IST
    "New York Kill Zone":(("13:30", "16:00"), "NewYork"),# 19:00–21:30 IST (less relevant for NSE)
    "NSE Open Kill Zone":(("03:45", "04:30"), "NSE"),    # 9:15–10:00 IST
    "NSE Close Kill Zone":(("09:45", "10:00"), "NSE"),   # 15:15–15:30 IST
}

def detect_ict(symbol: str, chain_data: Dict[str, Any]) -> Dict[str, Any]:
    """Detect ICT concepts."""
    try:
        prices = _prices(symbol)
        spot = chain_data.get("spot", 0)
        strikes = chain_data.get("strikes", [])

        kill_zone = _detect_kill_zone()
        liq_grab = _detect_liquidity_grab(prices)
        pd_zone = _detect_premium_discount(spot, strikes)
        mss = _detect_market_structure_shift(prices)

        signals = [kill_zone.get("active"), liq_grab.get("detected"), mss.get("detected")]
        active_signals = sum(bool(s) for s in signals)
        confidence = min(100, active_signals * 33)

        return {
            "kill_zone": kill_zone,
            "liquidity_grab": liq_grab,
            "premium_discount_zone": pd_zone,
            "market_structure_shift": mss,
            "ict_confidence": confidence,
            "has_active_signal": active_signals > 0,
        }
    except Exception as e:
        logger.error(f"ICT detection error for {symbol}: {e}")
        return {"ict_confidence": 0, "error": str(e)}


def _detect_kill_zone() -> Dict[str, Any]:
    """Check if current IST time falls within a known kill zone."""
    try:
        ist = datetime.now(timezone(timedelta(hours=5, minutes=30)))
        t = ist.strftime("%H:%M")

        for name, ((start, end), zone) in _ICT_KILL_ZONES.items():
            # Handle wrap-around midnight
            if start <= end:
                active = start <= t <= end
            else:
                active = t >= start or t <= end

            if active:
                return {
                    "active": True,
                    "zone": name,
                    "session": zone,
                    "time": t,
                    "note": f"High-probability manipulation window: {name}"
                }
        return {"active": False, "zone": None, "time": t}
    except Exception:
        return {"active": False, "zone": None}


def _detect_liquidity_grab(prices: List[float]) -> Dict[str, Any]:
    """Detect sharp spike + immediate reversal (liquidity grab)."""
    if len(prices) < 8:
        return {"detected": False, "direction": "neutral", "level": 0}
    try:
        # Spike up then reversal
        recent = prices[-6:]
        avg = sum(recent[:-2]) / max(len(recent[:-2]), 1)
        spike = recent[-2]
        current = recent[-1]

        spike_up = spike > avg * 1.002 and current < avg * 1.001
        spike_dn = spike < avg * 0.998 and current > avg * 0.999

        if spike_up:
            return {"detected": True, "direction": "bearish", "level": round(spike, 2),
                    "note": "Upward liquidity grab — potential short entry"}
        if spike_dn:
            return {"detected": True, "direction": "bullish", "level": round(spike, 2),
                    "note": "Downward liquidity grab — potential long entry"}
        return {"detected": False, "direction": "neutral", "level": 0}
    except Exception:
        return {"detected": False, "direction": "neutral", "level": 0}


def _detect_premium_discount(spot: float, strikes: List[Dict]) -> Dict[str, Any]:
    """
    Premium zone = above equilibrium (ATM).
    Discount zone = below equilibrium.
    Institutional traders: buy discount, sell premium.
    """
    try:
        if not strikes or not spot:
            return {"zone": "neutral", "atm": 0, "description": "No data"}

        # Find ATM
        atm = min(strikes, key=lambda s: abs(s.get("strike", 0) - spot), default={}).get("strike", spot)
        midpoint = atm

        if spot > midpoint * 1.005:
            return {
                "zone": "premium",
                "atm": midpoint,
                "spot": spot,
                "description": "Price in Premium Zone — favor shorts / put buys",
                "deviation_pct": round((spot - midpoint) / max(midpoint, 1) * 100, 2)
            }
        elif spot < midpoint * 0.995:
            return {
                "zone": "discount",
                "atm": midpoint,
                "spot": spot,
                "description": "Price in Discount Zone — favor longs / call buys",
                "deviation_pct": round((midpoint - spot) / max(midpoint, 1) * 100, 2)
            }
        return {
            "zone": "equilibrium",
            "atm": midpoint,
            "spot": spot,
            "description": "Price at equilibrium — wait for directional move",
            "deviation_pct": 0
        }
    except Exception:
        return {"zone": "neutral", "atm": 0}


def _detect_market_structure_shift(prices: List[float]) -> Dict[str, Any]:
    """Market Structure Shift: change from higher-highs to lower-highs (or vice versa)."""
    if len(prices) < 12:
        return {"detected": False, "direction": "neutral"}
    try:
        # Compare two windows: old vs new
        n = len(prices)
        old = prices[n // 2 - 4: n // 2]
        new = prices[-4:]

        old_high = max(old)
        new_high = max(new)
        old_low = min(old)
        new_low = min(new)

        # Shift to bullish: new high > old high AND new low > old low
        if new_high > old_high and new_low > old_low:
            return {
                "detected": True,
                "direction": "bullish",
                "old_high": round(old_high, 2),
                "new_high": round(new_high, 2),
                "note": "Market structure shifted bullish — potential trend reversal up"
            }
        # Shift to bearish: new high < old high AND new low < old low
        if new_high < old_high and new_low < old_low:
            return {
                "detected": True,
                "direction": "bearish",
                "old_low": round(old_low, 2),
                "new_low": round(new_low, 2),
                "note": "Market structure shifted bearish — potential trend reversal down"
            }
        return {"detected": False, "direction": "neutral"}
    except Exception:
        return {"detected": False, "direction": "neutral"}


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 14-C  CRT Model (Consolidation → Range → Trend)
# ═══════════════════════════════════════════════════════════════════════════════

def detect_crt(symbol: str, chain_data: Dict[str, Any]) -> Dict[str, Any]:
    """Detect CRT (Consolidation, Range Expansion, Trend Continuation) model."""
    try:
        prices = _prices(symbol)
        if not prices:
            return {"phase": "unknown", "confidence": 0}

        phase, strength = _classify_crt_phase(prices)

        # Use OI to confirm trend
        strikes = chain_data.get("strikes", [])
        oi_trend = _oi_trend_confirmation(strikes)

        return {
            "phase": phase,
            "strength": strength,
            "oi_confirmation": oi_trend,
            "confidence": min(100, strength * (1.2 if oi_trend.get("confirms") else 0.8)),
            "note": _crt_note(phase, oi_trend)
        }
    except Exception as e:
        logger.error(f"CRT error for {symbol}: {e}")
        return {"phase": "unknown", "confidence": 0}


def _classify_crt_phase(prices: List[float]) -> Tuple[str, float]:
    """Classify current price action as consolidation, expansion, or continuation."""
    if len(prices) < 10:
        return "unknown", 0
    try:
        recent = prices[-10:]
        price_range = max(recent) - min(recent)
        avg = sum(recent) / len(recent)
        range_pct = price_range / max(avg, 1) * 100

        # Consolidation: tight range < 0.3%
        if range_pct < 0.3:
            return "consolidation", min(100.0, (0.3 - range_pct) / 0.3 * 100)

        # Expansion: strong directional move > 0.5%
        net_move = prices[-1] - prices[-10]
        net_pct = abs(net_move) / max(avg, 1) * 100
        if net_pct > 0.5 and range_pct > 0.5:
            return "expansion", min(100.0, net_pct * 20)

        # Check for continuation: same direction as prior 10 bars
        if len(prices) >= 20:
            prior = prices[-20:-10]
            prior_move = prices[-10] - prices[-20]
            current_move = prices[-1] - prices[-10]
            if prior_move * current_move > 0:  # same direction
                return "continuation", min(100.0, abs(current_move) / max(avg, 1) * 2000)

        return "ranging", min(100.0, range_pct * 30)
    except Exception:
        return "unknown", 0


def _oi_trend_confirmation(strikes: List[Dict]) -> Dict[str, Any]:
    """Check OI flow direction to confirm CRT phase."""
    try:
        total_call_oi = sum(s.get("call_oi", 0) for s in strikes)
        total_put_oi = sum(s.get("put_oi", 0) for s in strikes)
        pcr = total_put_oi / max(total_call_oi, 1)

        if pcr > 1.2:
            return {"confirms": True, "direction": "bullish", "pcr": round(pcr, 2)}
        elif pcr < 0.8:
            return {"confirms": True, "direction": "bearish", "pcr": round(pcr, 2)}
        return {"confirms": False, "direction": "neutral", "pcr": round(pcr, 2)}
    except Exception:
        return {"confirms": False, "direction": "neutral", "pcr": 1.0}


def _crt_note(phase: str, oi: Dict) -> str:
    notes = {
        "consolidation": "Price coiling — expect breakout soon",
        "expansion": "Strong momentum — potential continuation",
        "continuation": "Trend intact — ride with managed risk",
        "ranging": "Market ranging — wait for direction",
    }
    base = notes.get(phase, "Monitoring market structure")
    if oi.get("confirms") and oi.get("direction") != "neutral":
        base += f" (OI confirms {oi['direction']})"
    return base


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 14-D  MSNR (Market Structure & Reversal)
# ═══════════════════════════════════════════════════════════════════════════════

def detect_msnr(symbol: str, chain_data: Dict[str, Any]) -> Dict[str, Any]:
    """Detect Market Structure & Reversal patterns (MSNR)."""
    try:
        prices = _prices(symbol)
        if not prices:
            return {"trend": "unknown", "exhaustion": False, "confidence": 0}

        hh_hl = _detect_hh_hl(prices)
        exhaustion = _detect_trend_exhaustion(prices, chain_data)
        reversal = _detect_reversal_signals(prices, chain_data)

        # Overall structure
        if hh_hl.get("pattern") == "HH_HL":
            trend = "bullish"
        elif hh_hl.get("pattern") == "LL_LH":
            trend = "bearish"
        else:
            trend = "choppy"

        confidence = 0
        if hh_hl.get("confirmed"):
            confidence += 40
        if exhaustion.get("detected"):
            confidence += 30
        if reversal.get("signal"):
            confidence += 30

        return {
            "trend": trend,
            "structure": hh_hl,
            "exhaustion": exhaustion,
            "reversal": reversal,
            "confidence": min(100, confidence),
            "note": _msnr_note(trend, exhaustion, reversal)
        }
    except Exception as e:
        logger.error(f"MSNR error for {symbol}: {e}")
        return {"trend": "unknown", "confidence": 0}


def _detect_hh_hl(prices: List[float]) -> Dict[str, Any]:
    """Detect higher highs / higher lows (bullish) or lower lows / lower highs (bearish)."""
    if len(prices) < 12:
        return {"pattern": "insufficient_data", "confirmed": False}
    try:
        # Divide into 3 segments for swing point detection
        n = len(prices)
        seg_size = n // 3
        seg1 = prices[:seg_size]
        seg2 = prices[seg_size: 2 * seg_size]
        seg3 = prices[2 * seg_size:]

        h1, l1 = max(seg1), min(seg1)
        h2, l2 = max(seg2), min(seg2)
        h3, l3 = max(seg3), min(seg3)

        hh_hl = h3 > h2 > h1 and l3 > l2 > l1
        ll_lh = h3 < h2 < h1 and l3 < l2 < l1

        if hh_hl:
            return {
                "pattern": "HH_HL",
                "confirmed": True,
                "highs": [round(h1, 1), round(h2, 1), round(h3, 1)],
                "lows": [round(l1, 1), round(l2, 1), round(l3, 1)]
            }
        if ll_lh:
            return {
                "pattern": "LL_LH",
                "confirmed": True,
                "highs": [round(h1, 1), round(h2, 1), round(h3, 1)],
                "lows": [round(l1, 1), round(l2, 1), round(l3, 1)]
            }
        return {"pattern": "choppy", "confirmed": False}
    except Exception:
        return {"pattern": "unknown", "confirmed": False}


def _detect_trend_exhaustion(prices: List[float], chain_data: Dict[str, Any]) -> Dict[str, Any]:
    """Detect trend exhaustion via momentum divergence + OI signals."""
    if len(prices) < 15:
        return {"detected": False, "type": "none"}
    try:
        # Simple momentum: compare velocity of last 5 vs prior 5
        recent_vel = prices[-1] - prices[-5]
        prior_vel = prices[-6] - prices[-11]
        divergence = abs(recent_vel) < abs(prior_vel) * 0.5

        # OI exhaustion: rapid OI increase with small price move
        spot = chain_data.get("spot", 0)
        strikes = chain_data.get("strikes", [])
        total_oi = sum(s.get("call_oi", 0) + s.get("put_oi", 0) for s in strikes)

        if divergence:
            direction = "bullish_exhaustion" if recent_vel > 0 else "bearish_exhaustion"
            return {
                "detected": True,
                "type": direction,
                "recent_momentum": round(recent_vel, 2),
                "prior_momentum": round(prior_vel, 2),
                "note": f"Momentum slowing — {direction} detected"
            }
        return {"detected": False, "type": "none"}
    except Exception:
        return {"detected": False, "type": "none"}


def _detect_reversal_signals(prices: List[float], chain_data: Dict[str, Any]) -> Dict[str, Any]:
    """Detect potential reversal based on structure + option chain."""
    try:
        if len(prices) < 10:
            return {"signal": None, "confidence": 0}

        spot = chain_data.get("spot", 0)
        strikes = chain_data.get("strikes", [])

        # Find max OI strikes (key levels)
        call_walls = sorted(
            [s for s in strikes if s.get("call_oi", 0) > 0],
            key=lambda s: s.get("call_oi", 0), reverse=True
        )[:2]
        put_walls = sorted(
            [s for s in strikes if s.get("put_oi", 0) > 0],
            key=lambda s: s.get("put_oi", 0), reverse=True
        )[:2]

        if not spot:
            return {"signal": None, "confidence": 0}

        # Near call wall = potential reversal bearish
        for cw in call_walls:
            level = cw.get("strike", 0)
            if level and abs(spot - level) / max(spot, 1) < 0.003:
                return {
                    "signal": "bearish_reversal",
                    "at_level": level,
                    "oi": cw.get("call_oi", 0),
                    "confidence": 65,
                    "note": f"Spot approaching Call Wall at {level} — high reversal probability"
                }
        # Near put wall = potential reversal bullish
        for pw in put_walls:
            level = pw.get("strike", 0)
            if level and abs(spot - level) / max(spot, 1) < 0.003:
                return {
                    "signal": "bullish_reversal",
                    "at_level": level,
                    "oi": pw.get("put_oi", 0),
                    "confidence": 65,
                    "note": f"Spot at Put Wall support at {level} — high reversal probability"
                }
        return {"signal": None, "confidence": 0}
    except Exception:
        return {"signal": None, "confidence": 0}


def _msnr_note(trend: str, exhaustion: Dict, reversal: Dict) -> str:
    if reversal.get("signal"):
        return reversal.get("note", "Reversal signal active")
    if exhaustion.get("detected"):
        return exhaustion.get("note", "Trend exhausting")
    return f"Trend: {trend.upper()} — no reversal signal yet"


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 14 — Master runner
# ═══════════════════════════════════════════════════════════════════════════════

def run_advanced_strategies(symbol: str, chain_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run all four strategy modules and return combined output.
    Called by analytics_broadcaster every cycle.
    """
    try:
        return {
            "type": "advanced_strategies",
            "symbol": symbol,
            "timestamp": int(time.time()),   # P2: int cheaper than ISO string
            "smc": detect_smc(symbol, chain_data),
            "ict": detect_ict(symbol, chain_data),
            "crt": detect_crt(symbol, chain_data),
            "msnr": detect_msnr(symbol, chain_data),
        }
    except Exception as e:
        logger.error(f"Advanced strategies error for {symbol}: {e}")
        return {"type": "advanced_strategies", "symbol": symbol, "error": str(e)}
