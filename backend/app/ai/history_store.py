"""
Bounded History Store for StrikeIQ
Maintains a sliding window of snapshots per symbol to prevent memory leaks
"""

import logging
from collections import deque
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class BoundedHistoryStore:
    """
    In-memory store for market snapshots with fixed capacity.
    Ensures memory safety for long-running production sessions.
    """
    
    def __init__(self, max_len: int = 400):
        self._max_len = max_len
        self._store: Dict[str, deque] = {}
        logger.info(f"BoundedHistoryStore initialized with max_len={max_len}")

    def append(self, symbol: str, snapshot: Dict[str, Any]) -> None:
        """Add a new snapshot for a symbol, dropping the oldest if at capacity."""
        if symbol not in self._store:
            self._store[symbol] = deque(maxlen=self._max_len)
        
        self._store[symbol].append(snapshot)

    def get_history(self, symbol: str, n: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get the last N snapshots for a symbol.
        If N is None or larger than available, returns all available.
        """
        if symbol not in self._store:
            return []
        
        history = list(self._store[symbol])
        if n is not None:
            return history[-n:]
        return history

    def get_latest(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get the most recent snapshot for a symbol."""
        if symbol not in self._store or not self._store[symbol]:
            return None
        return self._store[symbol][-1]

    def clear(self, symbol: Optional[str] = None) -> None:
        """Clear history for a specific symbol or all symbols."""
        if symbol:
            if symbol in self._store:
                self._store[symbol].clear()
                logger.info(f"History cleared for {symbol}")
        else:
            self._store.clear()
            logger.info("All history cleared")

    @property
    def capacity(self) -> int:
        return self._max_len

# Global singleton for the application
history_store = BoundedHistoryStore()
