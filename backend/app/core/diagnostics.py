import time
import logging

logger = logging.getLogger("strikeiq.diagnostics")
logger.setLevel(logging.INFO)

# Pipeline counters for break detection
ticks_received = 0
chain_updates = 0
db_saves = 0
last_pipeline_stats = time.time()

def diag(stage, message):
    logger.info(f"[DIAG] {stage} | {message}")

def increment_counter(counter_name):
    """Increment pipeline counter"""
    global ticks_received, chain_updates, db_saves
    if counter_name == "ticks_received":
        ticks_received += 1
    elif counter_name == "chain_updates":
        chain_updates += 1
    elif counter_name == "db_saves":
        db_saves += 1

def log_pipeline_stats():
    """Log pipeline statistics every 60 seconds"""
    global ticks_received, chain_updates, db_saves, last_pipeline_stats
    
    current_time = time.time()
    if current_time - last_pipeline_stats >= 60:
        diag("PIPELINE_STATS", 
             f"ticks={ticks_received} chain_updates={chain_updates} db_saves={db_saves}")
        last_pipeline_stats = current_time
