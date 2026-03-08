"""
AI Models for StrikeIQ Trading System

SQLAlchemy models for AI signal logs and related tables.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Index
from app.core.database import Base, engine


class AISignalLog(Base):
    """AI Signal Logs Table"""
    __tablename__ = "ai_signal_logs"
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(20))
    signal = Column(String(50))
    confidence = Column(Float)
    spot_price = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)


class MarketSnapshot(Base):
    """Market Snapshot Table for AI Analysis"""
    __tablename__ = "market_snapshot"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False)
    spot_price = Column(Float, nullable=False)
    pcr = Column(Float, nullable=False)  # Put-Call Ratio
    total_call_oi = Column(Float, nullable=False)
    total_put_oi = Column(Float, nullable=False)
    atm_strike = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Index for performance
    __table_args__ = (
        Index('idx_market_snapshot_symbol_timestamp', 'symbol', 'timestamp'),
    )
    
    def __repr__(self):
        return f"<MarketSnapshot(symbol={self.symbol}, spot_price={self.spot_price}, pcr={self.pcr})>"
