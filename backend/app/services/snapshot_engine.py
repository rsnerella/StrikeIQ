import logging
from datetime import datetime
from typing import Dict, Any, Optional
from ..models.market_data import MarketSnapshot
from ..models.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

class SnapshotEngine:
    """
    Core engine for creating and managing market snapshots.
    Ensures data integrity and professional-grade analytics storage.
    """
    
    async def create_snapshot(self, data: Dict[str, Any]) -> Optional[MarketSnapshot]:
        """
        Create a new market snapshot with full analytics details.
        
        Mandatory fields: spot_price, total_call_oi, total_put_oi, gamma_exposure, expected_move.
        Reject if spot_price <= 0.
        """
        try:
            spot = float(data.get("spot_price", 0) or 0)
            
            # Phase 4 GUARD: Reject if spot price is invalid
            if spot <= 0:
                logger.warning(f"Snapshot rejected: spot_price {spot} invalid")
                return None
                
            async with AsyncSessionLocal() as db:
                snapshot = MarketSnapshot(
                    symbol=data.get("symbol"),
                    timestamp=datetime.utcnow(),
                    spot_price=spot,
                    pcr=data.get("pcr", 0.0),
                    total_call_oi=int(data.get("total_call_oi", 0) or 0),
                    total_put_oi=int(data.get("total_put_oi", 0) or 0),
                    atm_strike=float(data.get("atm_strike", 0) or 0),
                    gamma_exposure=float(data.get("gamma_exposure", 0) or 0),
                    expected_move=float(data.get("expected_move", 0) or 0),
                    vwap=data.get("vwap"),
                    market_status="OPEN"
                )
                
                db.add(snapshot)
                await db.commit()
                await db.refresh(snapshot)
                
                logger.debug(f"Market snapshot created: {snapshot.symbol} @ {snapshot.spot_price}")
                print("[SNAPSHOT CREATED]", snapshot)
                return snapshot
                
        except Exception as e:
            logger.error(f"Failed to create market snapshot: {e}")
            return None

snapshot_engine = SnapshotEngine()
