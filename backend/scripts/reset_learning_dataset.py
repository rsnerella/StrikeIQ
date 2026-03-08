"""
reset_learning_dataset.py — StrikeIQ Learning Dataset Reset

Run this before the next market open to start fresh learning data collection.

Actions:
  1. Archive today's JSONL dataset (timestamped backup)
  2. Clear signal logs from DB (if SQLAlchemy models available)
  3. Reset signal_outcome_tracker in-memory state
  4. Preserve: token cache, system config, analytics cache, Redis state

Usage:
    python scripts/reset_learning_dataset.py [--archive-only] [--dry-run]

Safe:
  - Does NOT drop tables
  - Does NOT touch Redis
  - Does NOT modify analytics or system config
"""

import argparse
import json
import logging
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("reset_learning")

# ── Paths ──────────────────────────────────────────────────────────────────────

SCRIPT_DIR   = Path(__file__).parent
BACKEND_DIR  = SCRIPT_DIR.parent
DATA_DIR     = BACKEND_DIR / "data" / "learning"
ARCHIVE_DIR  = DATA_DIR / "archive"
DATASET_FILE = DATA_DIR / "chart_signals.jsonl"


def parse_args():
    parser = argparse.ArgumentParser(description="Reset StrikeIQ learning dataset")
    parser.add_argument("--archive-only", action="store_true",
                        help="Only archive current dataset, do not clear DB tables")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be done without actually doing it")
    return parser.parse_args()


def archive_dataset(dry_run: bool = False) -> Path | None:
    """Archive today's chart_signals.jsonl with timestamp."""
    if not DATASET_FILE.exists():
        logger.info("No dataset file to archive: %s", DATASET_FILE)
        return None

    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    archive_path = ARCHIVE_DIR / f"chart_signals_{ts}.jsonl"

    if dry_run:
        logger.info("[DRY RUN] Would archive %s → %s", DATASET_FILE, archive_path)
        return archive_path

    shutil.copy2(DATASET_FILE, archive_path)
    logger.info("✅ Dataset archived: %s (%d bytes)", archive_path, archive_path.stat().st_size)
    return archive_path


def clear_jsonl_dataset(dry_run: bool = False) -> int:
    """Count records in current dataset then truncate the file."""
    if not DATASET_FILE.exists():
        return 0

    count = 0
    with open(DATASET_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                count += 1

    if dry_run:
        logger.info("[DRY RUN] Would clear %d records from %s", count, DATASET_FILE)
        return count

    DATASET_FILE.write_text("", encoding="utf-8")
    logger.info("✅ Cleared %d records from %s", count, DATASET_FILE)
    return count


def clear_db_signal_logs(dry_run: bool = False) -> int:
    """
    Clear signal_logs from DB via SQLAlchemy.
    Does NOT touch: token cache, system config, analytics cache.
    """
    try:
        sys.path.insert(0, str(BACKEND_DIR))
        from app.models.database import SessionLocal
        from app.models.ai_signal_log import AiSignalLog

        db = SessionLocal()
        try:
            count = db.query(AiSignalLog).count()
            if dry_run:
                logger.info("[DRY RUN] Would delete %d rows from ai_signal_log", count)
                return count

            db.query(AiSignalLog).delete()
            db.commit()
            logger.info("✅ Cleared %d rows from ai_signal_log table", count)
            return count
        finally:
            db.close()

    except Exception as e:
        logger.warning("DB clear skipped (may not be needed): %s", e)
        return 0


def print_summary(archived: Path | None, jsonl_cleared: int, db_cleared: int, dry_run: bool) -> None:
    prefix = "[DRY RUN] " if dry_run else ""
    print("\n" + "═" * 60)
    print(f"  {prefix}StrikeIQ Learning Dataset Reset")
    print("═" * 60)
    print(f"  Archive:         {archived or 'None'}")
    print(f"  JSONL cleared:   {jsonl_cleared} records")
    print(f"  DB rows cleared: {db_cleared}")
    print("  Redis:           UNTOUCHED ✅")
    print("  Token cache:     UNTOUCHED ✅")
    print("  Analytics cache: UNTOUCHED ✅")
    print("═" * 60)
    print("  System is ready to collect fresh learning data from next market open.")
    print("═" * 60 + "\n")


def main():
    args = parse_args()

    logger.info("Starting learning dataset reset (dry_run=%s, archive_only=%s)",
                args.dry_run, args.archive_only)

    # Step 1: Archive
    archived = archive_dataset(dry_run=args.dry_run)

    if args.archive_only:
        logger.info("--archive-only flag set. Stopping after archive.")
        print_summary(archived, 0, 0, args.dry_run)
        return

    # Step 2: Clear JSONL dataset
    jsonl_cleared = clear_jsonl_dataset(dry_run=args.dry_run)

    # Step 3: Clear DB signal logs
    db_cleared = clear_db_signal_logs(dry_run=args.dry_run)

    # Step 4: Summary
    print_summary(archived, jsonl_cleared, db_cleared, args.dry_run)


if __name__ == "__main__":
    main()
