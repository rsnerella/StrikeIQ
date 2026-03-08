"""
Signal Logger Service - Unified AI signal logging with SQLAlchemy
Replaces duplicate database infrastructure with standardized ORM approach
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from ..models.database import AsyncSessionLocal
from ..models.ai_signal_log import AiSignalLog

logger = logging.getLogger(__name__)

class SignalLogger:
    """
    Unified signal logging service using SQLAlchemy ORM
    Replaces direct psycopg2 connections with standardized database access
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def log_ai_signal(
        self,
        symbol: str,
        signal: str,
        confidence: float,
        spot_price: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Log AI signal to database using SQLAlchemy ORM
        
        Args:
            symbol: Trading symbol (e.g., "BANKNIFTY")
            signal: Signal type (e.g., "BULLISH", "LIQUIDITY_SWEEP_UP")
            confidence: Signal confidence (0.0 to 1.0)
            spot_price: Current spot price
            metadata: Additional signal metadata as dictionary
            
        Returns:
            bool: Success status
        """
        try:
            # Get database session
            db = SessionLocal()
            
            # Create signal log record
            signal_log = AiSignalLog(
                symbol=symbol,
                signal=signal,
                confidence=confidence,
                spot_price=spot_price,
                metadata=metadata or {}
            )
            
            # Add to session and commit
            db.add(signal_log)
            db.commit()
            
            self.logger.info(f"AI signal logged: {signal} for {symbol} with confidence {confidence:.3f}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to log AI signal: {e}")
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
    
    def get_recent_signals(
        self,
        symbol: Optional[str] = None,
        limit: int = 100,
        hours: Optional[int] = None
    ) -> list:
        """
        Retrieve recent AI signals from database
        
        Args:
            symbol: Filter by symbol (optional)
            limit: Maximum number of records to return
            hours: Filter by last N hours (optional)
            
        Returns:
            list: List of AiSignalLog records
        """
        try:
            db = SessionLocal()
            query = db.query(AiSignalLog)
            
            # Apply filters
            if symbol:
                query = query.filter(AiSignalLog.symbol == symbol)
            
            if hours:
                from datetime import timedelta
                cutoff_time = datetime.now() - timedelta(hours=hours)
                query = query.filter(AiSignalLog.timestamp >= cutoff_time)
            
            # Order by timestamp and limit
            signals = query.order_by(AiSignalLog.timestamp.desc()).limit(limit).all()
            
            self.logger.info(f"Retrieved {len(signals)} recent signals")
            return signals
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve recent signals: {e}")
            return []
        finally:
            try:
                db.close()
            except:
                pass
    
    def get_signal_statistics(
        self,
        symbol: Optional[str] = None,
        hours: int = 24
    ) -> Dict[str, Any]:
        """
        Get signal statistics for analysis
        
        Args:
            symbol: Filter by symbol (optional)
            hours: Time window in hours
            
        Returns:
            dict: Signal statistics
        """
        try:
            db = SessionLocal()
            query = db.query(AiSignalLog)
            
            # Apply filters
            if symbol:
                query = query.filter(AiSignalLog.symbol == symbol)
            
            from datetime import timedelta
            cutoff_time = datetime.now() - timedelta(hours=hours)
            query = query.filter(AiSignalLog.timestamp >= cutoff_time)
            
            # Get all signals for statistics
            signals = query.all()
            
            if not signals:
                return {
                    'total_signals': 0,
                    'unique_signals': 0,
                    'avg_confidence': 0.0,
                    'signal_types': {}
                }
            
            # Calculate statistics
            total_signals = len(signals)
            unique_signals = len(set(s.signal for s in signals))
            avg_confidence = sum(s.confidence for s in signals) / total_signals
            
            # Count signal types
            signal_types = {}
            for signal in signals:
                signal_type = signal.signal
                signal_types[signal_type] = signal_types.get(signal_type, 0) + 1
            
            stats = {
                'total_signals': total_signals,
                'unique_signals': unique_signals,
                'avg_confidence': avg_confidence,
                'signal_types': signal_types
            }
            
            self.logger.info(f"Generated statistics for {total_signals} signals")
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to generate signal statistics: {e}")
            return {}
        finally:
            try:
                db.close()
            except:
                pass

# Global signal logger instance
signal_logger = SignalLogger()
