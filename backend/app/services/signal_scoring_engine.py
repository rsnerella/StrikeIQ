"""
signal_scoring_engine.py — StrikeIQ Step 15

Combines signals from:
  • OI changes (put/call velocity)
  • Price movement (momentum)
  • Gamma exposure (flip level distance)
  • SMC structure (liquidity sweeps, BOS, OBs, FVG)
  • ICT liquidity concepts

Produces a normalized confidence score (0-100) + directional bias.
"""

import logging
import time
from typing import Any, Dict, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class SignalScoringEngine:
    """
    Step 15: Unified signal scoring.

    Takes outputs from advanced_strategies_engine + standard analytics
    and produces a single merged score payload.
    """

    # ── Weights for each signal category (must sum ≤ 100) ──────────────────
    WEIGHTS = {
        "oi_flow":      20,   # OI velocity and direction
        "price_move":   15,   # Momentum / trend direction
        "gamma":        20,   # Gamma exposure and flip distance
        "smc":          20,   # SMC (BOS, sweep, OB, FVG)
        "ict":          15,   # ICT (kill zone, MSS, liq grab)
        "crt":          10,   # CRT phase
    }

    def score(
        self,
        symbol: str,
        chain_data: Dict[str, Any],
        analytics: Dict[str, Any],
        advanced: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Compute unified signal score.

        Args:
            symbol:       Trading symbol
            chain_data:   Raw option chain (strikes, spot)
            analytics:    Output from AnalyticsBroadcaster._compute_analytics
            advanced:     Output from advanced_strategies_engine.run_advanced_strategies
        Returns:
            Structured signal dict with score, bias, components, top signals
        """
        try:
            components: Dict[str, float] = {}
            bias_votes: Dict[str, float] = {"bullish": 0.0, "bearish": 0.0, "neutral": 0.0}

            # ── OI Flow Score ────────────────────────────────────────────────
            oi_score, oi_bias = self._score_oi_flow(chain_data, analytics)
            components["oi_flow"] = oi_score
            bias_votes[oi_bias] += oi_score * self.WEIGHTS["oi_flow"] / 100

            # ── Price Movement Score ─────────────────────────────────────────
            price_score, price_bias = self._score_price_movement(analytics)
            components["price_move"] = price_score
            bias_votes[price_bias] += price_score * self.WEIGHTS["price_move"] / 100

            # ── Gamma Score ──────────────────────────────────────────────────
            gamma_score, gamma_bias = self._score_gamma(analytics)
            components["gamma"] = gamma_score
            bias_votes[gamma_bias] += gamma_score * self.WEIGHTS["gamma"] / 100

            # ── SMC Score ────────────────────────────────────────────────────
            smc_score, smc_bias = self._score_smc(advanced.get("smc", {}))
            components["smc"] = smc_score
            bias_votes[smc_bias] += smc_score * self.WEIGHTS["smc"] / 100

            # ── ICT Score ────────────────────────────────────────────────────
            ict_score, ict_bias = self._score_ict(advanced.get("ict", {}))
            components["ict"] = ict_score
            bias_votes[ict_bias] += ict_score * self.WEIGHTS["ict"] / 100

            # ── CRT Score ────────────────────────────────────────────────────
            crt_score, crt_bias = self._score_crt(advanced.get("crt", {}))
            components["crt"] = crt_score
            bias_votes[crt_bias] += crt_score * self.WEIGHTS["crt"] / 100

            # ── Aggregate ────────────────────────────────────────────────────
            weighted_score = sum(
                components[k] * self.WEIGHTS[k] / 100
                for k in components
            )
            overall_score = round(min(100.0, max(0.0, weighted_score)), 1)

            # Dominant bias
            max_vote = max(bias_votes, key=lambda k: bias_votes[k])
            if bias_votes[max_vote] == 0:
                dominant_bias = "neutral"
            else:
                dominant_bias = max_vote

            # Confidence tier
            if overall_score >= 70:
                tier = "HIGH"
            elif overall_score >= 45:
                tier = "MEDIUM"
            elif overall_score >= 20:
                tier = "LOW"
            else:
                tier = "NOISE"

            # Top signals
            top_signals = self._extract_top_signals(advanced, analytics, dominant_bias)

            return {
                "type": "signal_score",
                "symbol": symbol,
                "timestamp": int(time.time()),
                "score": overall_score,
                "bias": dominant_bias,
                "confidence_tier": tier,
                "components": components,
                "bias_votes": {k: round(v, 2) for k, v in bias_votes.items()},
                "top_signals": top_signals,
                "summary": self._build_summary(symbol, overall_score, dominant_bias, tier, top_signals),
            }

        except Exception as e:
            logger.error(f"Signal scoring error for {symbol}: {e}")
            return {
                "type": "signal_score",
                "symbol": symbol,
                "score": 0,
                "bias": "neutral",
                "confidence_tier": "NOISE",
                "error": str(e),
                "components": {},
                "top_signals": [],
                "summary": "Score unavailable"
            }

    # ── Component Scorers ─────────────────────────────────────────────────────

    def _score_oi_flow(self, chain_data: Dict, analytics: Dict) -> tuple:
        """Score OI flow: velocity and PCR."""
        try:
            structural = analytics.get("structural", {})
            pcr = analytics.get("bias", {}).get("pcr", 1.0) or 1.0
            oi_velocity = structural.get("oi_velocity", 0)

            score = 0.0
            if pcr > 1.2:
                score += min(40.0, (pcr - 1.0) * 40)
                bias = "bullish"
            elif pcr < 0.8:
                score += min(40.0, (1.0 - pcr) * 50)
                bias = "bearish"
            else:
                score += 10.0
                bias = "neutral"

            # OI velocity adds weight
            abs_vel = abs(oi_velocity or 0)
            score += min(60.0, abs_vel * 0.1)
            return min(100.0, score), bias
        except Exception:
            return 0.0, "neutral"

    def _score_price_movement(self, analytics: Dict) -> tuple:
        """Score price momentum from structural analysis."""
        try:
            structural = analytics.get("structural", {})
            gamma_regime = structural.get("gamma_regime", "neutral")
            intent_score = structural.get("intent_score", 0)

            score = min(100.0, abs(intent_score or 0) * 0.5)
            if gamma_regime in ("positive_gamma", "positive"):
                return score + 20, "bullish"
            elif gamma_regime in ("negative_gamma", "negative"):
                return score + 20, "bearish"
            return score, "neutral"
        except Exception:
            return 0.0, "neutral"

    def _score_gamma(self, analytics: Dict) -> tuple:
        """Score based on gamma flip distance and exposure."""
        try:
            structural = analytics.get("structural", {})
            distance = structural.get("distance_from_flip", 0) or 0
            net_gamma = structural.get("net_gamma", 0) or 0

            # Close to flip = high score (unstable zone)
            flip_score = max(0.0, 100.0 - min(distance * 0.5, 100.0))
            gamma_score = min(100.0, flip_score + min(abs(net_gamma) * 0.001, 50.0))

            bias = "bullish" if net_gamma > 0 else ("bearish" if net_gamma < 0 else "neutral")
            return gamma_score, bias
        except Exception:
            return 0.0, "neutral"

    def _score_smc(self, smc: Dict) -> tuple:
        """Score SMC signals."""
        try:
            if not smc:
                return 0.0, "neutral"
            confidence = smc.get("confidence", 0)
            bias = smc.get("smc_bias", "neutral")
            return float(confidence), bias
        except Exception:
            return 0.0, "neutral"

    def _score_ict(self, ict: Dict) -> tuple:
        """Score ICT signals."""
        try:
            if not ict:
                return 0.0, "neutral"
            confidence = ict.get("ict_confidence", 0)

            # Kill zone active = extra weight
            kz = ict.get("kill_zone", {})
            if kz.get("active"):
                confidence += 20

            # Liquidity grab direction
            lg = ict.get("liquidity_grab", {})
            bias = lg.get("direction", "neutral") if lg.get("detected") else "neutral"

            # MSS direction override
            mss = ict.get("market_structure_shift", {})
            if mss.get("detected"):
                bias = mss.get("direction", bias)

            return min(100.0, float(confidence)), bias
        except Exception:
            return 0.0, "neutral"

    def _score_crt(self, crt: Dict) -> tuple:
        """Score CRT phase."""
        try:
            if not crt:
                return 0.0, "neutral"
            phase = crt.get("phase", "unknown")
            confidence = crt.get("confidence", 0)
            oi_dir = crt.get("oi_confirmation", {}).get("direction", "neutral")

            phase_scores = {
                "expansion": 80.0,
                "continuation": 70.0,
                "consolidation": 30.0,
                "ranging": 20.0,
                "unknown": 0.0
            }
            score = phase_scores.get(phase, 0.0)
            score = min(100.0, score * (confidence / 100))
            return score, oi_dir
        except Exception:
            return 0.0, "neutral"

    # ── Top Signals Builder ───────────────────────────────────────────────────

    def _extract_top_signals(
        self, advanced: Dict, analytics: Dict, bias: str
    ) -> list:
        """Extract most important signals for display in Signal Matrix."""
        signals = []

        try:
            # Type guard: advanced/analytics must be dicts — stale or error payloads may be bool
            if not isinstance(advanced, dict):
                logger.debug("_extract_top_signals: advanced is not a dict (%s) — skipping", type(advanced))
                return []
            if not isinstance(analytics, dict):
                analytics = {}

            smc = advanced.get("smc", {}) or {}
            ict = advanced.get("ict", {}) or {}
            crt = advanced.get("crt", {}) or {}
            msnr = advanced.get("msnr", {}) or {}
            structural = analytics.get("structural", {}) or {}

            # Ensure each sub-dict is actually a dict (defensive, since detectors can fail)
            if not isinstance(smc, dict):  smc = {}
            if not isinstance(ict, dict):  ict = {}
            if not isinstance(crt, dict):  crt = {}
            if not isinstance(msnr, dict): msnr = {}

            # SMC signals
            sweep = smc.get("liquidity_sweep", {})
            if isinstance(sweep, dict) and sweep.get("detected"):
                signals.append({
                    "source": "SMC",
                    "signal": "LIQUIDITY SWEEP",
                    "direction": sweep.get("direction", "neutral"),
                    "confidence": sweep.get("confidence", 0),
                    "level": sweep.get("swept_level", 0),
                })

            bos = smc.get("break_of_structure", {})
            if isinstance(bos, dict) and bos.get("detected"):
                signals.append({
                    "source": "SMC",
                    "signal": "BREAK OF STRUCTURE",
                    "direction": bos.get("direction", "neutral"),
                    "confidence": bos.get("strength", 0),
                    "level": bos.get("level", 0),
                })

            fvg = smc.get("fair_value_gap", {})
            if isinstance(fvg, dict) and fvg.get("detected"):
                signals.append({
                    "source": "SMC",
                    "signal": "FAIR VALUE GAP",
                    "direction": fvg.get("direction", "neutral"),
                    "confidence": fvg.get("confidence", 0),
                })

            # ICT signals
            kz = ict.get("kill_zone", {})
            if isinstance(kz, dict) and kz.get("active"):
                signals.append({
                    "source": "ICT",
                    "signal": f"KILL ZONE — {kz.get('zone', 'Active')}",
                    "direction": "watch",
                    "confidence": 70,
                })

            lg = ict.get("liquidity_grab", {})
            if isinstance(lg, dict) and lg.get("detected"):
                signals.append({
                    "source": "ICT",
                    "signal": "LIQUIDITY GRAB",
                    "direction": lg.get("direction", "neutral"),
                    "confidence": 65,
                    "level": lg.get("level", 0),
                })

            mss = ict.get("market_structure_shift", {})
            if isinstance(mss, dict) and mss.get("detected"):
                signals.append({
                    "source": "ICT",
                    "signal": "MARKET STRUCTURE SHIFT",
                    "direction": mss.get("direction", "neutral"),
                    "confidence": 60,
                })

            # CRT phase
            if crt.get("phase") in ("expansion", "continuation"):
                signals.append({
                    "source": "CRT",
                    "signal": f"CRT {crt['phase'].upper()}",
                    "direction": crt.get("oi_confirmation", {}).get("direction", "neutral"),
                    "confidence": int(crt.get("confidence", 0)),
                })

            # MSNR
            reversal = msnr.get("reversal", {})
            if reversal.get("signal"):
                signals.append({
                    "source": "MSNR",
                    "signal": reversal["signal"].replace("_", " ").upper(),
                    "direction": "bullish" if "bullish" in reversal["signal"] else "bearish",
                    "confidence": reversal.get("confidence", 0),
                    "level": reversal.get("at_level", 0),
                    "note": reversal.get("note", ""),
                })

            if msnr.get("exhaustion", {}).get("detected"):
                ex = msnr["exhaustion"]
                signals.append({
                    "source": "MSNR",
                    "signal": ex.get("type", "EXHAUSTION").replace("_", " ").upper(),
                    "direction": "bearish" if "bullish" in ex.get("type", "") else "bullish",
                    "confidence": 55,
                    "note": ex.get("note", ""),
                })

        except Exception as e:
            logger.error(f"Error building top signals: {e}")

        # Sort by confidence descending, cap at 5
        signals.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        return signals[:5]

    def _build_summary(
        self, symbol: str, score: float, bias: str, tier: str, signals: list
    ) -> str:
        top = signals[0]["signal"] if signals else "No active signals"
        return (
            f"{symbol} — Score {score:.0f}/100 | {tier} confidence | "
            f"Bias: {bias.upper()} | Top: {top}"
        )


# ── Module singleton ─────────────────────────────────────────────────────────
signal_scoring_engine = SignalScoringEngine()
