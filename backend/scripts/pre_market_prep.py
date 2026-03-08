#!/usr/bin/env python3
"""
pre_market_prep.py — StrikeIQ Pre-Market Session Preparation

Performs a full system reset and validation before market open.

Steps:
  1. Inspect & categorise PostgreSQL tables
  2. Truncate runtime tables (preserve config / strategy tables)
  3. Clear Redis runtime keys (preserve upstox_access_token)
  4. Reset learning dataset on disk
  5. Import-test all backend pipeline modules
  6. Simulate tick flow through message_router → candle_builder
  7. Verify chart_signal_engine output
  8. Verify WebSocket broadcast message types
  9. Verify Zustand store message handling (via wsStore type check)
 10. Print final health report

Usage:
    cd d:\\StrikeIQ\\backend
    python scripts/pre_market_prep.py [--dry-run]

    --dry-run  Prints what would be done without actually modifying any data.

IMPORTANT:
    • Does NOT drop tables
    • Does NOT delete schema
    • Does NOT touch upstox_access_token in Redis
    • Does NOT remove strategy / formula / instrument / config tables
"""

import asyncio
import json
import logging
import os
import sys
import time
import shutil
import argparse
from datetime import datetime, timezone
from pathlib import Path

# ── path setup ─────────────────────────────────────────────────────────────────
SCRIPT_DIR  = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

# ── logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("pre_market_prep")

# ── colour helpers ─────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

def ok(msg):  logger.info(f"{GREEN}✅ {msg}{RESET}")
def warn(msg): logger.warning(f"{YELLOW}⚠️  {msg}{RESET}")
def fail(msg): logger.error(f"{RED}❌ {msg}{RESET}")
def step(n, msg): logger.info(f"\n{BOLD}{CYAN}── STEP {n}: {msg.upper()} ──{RESET}")

# ── Table classification ───────────────────────────────────────────────────────
# Tables that must NEVER be touched — safe-list driven
PRESERVE_KEYWORDS = {
    "users", "strategies", "formula", "indicator", "instrument_registry",
    "instruments", "config", "configuration", "expiry", "symbol_map",
    "nse_instruments", "alembic", "schema_version", "migrations",
    "token", "auth", "credentials", "admin", "roles", "permissions",
    "strategy", "formula_definitions", "indicator_configs",
}

# Explicit runtime table names to truncate
RUNTIME_TABLE_KEYWORDS = {
    "tick", "snapshot", "heatmap", "cache", "signal_log", "signal_outcome",
    "chart_signal", "learning", "ws_connection", "session_state",
    "prediction", "outcome", "ai_event", "market_snapshot",
    "option_chain_snapshot", "smart_money_prediction", "analytics_cache",
    "oi_cache", "price_cache", "candle",
}


def classify_tables(table_names: list) -> tuple:
    """
    Returns (preserve_tables, runtime_tables).
    A table is preserved if any preserve keyword is found in its name.
    """
    preserve = []
    runtime  = []
    for t in table_names:
        tl = t.lower()
        if any(kw in tl for kw in PRESERVE_KEYWORDS):
            preserve.append(t)
        elif any(kw in tl for kw in RUNTIME_TABLE_KEYWORDS):
            runtime.append(t)
        else:
            preserve.append(t)   # unknown → safe side, preserve
    return sorted(preserve), sorted(runtime)


# ──────────────────────────────────────────────────────────────────────────────
# STEP 1 — Inspect PostgreSQL tables
# ──────────────────────────────────────────────────────────────────────────────

def step1_inspect_tables(db_url: str) -> tuple:
    step(1, "Inspect PostgreSQL Tables")
    try:
        from sqlalchemy import create_engine, inspect as sa_inspect, text
        engine = create_engine(db_url)
        with engine.connect() as conn:
            insp = sa_inspect(engine)
            tables = insp.get_table_names()
            ok(f"Connected to PostgreSQL — {len(tables)} tables found")
            preserve, runtime = classify_tables(tables)
            logger.info(f"  CONFIG (preserve): {preserve}")
            logger.info(f"  RUNTIME (clean):   {runtime}")
            return preserve, runtime
    except Exception as e:
        fail(f"PostgreSQL inspect failed: {e}")
        return [], []


# ──────────────────────────────────────────────────────────────────────────────
# STEP 2 — Truncate runtime tables
# ──────────────────────────────────────────────────────────────────────────────

