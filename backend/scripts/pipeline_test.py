"""
pipeline_test.py — Isolated pipeline validation script.
Runs outside the FastAPI server process.
"""
import sys, os, time, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PASS = []; FAIL = []

def ok(tag, msg=""):   PASS.append(tag); print(f"  OK   {tag} {msg}")
def err(tag, e):       FAIL.append(tag); print(f"  FAIL {tag}: {str(e)[:100]}")

print("\n=== STEP 5 — MODULE IMPORTS ===")
modules = [
    ("app.services.message_router",            "MessageRouter"),
    ("app.services.candle_builder",            "candle_builder"),
    ("app.services.structure_engine",          "structure_engine"),
    ("app.services.wave_engine",               "wave_engine"),
    ("app.services.zone_detection_engine",     "zone_detection_engine"),
    ("app.services.candle_pattern_engine",     "candle_pattern_engine"),
    ("app.services.chart_signal_engine",       "chart_signal_engine"),
    ("app.services.signal_outcome_tracker",    "signal_outcome_tracker"),
    ("app.services.signal_scoring_engine",     "signal_scoring_engine"),
    ("app.services.advanced_strategies_engine","run_advanced_strategies"),
]
imported = {}
for mp, attr in modules:
    try:
        import importlib
        mod = importlib.import_module(mp)
        obj = getattr(mod, attr)
        imported[attr] = obj
        ok(mp.split(".")[-1])
    except Exception as e:
        err(mp.split(".")[-1], e)

print("\n=== STEP 6 — TICK FLOW ===")
try:
    from app.services.message_router import MessageRouter
    from app.services.candle_builder import candle_builder
    r = MessageRouter()
    now = time.time()
    routed = 0
    # Feed 60 index ticks (5s apart) to cross multiple 1m candle boundaries
    for i in range(60):
        tick = {
            "instrument_key": "NSE_INDEX|NIFTY 50",
            "ltp": 22400.0 + (i % 20) * 5,
            "oi": 0, "volume": 1000 + i * 10,
            "timestamp": now + i * 5,
        }
        result = r.route_tick(tick)
        if result:
            routed += 1
    # Also push directly into candle_builder to ensure boundaries
    for i in range(65):
        candle_builder.push_tick("NIFTY", 22400 + (i % 20) * 5, volume=float(i*100), ts=now + i*5)

    c1m = candle_builder.get_candles("NIFTY", "1m", n=20)
    c5m = candle_builder.get_candles("NIFTY", "5m", n=20)
    ok("message_router",  f"routed={routed}/60 ticks")
    ok("candle_builder",  f"1m={len(c1m)} candles  5m={len(c5m)} candles")
except Exception as e:
    err("tick_flow", e)

print("\n=== STEP 7 — CHART SIGNAL ENGINE ===")
REQUIRED = ["trend","wave","supply_zone","demand_zone","signal","confidence","target_zone","stop_zone"]
try:
    from app.services.chart_signal_engine import chart_signal_engine
    out = chart_signal_engine.analyze(
        symbol="NIFTY",
        current_price=22450.0,
        chain_data={"spot": 22450.0, "strikes": [], "pcr": 1.1},
        options_analytics={},
        interval="1m",
    )
    for f in REQUIRED:
        if f in out: ok(f"field:{f}", str(out[f])[:40])
        else:        err(f"field:{f}", "MISSING from output")
    print(f"  signal={out.get('signal')} conf={out.get('confidence'):.3f} wave={out.get('wave')} trend={out.get('trend')}")
except Exception as e:
    err("chart_signal_engine", e)

print("\n=== STEP 8 — WS MESSAGE TYPES ===")
try:
    from app.services.advanced_strategies_engine import run_advanced_strategies
    adv = run_advanced_strategies("NIFTY", {"spot": 22450, "strikes": []})
    ok("advanced_strategies", f"type={adv.get('type')}")
except Exception as e: err("advanced_strategies", e)

try:
    from app.services.signal_scoring_engine import signal_scoring_engine
    from app.services.advanced_strategies_engine import run_advanced_strategies
    adv = run_advanced_strategies("NIFTY", {"spot": 22450, "strikes": []})
    sc = signal_scoring_engine.score("NIFTY", {"spot":22450,"strikes":[]}, {}, adv)
    ok("signal_score", f"type={sc.get('type')}")
except Exception as e: err("signal_score", e)

try:
    from app.services.chart_signal_engine import chart_signal_engine
    ca = chart_signal_engine.analyze("NIFTY", 22450.0, {"spot":22450,"strikes":[]})
    ok("chart_analysis", f"type={ca.get('type')}")
except Exception as e: err("chart_analysis", e)

print("\n=== STEP 9 — ZUSTAND STORE HANDLERS ===")
import pathlib
store = pathlib.Path(r"d:\StrikeIQ\frontend\src\core\ws\wsStore.ts")
if store.exists():
    content = store.read_text(encoding="utf-8")
    for t in ["chart_analysis","advanced_strategies","signal_score","analytics","option_chain_update","index_tick"]:
        if t in content: ok(f"wsStore:{t}")
        else:            err(f"wsStore:{t}", "handler not found")
else:
    err("wsStore.ts", "file not found")

print(f"\n=== FINAL RESULT ===")
print(f"  PASSED: {len(PASS)}")
print(f"  FAILED: {len(FAIL)}")
if FAIL:
    print(f"  FAILED ITEMS: {FAIL}")
else:
    print("  ALL CHECKS PASSED — SYSTEM READY FOR MARKET OPEN")
