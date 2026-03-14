"""
Symbol+expiry scoped LiveOptionChainBuilder Registry
Ensures SINGLE builder instance per symbol:expiry
"""

from typing import Dict
from app.services.live_option_chain_builder import LiveOptionChainBuilder

# SYMBOL+EXPIRY SCOPED INSTANCE STORE
_builder_instances: Dict[str, LiveOptionChainBuilder] = {}


def get_live_chain_builder(symbol: str, expiry: str = "") -> LiveOptionChainBuilder:
    """
    ISSUE 4 FIX: Returns SAME builder instance per symbol:expiry.
    Prevents dual instance ingestion bug.
    """
    # Use default expiry if not provided
    if not expiry:
        expiry = "1970-01-01"  # Default placeholder
        
    key = f"{symbol}:{expiry}"

    if key not in _builder_instances:
        _builder_instances[key] = LiveOptionChainBuilder(symbol, expiry)

    return _builder_instances[key]