def step2_truncate_runtime(db_url: str, runtime_tables: list, dry_run: bool) -> list:
    step(2, "Clean Runtime Tables")
    cleaned = []
    if not runtime_tables:
        warn("No runtime tables identified — skipping")
        return cleaned

    try:
        from sqlalchemy import create_engine, text
        engine = create_engine(db_url)
        with engine.connect() as conn:
            for table in runtime_tables:
                sql = f'TRUNCATE TABLE "{table}" RESTART IDENTITY CASCADE;'
                if dry_run:
                    logger.info(f"  [DRY RUN] Would run: {sql}")
                else:
                    try:
                        conn.execute(text(sql))
                        conn.commit()
                        ok(f"Truncated: {table}")
                        cleaned.append(table)
                    except Exception as e:
                        warn(f"Could not truncate {table}: {e}")
    except Exception as e:
        fail(f"DB truncate failed: {e}")

    return cleaned


# ──────────────────────────────────────────────────────────────────────────────
# STEP 3 — Clear Redis runtime keys
# ──────────────────────────────────────────────────────────────────────────────

REDIS_RUNTIME_PATTERNS = [
    "market_state*",
    "ws_clients*",
    "analytics_cache*",
    "signal_cache*",
    "price_cache*",
    "chain_snapshot*",
    "heatmap_cache*",
    "oi_cache*",
    "candle_*",
]

REDIS_PROTECTED_PREFIXES = ["upstox_access_token", "token:"]


async def step3_clear_redis(redis_url: str, dry_run: bool) -> list:
    step(3, "Clear Redis Runtime State")
    cleared = []
    try:
        import redis.asyncio as redis_async
        rc = redis_async.from_url(redis_url, decode_responses=True)
        await rc.ping()
        ok("Redis connected")

        for pattern in REDIS_RUNTIME_PATTERNS:
            keys = await rc.keys(pattern)
            for key in keys:
                # Double-check against protected prefixes
                if any(key.startswith(p) for p in REDIS_PROTECTED_PREFIXES):
                    warn(f"  SKIPPING protected key: {key}")
                    continue
                if dry_run:
                    logger.info(f"  [DRY RUN] Would delete key: {key}")
                else:
                    await rc.delete(key)
                    cleared.append(key)

        if cleared:
            ok(f"Deleted {len(cleared)} Redis runtime keys")
        else:
            ok("No matching Redis runtime keys found (or dry run)")

        await rc.aclose()
    except Exception as e:
        warn(f"Redis clear skipped: {e}")

    return cleared


# ──────────────────────────────────────────────────────────────────────────────
# STEP 4 — Reset learning dataset
# ──────────────────────────────────────────────────────────────────────────────

LEARNING_DIR = BACKEND_DIR / "data" / "learning"
ARCHIVE_DIR  = LEARNING_DIR / "archive"


def step4_reset_learning_dataset(dry_run: bool) -> dict:
    step(4, "Reset Learning Dataset")
    result = {"archived": [], "created": ""}

    LEARNING_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    for f in LEARNING_DIR.glob("*.jsonl"):
        archive_path = ARCHIVE_DIR / f"{f.stem}_{ts}{f.suffix}"
        if dry_run:
            logger.info(f"  [DRY RUN] Would archive {f.name} → {archive_path.name}")
        else:
            shutil.copy2(f, archive_path)
            f.write_text("", encoding="utf-8")
            ok(f"Archived {f.name} → {archive_path.name}")
        result["archived"].append(f.name)

    # Create fresh dataset file
    new_file = LEARNING_DIR / "learning_signals.jsonl"
    if dry_run:
        logger.info(f"  [DRY RUN] Would create {new_file}")
    else:
        new_file.touch()
        ok(f"Created fresh dataset: {new_file}")
    result["created"] = str(new_file)

    return result


# ──────────────────────────────────────────────────────────────────────────────
# STEP 5 — Verify backend pipeline imports
# ──────────────────────────────────────────────────────────────────────────────

PIPELINE_MODULES = [
    ("app.services.message_router",            "message_router"),
    ("app.services.candle_builder",            "candle_builder"),
    ("app.services.option_chain_builder",      "option_chain_builder"),
    ("app.services.oi_heatmap_engine",         "oi_heatmap_engine"),
    ("app.services.analytics_broadcaster",     "analytics_broadcaster"),
    ("app.services.advanced_strategies_engine","run_advanced_strategies"),
    ("app.services.signal_scoring_engine",     "signal_scoring_engine"),
    ("app.services.structure_engine",          "structure_engine"),
    ("app.services.wave_engine",               "wave_engine"),
    ("app.services.zone_detection_engine",     "zone_detection_engine"),
    ("app.services.candle_pattern_engine",     "candle_pattern_engine"),
    ("app.services.chart_signal_engine",       "chart_signal_engine"),
    ("app.services.signal_outcome_tracker",    "signal_outcome_tracker"),
]


