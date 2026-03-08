"""
chart_signal_engine.py — StrikeIQ Chart Signal Generator

Combines:
  • Elliott Wave analysis
  • Market structure (BOS, MSS, HH/HL)
  • Supply / Demand zones
  • Candlestick patterns
  • Options analytics (OI, gamma, PCR)

Generates:
  • BUY / SELL / WAIT signal
  • Confidence score (0–1)
  • Target zones and stop-loss zones
  • chart_analysis WebSocket payload

Performance:
  • Pure Python — no I/O
  • ~1ms per call
  • Called every 3s by analytics_broadcaster
"""

import logging
import time
from typing import Any, Dict, List, Optional

from .candle_builder import candle_builder
from .structure_engine import structure_engine
from .wave_engine import wave_engine
from .zone_detection_engine import zone_detection_engine
from .candle_pattern_engine import candle_pattern_engine

logger = logging.getLogger(__name__)

# ── Score weights ──────────────────────────────────────────────────────────────
_W = {
    "wave":      0.20,
    "structure": 0.25,
    "zone":      0.20,
    "pattern":   0.15,
    "options":   0.20,
}


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


class ChartSignalEngine:
    """
    Master chart intelligence engine.
    Combines all chart sub-engines into a single tradable signal.
    """

    def analyze(
        self,
        symbol: str,
        current_price: float,
        chain_data: Optional[Dict[str, Any]] = None,
        options_analytics: Optional[Dict[str, Any]] = None,
        interval: str = "1m",
    ) -> Dict[str, Any]:
        """
        Full chart analysis.

        Args:
            symbol:             "NIFTY" or "BANKNIFTY"
            current_price:      Latest spot price
            chain_data:         Option chain snapshot
            options_analytics:  Output from analytics_broadcaster
            interval:           Candle interval for analysis ("1m" or "5m")

        Returns:
            chart_analysis payload ready for WebSocket broadcast.
        """
        try:
            t0 = time.monotonic()

            candles = candle_builder.get_candles(symbol, interval, n=100)

            if not candles or current_price <= 0:
                return self._empty(symbol, current_price, "Insufficient candle data")

            # ── Sub-engine calls ───────────────────────────────────────────────
            structure = structure_engine.analyze(symbol, candles, current_price)
            waves     = wave_engine.analyze(symbol, candles, current_price)
            zones     = zone_detection_engine.analyze(symbol, candles, current_price)
            patterns  = candle_pattern_engine.analyze(symbol, candles)

            # ── Score assembly ─────────────────────────────────────────────────
            wave_score    = self._score_wave(waves)
            struct_score  = self._score_structure(structure)
            zone_score    = self._score_zones(zones, current_price)
            pattern_score = self._score_pattern(patterns)
            options_score = self._score_options(options_analytics or {})

            raw_bull = (
                wave_score["bull"]    * _W["wave"]     +
                struct_score["bull"]  * _W["structure"] +
                zone_score["bull"]    * _W["zone"]     +
                pattern_score["bull"] * _W["pattern"]  +
                options_score["bull"] * _W["options"]
            )
            raw_bear = (
                wave_score["bear"]    * _W["wave"]     +
                struct_score["bear"]  * _W["structure"] +
                zone_score["bear"]    * _W["zone"]     +
                pattern_score["bear"] * _W["pattern"]  +
                options_score["bear"] * _W["options"]
            )

            bull = _clamp(raw_bull)
            bear = _clamp(raw_bear)
            diff = bull - bear
            confidence = _clamp(abs(diff))

            if diff > 0.15:
                signal = "BUY"
            elif diff < -0.15:
                signal = "SELL"
            else:
                signal = "WAIT"

            # ── Target / Stop zones ────────────────────────────────────────────
            supply = zones.get("nearest_supply")
            demand = zones.get("nearest_demand")
            atr    = zones.get("atr", current_price * 0.005)

            if signal == "BUY":
                target_zone = [round(current_price + atr, 2), round(current_price + atr * 2, 2)]
                stop_zone   = [round(current_price - atr * 1.5, 2), round(current_price - atr, 2)]
                if supply:
                    target_zone = [supply["bottom"], supply["top"]]
                if demand:
                    stop_zone = [demand["bottom"], demand["top"]]
            elif signal == "SELL":
                target_zone = [round(current_price - atr * 2, 2), round(current_price - atr, 2)]
                stop_zone   = [round(current_price + atr, 2), round(current_price + atr * 1.5, 2)]
                if demand:
                    target_zone = [demand["bottom"], demand["top"]]
                if supply:
                    stop_zone = [supply["bottom"], supply["top"]]
            else:
                target_zone = []
                stop_zone   = []

            elapsed_ms = round((time.monotonic() - t0) * 1000, 1)

            result = {
                "type":        "chart_analysis",
                "symbol":      symbol,
                "timestamp":   int(time.time()),
                "price":       round(current_price, 2),
                "signal":      signal,
                "confidence":  round(confidence, 3),
                "bull_score":  round(bull, 3),
                "bear_score":  round(bear, 3),
                # Wave
                "wave":        waves["elliott"].get("wave", "?"),
                "wave_pattern": waves["elliott"].get("pattern", "UNKNOWN"),
                "wave_probability": waves["elliott"].get("probability", 0),
                "neo_pattern": waves["neo"].get("pattern", "UNKNOWN"),
                # Structure
                "trend":       structure.get("trend", "UNKNOWN"),
                "bos":         structure.get("bos", {}).get("detected", False),
                "bos_direction": structure.get("bos", {}).get("direction", "NONE"),
                "mss":         structure.get("mss", {}).get("detected", False),
                # Zones
                "supply_zone": [supply["bottom"], supply["top"]] if supply else [],
                "demand_zone": [demand["bottom"], demand["top"]] if demand else [],
                "order_blocks": len(zones.get("order_blocks", [])),
                "liquidity_pools": len(zones.get("liquidity_pools", [])),
                # Patterns
                "candle_pattern": patterns["primary"]["pattern"] if patterns["primary"] else None,
                "candle_signal":  patterns["primary"]["signal"]  if patterns["primary"] else "WAIT",
                # Trade levels
                "target_zone": target_zone,
                "stop_zone":   stop_zone,
                # Meta
                "computation_ms": elapsed_ms,
            }

            logger.debug(
                "CHART SIGNAL [%s] signal=%s conf=%.2f wave=%s trend=%s (%.1fms)",
                symbol, signal, confidence,
                result["wave"], result["trend"], elapsed_ms
            )

            return result

        except Exception as e:
            logger.error("ChartSignalEngine.analyze error for %s: %s", symbol, e)
            return self._empty(symbol, current_price, str(e))

    # ── Sub-scorers ────────────────────────────────────────────────────────────

    def _score_wave(self, waves: Dict) -> Dict[str, float]:
        pattern = waves.get("elliott", {}).get("pattern", "")
        prob    = waves.get("elliott", {}).get("probability", 0) / 100.0
        wave    = waves.get("elliott", {}).get("wave", "?")

        bull = bear = 0.0
        if "BULLISH" in pattern:
            bull = prob
            if wave in ("3", "5"):   # strongest bullish waves
                bull = min(1.0, bull * 1.2)
        elif "BEARISH" in pattern:
            bear = prob
            if wave in ("3", "5"):
                bear = min(1.0, bear * 1.2)
        elif "ABC" in pattern:
            if "BULLISH" in pattern:
                bull = prob * 0.6
            else:
                bear = prob * 0.6

        return {"bull": bull, "bear": bear}

    def _score_structure(self, structure: Dict) -> Dict[str, float]:
        trend = structure.get("trend", "CHOPPY")
        bos   = structure.get("bos", {})
        mss   = structure.get("mss", {})

        bull = bear = 0.0
        if trend == "BULLISH":
            bull = 0.7
        elif trend == "BEARISH":
            bear = 0.7

        if bos.get("detected"):
            if bos.get("direction") == "BULLISH":
                bull = min(1.0, bull + 0.2)
            elif bos.get("direction") == "BEARISH":
                bear = min(1.0, bear + 0.2)

        if mss.get("detected"):
            new_trend = mss.get("to", "")
            if new_trend == "BULLISH":
                bull = min(1.0, bull + 0.15)
            elif new_trend == "BEARISH":
                bear = min(1.0, bear + 0.15)

        return {"bull": bull, "bear": bear}

    def _score_zones(self, zones: Dict, price: float) -> Dict[str, float]:
        bull = bear = 0.0
        demand = zones.get("nearest_demand")
        supply = zones.get("nearest_supply")

        if demand:
            dist_pct = abs(price - demand["mid"]) / max(price, 1)
            if dist_pct < 0.005:          # within 0.5% of demand zone
                bull = min(1.0, demand["strength"] / 100.0 * 0.8)

        if supply:
            dist_pct = abs(price - supply["mid"]) / max(price, 1)
            if dist_pct < 0.005:
                bear = min(1.0, supply["strength"] / 100.0 * 0.8)

        return {"bull": bull, "bear": bear}

    def _score_pattern(self, patterns: Dict) -> Dict[str, float]:
        primary = patterns.get("primary")
        if not primary:
            return {"bull": 0.0, "bear": 0.0}

        strength = primary.get("strength", 0) / 100.0
        direction = primary.get("direction", "NEUTRAL")

        if direction == "BULLISH":
            return {"bull": strength, "bear": 0.0}
        elif direction == "BEARISH":
            return {"bull": 0.0, "bear": strength}
        return {"bull": 0.0, "bear": 0.0}

    def _score_options(self, analytics: Dict) -> Dict[str, float]:
        """Extract bullish/bearish score from existing analytics output."""
        bull = bear = 0.0

        bias_label = analytics.get("bias", {}).get("label", "") if isinstance(analytics.get("bias"), dict) else ""
        pcr        = analytics.get("bias", {}).get("pcr", 1.0) if isinstance(analytics.get("bias"), dict) else 1.0

        if bias_label and "bullish" in bias_label.lower():
            bull += 0.4
        elif bias_label and "bearish" in bias_label.lower():
            bear += 0.4

        if pcr > 1.2:
            bull += 0.3
        elif pcr < 0.8:
            bear += 0.3

        # Gamma from structural analytics
        struct = analytics.get("structural", {})
        gamma_regime = struct.get("gamma_regime", "") if isinstance(struct, dict) else ""
        if "positive" in gamma_regime.lower():
            bull += 0.3
        elif "negative" in gamma_regime.lower():
            bear += 0.3

        return {"bull": _clamp(bull), "bear": _clamp(bear)}

    def _empty(self, symbol: str, price: float, reason: str) -> Dict[str, Any]:
        return {
            "type": "chart_analysis",
            "symbol": symbol,
            "timestamp": int(time.time()),
            "price": round(price, 2),
            "signal": "WAIT",
            "confidence": 0.0,
            "wave": "?",
            "wave_pattern": "INSUFFICIENT_DATA",
            "neo_pattern": "INSUFFICIENT_DATA",
            "trend": "UNKNOWN",
            "bos": False,
            "mss": False,
            "supply_zone": [],
            "demand_zone": [],
            "order_blocks": 0,
            "liquidity_pools": 0,
            "candle_pattern": None,
            "candle_signal": "WAIT",
            "target_zone": [],
            "stop_zone": [],
            "note": reason,
            "computation_ms": 0,
        }


# ── Global singleton ───────────────────────────────────────────────────────────
chart_signal_engine = ChartSignalEngine()
