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

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.models.database import AsyncSessionLocal
from app.models.ai_signal_log import AiSignalLog
from app.models.signal_outcome import SignalOutcome

logger = logging.getLogger(__name__)

# No longer used, but kept for cleanup if needed
_DATASET_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "learning"
)


# ── Outcome evaluation windows ─────────────────────────────────────────────────

EVAL_WINDOWS = [5 * 60, 15 * 60, 30 * 60]   # seconds


class PendingSignal:
    """A chart signal awaiting outcome evaluation."""

    __slots__ = ("signal_id", "db_id", "symbol", "signal", "confidence", "price_at_signal",
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
        self.db_id          = None  # To be filled after DB save
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
        self._resolved_count = 0
        self._wins = 0
        self._losses = 0
        self._lock = asyncio.Lock()
        logger.info("SignalOutcomeTracker initialized | Supabase Persistence Active")

    async def record_signal(
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

            # Persist to Supabase immediately (ai_signal_logs)
            try:
                async with AsyncSessionLocal() as session:
                    db_log = AiSignalLog(
                        symbol=ps.symbol,
                        signal=ps.signal,
                        confidence=ps.confidence,
                        spot_price=ps.price_at_signal,
                        extra_metadata={
                            **meta,
                            "signal_id_internal": signal_id
                        }
                    )
                    session.add(db_log)
                    await session.commit()
                    await session.refresh(db_log)
                    ps.db_id = db_log.id
            except Exception as db_e:
                logger.error(f"Failed to persist signal to DB: {db_e}")
                # Don't return False, we can still track in-memory for this session

            self._pending.append(ps)
            logger.info("Signal recorded & persisted: %s %s (DB ID: %s)", signal_id, signal, ps.db_id)
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
                    await self._persist_outcomes(ps, current_price)
                    self._resolved_count += 1
                    resolved_count += 1

        return resolved_count

    async def _persist_outcomes(self, ps: PendingSignal, final_price: float) -> None:
        """Persist resolved outcomes to signal_outcomes table"""
        if not ps.db_id:
            logger.warning(f"Cannot persist outcomes for signal {ps.signal_id} - missing DB ID")
            return

        try:
            async with AsyncSessionLocal() as session:
                for window, result in ps.outcomes.items():
                    outcome = SignalOutcome(
                        signal_id=ps.db_id,
                        outcome_type=f"{window // 60}m",
                        outcome_value=final_price - ps.price_at_signal,
                        result=result,
                        metadata={
                            "entry_price": ps.price_at_signal,
                            "exit_price": final_price,
                            "window_seconds": window
                        }
                    )
                    session.add(outcome)
                    
                    if result == "WIN":
                        self._wins += 1
                    elif result == "LOSS":
                        self._losses += 1
                        
                await session.commit()
                logger.info(f"Outcomes persisted for signal {ps.db_id}")
        except Exception as e:
            logger.error(f"Failed to persist outcomes to DB: {e}")

    def _determine_outcome(self, signal: str, entry_price: float, current_price: float) -> str:
        """WIN / LOSS / HOLD based on signal direction vs price movement."""
        move_pct = (current_price - entry_price) / max(entry_price, 1) * 100
        if abs(move_pct) < 0.3:
            return "HOLD"
        if signal == "BUY":
            return "WIN" if move_pct > 0 else "LOSS"
        else:  # SELL
            return "WIN" if move_pct < 0 else "LOSS"

    def get_stats(self) -> Dict[str, Any]:
        """Summary stats for monitoring."""
        return {
            "pending":    len(self._pending),
            "resolved":   self._resolved_count,
            "wins":       self._wins,
            "losses":     self._losses,
            "win_rate":   round(self._wins / max(self._resolved_count, 1) * 100, 1),
        }


# ── Global singleton ───────────────────────────────────────────────────────────
signal_outcome_tracker = SignalOutcomeTracker()