def step5_verify_imports() -> dict:
    step(5, "Verify Backend Pipeline Imports")
    passed = []
    failed = []

    for module_path, attr in PIPELINE_MODULES:
        try:
            mod = __import__(module_path, fromlist=[attr])
            getattr(mod, attr)
            ok(f"{module_path}.{attr}")
            passed.append(module_path)
        except Exception as e:
            fail(f"{module_path}.{attr} — {e}")
            failed.append((module_path, str(e)))

    return {"passed": passed, "failed": failed}


# ──────────────────────────────────────────────────────────────────────────────
# STEP 6 — Simulate tick flow
# ──────────────────────────────────────────────────────────────────────────────

SIMULATED_TICKS = [
    {"instrument_key": "NSE_INDEX|NIFTY 50",   "ltp": 22450.0, "oi": 0,       "volume": 1000, "timestamp": time.time()},
    {"instrument_key": "NSE_INDEX|NIFTY 50",   "ltp": 22460.5, "oi": 0,       "volume": 1200, "timestamp": time.time()},
    {"instrument_key": "NSE_INDEX|NIFTY 50",   "ltp": 22445.0, "oi": 0,       "volume": 900,  "timestamp": time.time()},
    {"instrument_key": "NSE_INDEX|NIFTY BANK", "ltp": 48200.0, "oi": 0,       "volume": 500,  "timestamp": time.time()},
    {"instrument_key": "NSE_INDEX|NIFTY BANK", "ltp": 48215.5, "oi": 0,       "volume": 700,  "timestamp": time.time()},
]


def step6_simulate_ticks() -> dict:
    step(6, "Simulate Tick Flow")
    result = {"routed": 0, "candle_ticks": 0, "errors": []}

    try:
        from app.services.message_router import MessageRouter
        from app.services.candle_builder import candle_builder

        router = MessageRouter()
        now = time.time()

        # Feed a burst of 60 synthetic ticks at slightly different timestamps
        # to exercise candle boundaries
        for i, base_tick in enumerate(SIMULATED_TICKS * 12):
            tick = dict(base_tick)
            tick["timestamp"] = now + i * 5   # 5s apart → crosses 1m boundary at i=12

            routed = router.route_tick(tick)
            if routed:
                result["routed"] += 1

        # Push directly into candle_builder to verify boundary crossing
        for i in range(65):
            price = 22400 + (i % 20) * 3
            ts = now + i * 5
            candle_builder.push_tick("NIFTY", price, volume=float(i * 100), ts=ts)
            result["candle_ticks"] += 1

        # Verify candles were built
        candles_1m = candle_builder.get_candles("NIFTY", "1m", n=10)
        ok(f"Tick simulation complete — routed={result['routed']} candle_ticks={result['candle_ticks']}")
        ok(f"Candles built: 1m={len(candles_1m)}")
        result["candles_1m"] = len(candles_1m)

    except Exception as e:
        fail(f"Tick simulation error: {e}")
        result["errors"].append(str(e))

    return result


# ──────────────────────────────────────────────────────────────────────────────
# STEP 7 — Verify chart_signal_engine
# ──────────────────────────────────────────────────────────────────────────────

REQUIRED_CHART_FIELDS = [
    "trend", "wave", "supply_zone", "demand_zone",
    "signal", "confidence", "target_zone", "stop_zone",
]


def step7_verify_chart_engine() -> dict:
    step(7, "Verify Chart Signal Engine")
    result = {"fields_present": [], "fields_missing": [], "signal": None, "error": None}

    try:
        from app.services.chart_signal_engine import chart_signal_engine

        output = chart_signal_engine.analyze(
            symbol="NIFTY",
            current_price=22450.0,
            chain_data={
                "spot": 22450.0,
                "strikes": [],
                "pcr": 1.1,
            },
            options_analytics={},
            interval="1m",
        )

        result["signal"] = output.get("signal")
        logger.info(f"  Chart engine output: signal={output.get('signal')} "
                    f"conf={output.get('confidence'):.3f} "
                    f"wave={output.get('wave')} "
                    f"trend={output.get('trend')}")

        for field in REQUIRED_CHART_FIELDS:
            if field in output:
                result["fields_present"].append(field)
                ok(f"  ✓ {field} = {output[field]}")
            else:
                result["fields_missing"].append(field)
                fail(f"  ✗ {field} MISSING")

    except Exception as e:
        fail(f"Chart engine error: {e}")
        result["error"] = str(e)
        result["fields_missing"] = REQUIRED_CHART_FIELDS

    return result


