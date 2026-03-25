"""
Centralized AI Logger for StrikeIQ
Clean, decision-relevant logging only
"""

import logging
from typing import Any, Optional

# Enforce INFO level - block DEBUG
LOG_LEVEL = "INFO"

# Configure clean logger
logger = logging.getLogger("strikeiq_ai")
logger.setLevel(logging.INFO)

# Prevent duplicate handlers
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('[AI] %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

def log(msg: str, data: Optional[Any] = None) -> None:
    """
    Clean AI logging with optional data
    
    Args:
        msg: Log message
        data: Optional data to format (will be simplified)
    """
    if data is not None:
        # Handle different data types cleanly
        if isinstance(data, dict):
            # Only include key decision metrics
            clean_data = {}
            for key, value in data.items():
                if key in ['spot', 'confidence', 'signal', 'pcr', 'rsi', 'gamma', 'action']:
                    clean_data[key] = value
            if clean_data:
                msg += f" {clean_data}"
        elif isinstance(data, (int, float, str)):
            msg += f" {data}"
    
    logger.info(msg)

def log_market_data(spot: float, pcr: float, rsi: float = None, gamma: str = None) -> None:
    """Log key market metrics"""
    msg = f"Spot: {spot}"
    if pcr is not None:
        msg += f" | PCR: {pcr}"
    if rsi is not None:
        msg += f" | RSI: {rsi}"
    if gamma is not None:
        msg += f" | Gamma: {gamma}"
    log(msg)

def log_decision(confidence: float, signal: str) -> None:
    """Log trading decision"""
    log(f"Confidence: {confidence} | Signal: {signal}")

def log_fetching(resource: str) -> None:
    """Log resource fetching"""
    log(f"Fetching {resource}...")

def log_error(msg: str, error: Exception = None) -> None:
    """Log error cleanly"""
    if error:
        log(f"ERROR: {msg} - {str(error)[:100]}")
    else:
        log(f"ERROR: {msg}")

# Block debug logging at the module level
def debug_log(msg: str) -> None:
    """Debug logging stub - does nothing"""
    pass
