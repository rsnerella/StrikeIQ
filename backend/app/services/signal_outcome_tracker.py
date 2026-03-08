"""
signal_outcome_tracker.py — StrikeIQ Learning AI Outcome Tracker

Evaluates chart signals after 5, 15, and 30 minutes using price history.

Design:
  • In-memory pending queue (no DB required)
  • Resolves outcomes when enough price history accumulates in candle_builder
  • Only logs when signal_score >= 50 (performance guard)
  • Writes to JSON log file for ML dataset

No per-tick DB writes. CPU cost: ~0ms per tick.
"""

import asyncio
import json
import logging
import os
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Dataset directory ──────────────────────────────────────────────────────────

_DATASET_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "learning"
)

def _ensure_dataset_dir() -> str:
    os.makedirs(_DATASET_DIR, exist_ok=True)
    return _DATASET_DIR


# ── Outcome evaluation windows ─────────────────────────────────────────────────

EVAL_WINDOWS = [5 * 60, 15 * 60, 30 * 60]   # seconds


class PendingSignal:
    """A chart signal awaiting outcome evaluation."""

    __slots__ = ("signal_id", "symbol", "signal", "confidence", "price_at_signal",
                 "ts", "pcr", "gamma", "wave", "signal_score", "outcomes")

    def __init__(
        self,
        signal_id: str,
        symbol: str,
        signal: str,
        confidence: float,
        price: float,
        ts: float,
        metadata: Dict[str, Any],
    ):
        self.signal_id      = signal_id
        self.symbol         = symbol
        self.signal         = signal
        self.confidence     = confidence
        self.price_at_signal = price
        self.ts             = ts
        self.pcr            = metadata.get("pcr", 0)
        self.gamma          = metadata.get("gamma", 0)
        self.wave           = metadata.get("wave", "?")
        self.signal_score   = metadata.get("signal_score", 0)
        self.outcomes: Dict[int, Optional[str]] = {w: None for w in EVAL_WINDOWS}


class SignalOutcomeTracker:
    """
    Tracks chart signal outcomes in-memory.
    Writes resolved outcomes to JSON dataset file.

    Usage:
        tracker.record_signal(chart_analysis_payload, extra_metadata)
        # Every analytics cycle:
        await tracker.evaluate_pending(current_price)
    """

    MAX_PENDING = 500   # cap to prevent memory growth

    def __init__(self):
        self._pending: deque = deque(maxlen=self.MAX_PENDING)
        self._resolved: List[Dict] = []
        self._dataset_path = os.path.join(_ensure_dataset_dir(), "chart_signals.jsonl")
        self._lock = asyncio.Lock()
        logger.info("SignalOutcomeTracker initialized | dataset=%s", self._dataset_path)

    def record_signal(
        self,
        chart_payload: Dict[str, Any],
        extra: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Record a new chart signal for future outcome evaluation.

        Only records when confidence >= 0.5 (corresponds to signal_score >= 50).
        """
        try:
            confidence = chart_payload.get("confidence", 0)
            if confidence < 0.5:
                return False   # Performance guard — skip low-confidence signals

            signal = chart_payload.get("signal", "WAIT")
            if signal not in ("BUY", "SELL"):
                return False   # Only track actionable signals

            now = time.time()
            signal_id = f"{chart_payload.get('symbol','?')}_{int(now)}"

            meta = {
                "pcr":          (extra or {}).get("pcr", 0),
                "gamma":        (extra or {}).get("gamma", 0),
                "wave":         chart_payload.get("wave", "?"),
                "signal_score": (extra or {}).get("signal_score", 0),
            }

            ps = PendingSignal(
                signal_id  = signal_id,
                symbol     = chart_payload.get("symbol", "?"),
                signal     = signal,
                confidence = confidence,
                price      = chart_payload.get("price", 0),
                ts         = now,
                metadata   = meta,
            )

            self._pending.append(ps)
            logger.debug("Signal recorded: %s %s conf=%.2f", signal_id, signal, confidence)
            return True

        except Exception as e:
            logger.error("record_signal error: %s", e)
            return False

    async def evaluate_pending(self, symbol: str, current_price: float) -> int:
        """
        Evaluate pending signals for which an evaluation window has passed.
        Returns number of newly resolved outcomes.
        """
        if current_price <= 0:
            return 0

        now = time.time()
        resolved_count = 0

        async with self._lock:
            for ps in list(self._pending):
                if ps.symbol != symbol:
                    continue

                all_resolved = True
                for window in EVAL_WINDOWS:
                    if ps.outcomes[window] is not None:
                        continue
                    if now - ps.ts >= window:
                        outcome = self._determine_outcome(ps.signal, ps.price_at_signal, current_price)
                        ps.outcomes[window] = outcome
                    else:
                        all_resolved = False

                if all_resolved:
                    self._pending.remove(ps)
                    record = self._build_record(ps)
                    self._resolved.append(record)
                    self._write_record(record)
                    resolved_count += 1

        return resolved_count

    def _determine_outcome(self, signal: str, entry_price: float, current_price: float) -> str:
        """WIN / LOSS / HOLD based on signal direction vs price movement."""
        move_pct = (current_price - entry_price) / max(entry_price, 1) * 100
        if abs(move_pct) < 0.3:
            return "HOLD"
        if signal == "BUY":
            return "WIN" if move_pct > 0 else "LOSS"
        else:  # SELL
            return "WIN" if move_pct < 0 else "LOSS"

    def _build_record(self, ps: PendingSignal) -> Dict[str, Any]:
        return {
            "signal_id":      ps.signal_id,
            "symbol":         ps.symbol,
            "signal":         ps.signal,
            "confidence":     round(ps.confidence, 3),
            "price":          round(ps.price_at_signal, 2),
            "timestamp":      datetime.fromtimestamp(ps.ts, tz=timezone.utc).isoformat(),
            "pcr":            round(ps.pcr, 3),
            "gamma":          round(ps.gamma, 3),
            "wave":           ps.wave,
            "signal_score":   ps.signal_score,
            "outcomes": {
                f"{w // 60}m": ps.outcomes[w]
                for w in EVAL_WINDOWS
            },
        }

    def _write_record(self, record: Dict[str, Any]) -> None:
        """Append record as one JSONL line — no DB required."""
        try:
            with open(self._dataset_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
            logger.debug("Outcome written: %s", record["signal_id"])
        except Exception as e:
            logger.error("Failed to write outcome record: %s", e)

    def get_stats(self) -> Dict[str, Any]:
        """Summary stats for monitoring."""
        total = len(self._resolved)
        wins  = sum(1 for r in self._resolved if any(v == "WIN"  for v in r["outcomes"].values()))
        losses = sum(1 for r in self._resolved if any(v == "LOSS" for v in r["outcomes"].values()))
        return {
            "pending":    len(self._pending),
            "resolved":   total,
            "wins":       wins,
            "losses":     losses,
            "win_rate":   round(wins / max(total, 1) * 100, 1),
        }


# ── Global singleton ───────────────────────────────────────────────────────────
signal_outcome_tracker = SignalOutcomeTracker()