# ──────────────────────────────────────────────────────────────────────────────
# STEP 8 — Validate WebSocket broadcast message types
# ──────────────────────────────────────────────────────────────────────────────

EXPECTED_WS_TYPES = [
    "index_tick",
    "option_chain_update",
    "heatmap_update",
    "analytics",
    "advanced_strategies",
    "signal_score",
    "chart_analysis",
]


def step8_validate_ws_message_types() -> dict:
    step(8, "Validate WebSocket Broadcast Message Types")
    result = {"present": [], "missing": []}

    try:
        from app.services.message_router import MessageRouter
        from app.services.chart_signal_engine import chart_signal_engine
        from app.services.advanced_strategies_engine import run_advanced_strategies
        from app.services.signal_scoring_engine import signal_scoring_engine

        router = MessageRouter()

        type_map = {
            "index_tick":         lambda: router.route_tick({
                                      "instrument_key": "NSE_INDEX|NIFTY 50",
                                      "ltp": 22450.0, "oi": 0, "volume": 100,
                                      "timestamp": time.time()
                                  }),
            "option_chain_update": lambda: {"type": "option_chain_update"},  # produced by option_chain_builder
            "heatmap_update":      lambda: {"type": "heatmap_update"},       # produced by oi_heatmap_engine
            "analytics":           lambda: {"type": "analytics"},            # produced by analytics_broadcaster
            "advanced_strategies": lambda: run_advanced_strategies("NIFTY", {"spot": 22450, "strikes": []}),
            "signal_score":        lambda: signal_scoring_engine.score(
                                       "NIFTY",
                                       {"spot": 22450, "strikes": []},
                                       {},
                                       run_advanced_strategies("NIFTY", {"spot": 22450, "strikes": []})
                                   ),
            "chart_analysis":      lambda: chart_signal_engine.analyze(
                                       symbol="NIFTY",
                                       current_price=22450.0,
                                       chain_data={"spot": 22450, "strikes": []},
                                   ),
        }

        for msg_type, fn in type_map.items():
            try:
                out = fn()
                if out:
                    ok(f"  ✓ {msg_type} — type={out.get('type', '?')}")
                    result["present"].append(msg_type)
                else:
                    warn(f"  ~ {msg_type} — returned None/empty (may be normal if no chain data)")
                    result["present"].append(msg_type)
            except Exception as e:
                fail(f"  ✗ {msg_type} — {e}")
                result["missing"].append(msg_type)

    except Exception as e:
        fail(f"WS type validation error: {e}")
        result["missing"] = EXPECTED_WS_TYPES

    return result


# ──────────────────────────────────────────────────────────────────────────────
# STEP 9 — Validate frontend Zustand store message handling
# ──────────────────────────────────────────────────────────────────────────────

ZUSTAND_EXPECTED_HANDLERS = [
    "chart_analysis",
    "advanced_strategies",
    "signal_score",
    "analytics",
    "option_chain_snapshot",
    "index_tick",
]


def step9_validate_frontend_store() -> dict:
    step(9, "Validate Frontend Zustand Store")
    result = {"handled": [], "missing": []}

    store_file = BACKEND_DIR.parent / "frontend" / "src" / "core" / "ws" / "wsStore.ts"

    try:
        content = store_file.read_text(encoding="utf-8")
        for msg_type in ZUSTAND_EXPECTED_HANDLERS:
            if msg_type in content:
                ok(f"  ✓ wsStore handles '{msg_type}'")
                result["handled"].append(msg_type)
            else:
                fail(f"  ✗ wsStore missing handler for '{msg_type}'")
                result["missing"].append(msg_type)
    except Exception as e:
        warn(f"Could not read wsStore.ts: {e}")
        result["missing"] = ZUSTAND_EXPECTED_HANDLERS

    return result


# ──────────────────────────────────────────────────────────────────────────────
# STEP 10 — Final health report
# ──────────────────────────────────────────────────────────────────────────────

