"""
Timeframe Aggregator for StrikeIQ
Aggregates 1m snapshots into higher timeframe views (5m, 15m)
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class TimeframeAggregator:
    """
    Aggregates granular 1m or tick-level snapshots into higher timeframe summaries.
    Essential for multi-timeframe AI analysis.
    """
    
    def __init__(self):
        logger.info("TimeframeAggregator initialized")

    def aggregate(self, snapshots: List[Dict[str, Any]], window_minutes: int) -> Optional[Dict[str, Any]]:
        """
        Aggregates the last N minutes of snapshots into a single view.
        Returns a summary dict containing OHLC, volume, and OI trends.
        """
        if not snapshots:
            return None
            
        # Filter snapshots within the last window_minutes
        now = datetime.now().timestamp()
        cutoff = now - (window_minutes * 60)
        
        relevant = [s for s in snapshots if s.get("timestamp", 0) >= cutoff]
        if not relevant:
            # Fallback: take last few snapshots if time-based filtering returns empty
            # (useful for testing or slow markets)
            relevant = snapshots[-window_minutes:] if len(snapshots) >= window_minutes else snapshots

        if not relevant:
            return None

        # Compute aggregate metrics
        first = relevant[0]
        last = relevant[-1]
        
        spots = [s.get("spot", 0) for s in relevant if s.get("spot", 0) > 0]
        
        if not spots:
            return None

        return {
            "window_minutes": window_minutes,
            "open": first.get("spot", 0),
            "high": max(spots),
            "low": min(spots),
            "close": last.get("spot", 0),
            "pcr_start": first.get("option_chain", {}).get("pcr", 1.0),
            "pcr_end": last.get("option_chain", {}).get("pcr", 1.0),
            "oi_delta": float(last.get("option_chain", {}).get("total_oi", 0)) - float(first.get("option_chain", {}).get("total_oi", 0)),
            "snapshot_count": len(relevant)
        }

    def get_5m_view(self, snapshots: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        return self.aggregate(snapshots, 5)

    def get_15m_view(self, snapshots: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        return self.aggregate(snapshots, 15)

timeframe_aggregator = TimeframeAggregator()
