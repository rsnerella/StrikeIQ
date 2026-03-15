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
from app.analytics.structure_engine import structure_engine
from .candle_pattern_engine import candle_pattern_engine

logger = logging.getLogger(__name__)

# ── Score weights ──────────────────────────────────────────────────────────────
_W = {
    "wave":      0.15,  # Elliott
    "neo_wave":  0.10,  # Neo Wave
    "structure": 0.20,
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
        """
        try:
            t0 = time.monotonic()
            
            candles = candle_builder.get_candles(symbol, interval, n=100)

            if not candles or current_price <= 0:
                return self._empty(symbol, current_price, "Insufficient candle data")

            # ── Unified Engine Call ───────────────────────────────────────────
            analysis = structure_engine.analyze_market_structure(candles, current_price, symbol)
            
            # ── Sub-engine calls ───────────────────────────────────────────────
            # candles_patterns is still separate
            patterns  = candle_pattern_engine.analyze(symbol, candles)

            # ── Score assembly ─────────────────────────────────────────────────
            wave_score    = self._score_wave(analysis.wave_pattern)
            neo_score     = self._score_neo_wave(analysis.neo_wave)
            struct_score  = self._score_structure(analysis.structure_pattern, analysis.alerts)
            zone_score    = self._score_zones(analysis.supply_zones, analysis.demand_zones, current_price)
            pattern_score = self._score_pattern(patterns)
            options_score = self._score_options(options_analytics or {})

            raw_bull = (
                wave_score["bull"]    * _W["wave"]      +
                neo_score["bull"]     * _W["neo_wave"]  +
                struct_score["bull"]  * _W["structure"] +
                zone_score["bull"]    * _W["zone"]      +
                pattern_score["bull"] * _W["pattern"]   +
                options_score["bull"] * _W["options"]
            )
            raw_bear = (
                wave_score["bear"]    * _W["wave"]      +
                neo_score["bear"]     * _W["neo_wave"]  +
                struct_score["bear"]  * _W["structure"] +
                zone_score["bear"]    * _W["zone"]      +
                pattern_score["bear"] * _W["pattern"]   +
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
                target_zone = [round(current_price - atr * 2, 2), round(current_price - atr * 2, 2)]
            # ── Target / Stop zones ────────────────────────────────────────────
            supply = analysis.supply_zones[-1] if analysis.supply_zones else None
            demand = analysis.demand_zones[-1] if analysis.demand_zones else None
            atr    = current_price * 0.005 # Default fallback

            if signal == "BUY":
                target_zone = [round(current_price + atr, 2), round(current_price + atr * 2, 2)]
                stop_zone   = [round(current_price - atr * 1.5, 2), round(current_price - atr, 2)]
                if supply:
                    target_zone = [supply.bottom, supply.top]
                if demand:
                    stop_zone = [demand.bottom, demand.top]
            elif signal == "SELL":
                target_zone = [round(current_price - atr * 2, 2), round(current_price - atr * 2, 2)]
                stop_zone   = [round(current_price + atr * 2, 2), round(current_price + atr * 1.5, 2)]
                if demand:
                    target_zone = [demand.bottom, demand.top]
                if supply:
                    stop_zone = [supply.bottom, supply.top]
            else:
                target_zone = []
                stop_zone = []

            # ── Payload assembly ────────────────────────────────────────────────
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
                "wave":        analysis.wave_pattern.wave_label,
                "wave_pattern": analysis.wave_pattern.wave_type,
                "wave_probability": analysis.wave_pattern.probability,
                "wave_points": [sp.price for sp in analysis.swing_points[-5:]],
                "neo_pattern": analysis.neo_wave.get("pattern", "UNKNOWN"),
                # Structure
                "trend":       analysis.structure_pattern.trend,
                "bos":         any(a.get("type") == "structure_break" for a in analysis.alerts),
                "mss":         analysis.momentum_state,
                # Zones
                "supply_zone": [supply.bottom, supply.top] if supply else [],
                "demand_zone": [demand.bottom, demand.top] if demand else [],
                "all_zones": [
                    {"type": z.type, "top": z.top, "bottom": z.bottom, "strength": z.strength}
                    for z in analysis.supply_zones + analysis.demand_zones
                ],
                "order_blocks": analysis.key_levels.get("resistance", []) + analysis.key_levels.get("support", []),
                # Patterns
                "candle_pattern": patterns["primary"]["pattern"] if patterns["primary"] else None,
                "candle_signal":  patterns["primary"]["signal"]  if patterns["primary"] else "WAIT",
                # Trade levels
                "target_zone": target_zone,
                "stop_zone":   stop_zone,
                # Meta
                "computation_ms": elapsed_ms,
            }

            return result

        except Exception as e:
            logger.error("ChartSignalEngine.analyze error for %s: %s", symbol, e)
            return self._empty(symbol, current_price, str(e))

    # ── Sub-scorers ────────────────────────────────────────────────────────────

    def _score_wave(self, wave_pattern: Any) -> Dict[str, float]:
        pattern = wave_pattern.wave_type
        prob    = wave_pattern.probability
        label    = wave_pattern.wave_label

        bull = bear = 0.0
        if "BULLISH" in pattern or pattern == "IMPULSE":
            bull = prob
            if "W3" in label or "W5" in label:
                bull = min(1.0, bull * 1.2)
        elif "BEARISH" in pattern:
            bear = prob
            if "W3" in label or "W5" in label:
                bear = min(1.0, bear * 1.2)
        
        return {"bull": bull, "bear": bear}

    def _score_neo_wave(self, neo_wave: Dict) -> Dict[str, float]:
        """Score based on Neo Wave pattern confidence."""
        pattern = neo_wave.get("pattern", "UNKNOWN")
        conf = neo_wave.get("confidence", 0)
        
        bull = bear = 0.0
        # Diatmetrics and Symmetricals are often trend continuation or reversal
        if conf > 0.5:
            # Simplified: if pattern is detected, it adds to conviction
            # In a real system, we'd check if A-G is bullish or bearish
            bull = conf * 0.5 
            
        return {"bull": bull, "bear": bear}

    def _score_structure(self, structure_pattern: Any, alerts: List[Dict]) -> Dict[str, float]:
        trend = structure_pattern.trend
        
        bull = bear = 0.0
        if trend == "BULLISH":
            bull = 0.7
        elif trend == "BEARISH":
            bear = 0.7

        for alert in alerts:
            if alert.get("type") == "structure_break":
                if "broken below" in alert.get("message", ""):
                    bear = min(1.0, bear + 0.3)
                elif "broken above" in alert.get("message", ""):
                    bull = min(1.0, bull + 0.3)

        return {"bull": bull, "bear": bear}

    def _score_zones(self, supply: List[Any], demand: List[Any], price: float) -> Dict[str, float]:
        bull = bear = 0.0
        
        if demand:
            d = demand[-1]
            dist_pct = abs(price - d.mid) / max(price, 1)
            if dist_pct < 0.005:
                bull = min(1.0, d.strength / 100.0 * 0.8)

        if supply:
            s = supply[-1]
            dist_pct = abs(price - s.mid) / max(price, 1)
            if dist_pct < 0.005:
                bear = min(1.0, s.strength / 100.0 * 0.8)

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
