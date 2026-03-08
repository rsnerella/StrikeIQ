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
        
    def store_prediction(self, formula_id: str, signal: str, confidence: float, spot: float):
        """
        Store a prediction signal using SQLAlchemy ORM
        
        Args:
            formula_id: Formula identifier (e.g., F01, F02, etc.)
            signal: Trading signal (BUY/SELL)
            confidence: Confidence level (0.0 to 1.0)
            spot: Current NIFTY spot price
        """
        try:
            # Get database session
            db = SessionLocal()
            
            # Create signal log record
            signal_log = AiSignalLog(
                symbol="BANKNIFTY",  # Default symbol for now
                signal=f"{formula_id}_{signal}",  # Combine formula and signal
                confidence=confidence,
                spot_price=spot,
                metadata={
                    'formula_id': formula_id,
                    'raw_signal': signal,
                    'prediction_type': 'formula_prediction'
                }
            )
            
            # Add to session and commit
            db.add(signal_log)
            db.commit()
            
            logger.info(f"Prediction stored: {formula_id} {signal} @ {spot} (confidence: {confidence})")
            return True
            
        except Exception as e:
            logger.error(f"Error storing prediction: {e}")
            # Rollback on error
            try:
                db.rollback()
            except:
                pass
            return False
        finally:
            # Always close session
            try:
                db.close()
            except:
                pass
            
    def get_pending_predictions(self):
        """Get all predictions that haven't been checked for outcomes"""
        try:
            # Get database session
            db = SessionLocal()
            
            # Query for recent formula predictions
            from datetime import timedelta
            cutoff_time = datetime.now() - timedelta(minutes=5)
            
            signals = db.query(AiSignalLog).filter(
                AiSignalLog.metadata['prediction_type'].astext == 'formula_prediction'
            ).filter(
                AiSignalLog.timestamp >= cutoff_time
            ).all()
            
            pending_predictions = []
            for signal in signals:
                # Extract formula info from metadata
                metadata = signal.metadata or {}
                formula_id = metadata.get('formula_id', 'UNKNOWN')
                raw_signal = metadata.get('raw_signal', 'UNKNOWN')
                
                pending_predictions.append({
                    'id': signal.id,
                    'formula_id': formula_id,
                    'signal': raw_signal,
                    'confidence': signal.confidence,
                    'nifty_spot': signal.spot_price,
                    'prediction_time': signal.timestamp
                })
                
            logger.info(f"Found {len(pending_predictions)} pending predictions")
            return pending_predictions
            
        except Exception as e:
            logger.error(f"Error fetching pending predictions: {e}")
            return []
        finally:
            try:
                db.close()
            except:
                pass
            
    def mark_prediction_checked(self, prediction_id: int, outcome: str):
        """Mark a prediction as checked and update its outcome"""
        try:
            # Get database session
            db = SessionLocal()
            
            # Find the signal log record
            signal_log = db.query(AiSignalLog).filter(AiSignalLog.id == prediction_id).first()
            
            if signal_log:
                # Update metadata with outcome
                metadata = signal_log.metadata or {}
                metadata['outcome'] = outcome
                metadata['outcome_time'] = datetime.now().isoformat()
                metadata['outcome_checked'] = True
                
                signal_log.metadata = metadata
                db.commit()
                
                logger.info(f"Prediction {prediction_id} marked as checked with outcome: {outcome}")
                return True
            else:
                logger.error(f"Prediction {prediction_id} not found")
                return False
                
        except Exception as e:
            logger.error(f"Error marking prediction as checked: {e}")
            # Rollback on error
            try:
                db.rollback()
            except:
                pass
            return False
        finally:
            # Always close session
            try:
                db.close()
            except:
                pass

# Global prediction service instance
prediction_service = PredictionService()