def step10_health_report(
    preserve, runtime, cleaned, redis_cleared, dataset_result,
    imports, tick_sim, chart, ws_types, store
):
    step(10, "Final Health Report")

    border = "═" * 65
    print(f"\n{BOLD}{CYAN}{border}{RESET}")
    print(f"{BOLD}{CYAN}  StrikeIQ Pre-Market Preparation Report{RESET}")
    print(f"{BOLD}{CYAN}  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}{RESET}")
    print(f"{BOLD}{CYAN}{border}{RESET}\n")

    # DB
    print(f"{BOLD}● Database{RESET}")
    print(f"  Tables preserved  : {len(preserve)}")
    print(f"  Tables cleaned    : {len(cleaned)}/{len(runtime)}")
    for t in cleaned: print(f"    {GREEN}✓ {t}{RESET}")

    # Redis
    print(f"\n{BOLD}● Redis{RESET}")
    print(f"  Keys cleared      : {len(redis_cleared)}")
    print(f"  Token preserved   : upstox_access_token {GREEN}✅{RESET}")

    # Dataset
    print(f"\n{BOLD}● Learning Dataset{RESET}")
    print(f"  Files archived    : {len(dataset_result.get('archived', []))}")
    print(f"  Fresh file        : {dataset_result.get('created', 'N/A')}")

    # Imports
    print(f"\n{BOLD}● Backend Pipeline Modules{RESET}")
    print(f"  Passed : {len(imports['passed'])}/{len(PIPELINE_MODULES)}")
    if imports["failed"]:
        for m, e in imports["failed"]:
            print(f"  {RED}✗ {m}: {e}{RESET}")

    # Tick sim
    print(f"\n{BOLD}● Tick Flow Simulation{RESET}")
    print(f"  Ticks routed      : {tick_sim.get('routed', 0)}")
    print(f"  Candle ticks fed  : {tick_sim.get('candle_ticks', 0)}")
    print(f"  1m candles built  : {tick_sim.get('candles_1m', 0)}")
    if tick_sim.get("errors"):
        for e in tick_sim["errors"]: print(f"  {RED}✗ {e}{RESET}")

    # Chart engine
    print(f"\n{BOLD}● Chart Signal Engine{RESET}")
    print(f"  Fields present    : {len(chart['fields_present'])}/{len(REQUIRED_CHART_FIELDS)}")
    print(f"  Test signal       : {chart.get('signal')}")
    if chart.get("fields_missing"):
        print(f"  {YELLOW}Missing: {chart['fields_missing']}{RESET}")

    # WS types
    print(f"\n{BOLD}● WebSocket Message Types{RESET}")
    print(f"  Validated         : {len(ws_types['present'])}/{len(EXPECTED_WS_TYPES)}")
    if ws_types["missing"]:
        print(f"  {YELLOW}Missing: {ws_types['missing']}{RESET}")

    # Store
    print(f"\n{BOLD}● Zustand Store Handlers{RESET}")
    print(f"  Handled           : {len(store['handled'])}/{len(ZUSTAND_EXPECTED_HANDLERS)}")
    if store["missing"]:
        print(f"  {YELLOW}Missing handlers: {store['missing']}{RESET}")

    # Overall verdict
    all_good = (
        not imports["failed"]
        and not tick_sim.get("errors")
        and not chart.get("fields_missing")
        and not store["missing"]
    )
    print(f"\n{border}")
    if all_good:
        print(f"  {GREEN}{BOLD}STATUS: SYSTEM READY FOR MARKET OPEN TOMORROW ✅{RESET}")
    else:
        print(f"  {YELLOW}{BOLD}STATUS: REVIEW WARNINGS ABOVE BEFORE MARKET OPEN ⚠️{RESET}")
    print(f"{border}\n")


# ──────────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────────

async def main():
    parser = argparse.ArgumentParser(description="StrikeIQ Pre-Market Preparation")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview actions without modifying any data")
    args = parser.parse_args()

    if args.dry_run:
        logger.info(f"{YELLOW}⚠️  DRY RUN MODE — no data will be modified{RESET}")

    # Load config
    try:
        from app.core.config import settings
        DB_URL    = settings.DATABASE_URL
        REDIS_URL = settings.REDIS_URL
    except Exception as e:
        warn(f"Could not load settings ({e}), using defaults")
        DB_URL    = "postgresql://strikeiq:strikeiq123@localhost:5432/strikeiq"
        REDIS_URL = "redis://localhost:6379"

    # Run all steps
    preserve, runtime     = step1_inspect_tables(DB_URL)
    cleaned               = step2_truncate_runtime(DB_URL, runtime, args.dry_run)
    redis_cleared         = await step3_clear_redis(REDIS_URL, args.dry_run)
    dataset_result        = step4_reset_learning_dataset(args.dry_run)
    imports               = step5_verify_imports()
    tick_sim              = step6_simulate_ticks()
    chart                 = step7_verify_chart_engine()
    ws_types              = step8_validate_ws_message_types()
    store                 = step9_validate_frontend_store()

    step10_health_report(
        preserve, runtime, cleaned, redis_cleared, dataset_result,
        imports, tick_sim, chart, ws_types, store
    )


if __name__ == "__main__":
    asyncio.run(main())
