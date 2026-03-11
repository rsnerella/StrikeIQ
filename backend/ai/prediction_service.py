from datetime import datetime
from typing import Optional
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.database import AsyncSessionLocal
from app.models.ai_signal_log import AiSignalLog

logger = logging.getLogger(__name__)

class PredictionService:
    def __init__(self):
        # Use SQLAlchemy session instead of duplicate database connection
        pass
        
    async def store_prediction(self, formula_id: str, signal: str, confidence: float, spot: float, 
                               snapshot_id: Optional[int] = None, strike: Optional[float] = None,
                               direction: Optional[str] = None, entry: Optional[float] = None,
                               stop_loss: Optional[float] = None, target: Optional[float] = None,
                               reason: Optional[str] = None, entry_premium: Optional[float] = None,
                               expected_move: Optional[float] = None):
        try:
            async with AsyncSessionLocal() as db:
                signal_log = AiSignalLog(
                    snapshot_id=snapshot_id,
                    formula_id=formula_id,
                    symbol="NIFTY", # Standardized to NIFTY
                    signal=f"{formula_id}_{signal}",
                    confidence=confidence,
                    spot_price=spot,
                    strike=strike,
                    direction=direction or signal,
                    entry=entry or spot,
                    stop_loss=stop_loss,
                    target=target,
                    signal_reason=reason,
                    entry_premium=entry_premium,
                    signal_metadata={
                        'formula_id': formula_id,
                        'raw_signal': signal,
                        'prediction_type': 'formula_prediction',
                        'expected_move': expected_move
                    }
                )
                db.add(signal_log)
                await db.commit()
                logger.info(f"Prediction stored: {formula_id} {signal} @ {spot} (Snapshot: {snapshot_id})")
                return True
        except Exception as e:
            logger.error(f"Error storing prediction: {e}")
            return False
            
    async def get_pending_predictions(self):
        """Get pending predictions using async SQLAlchemy"""
        try:
            from sqlalchemy import select
            from datetime import timedelta
            cutoff_time = datetime.now() - timedelta(minutes=60) # Increased window
            
            async with AsyncSessionLocal() as db:
                stmt = select(AiSignalLog).where(
                    AiSignalLog.timestamp >= cutoff_time
                )
                result = await db.execute(stmt)
                signals = result.scalars().all()
                
                pending = []
                for s in signals:
                    meta = s.signal_metadata or {}
                    if meta.get('prediction_type') == 'formula_prediction' and not meta.get('outcome_checked'):
                        pending.append({
                            'id': s.id,
                            'formula_id': meta.get('formula_id', 'UNKNOWN'),
                            'signal': meta.get('raw_signal', 'UNKNOWN'),
                            'confidence': s.confidence,
                            'nifty_spot': s.spot_price,
                            'prediction_time': s.timestamp
                        })
                return pending
        except Exception as e:
            logger.error(f"Error fetching pending predictions: {e}")
            return []
            
    async def mark_prediction_checked(self, prediction_id: int, outcome: str):
        try:
            async with AsyncSessionLocal() as db:
                from sqlalchemy import select
                stmt = select(AiSignalLog).where(AiSignalLog.id == prediction_id)
                result = await db.execute(stmt)
                signal_log = result.scalar_one_or_none()
                
                if signal_log:
                    metadata = dict(signal_log.signal_metadata or {})
                    metadata['outcome'] = outcome
                    metadata['outcome_time'] = datetime.now().isoformat()
                    metadata['outcome_checked'] = True
                    
                    signal_log.signal_metadata = metadata
                    signal_log.outcome_checked = True
                    await db.commit()
                    return True
                return False
        except Exception as e:
            logger.error(f"Error marking prediction checked: {e}")
            return False

# Global prediction service instance
prediction_service = PredictionService()
