"""
AI Signal Log Model - SQLAlchemy ORM model for AI signal logging
Replaces raw SQL database operations with standardized ORM approach
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON, Boolean
from sqlalchemy.sql import func
from .database import Base

class AiSignalLog(Base):
    """
    AI Signal Log table for storing AI engine signals
    Replaces duplicate database infrastructure with unified ORM approach
    """
    __tablename__ = "ai_signal_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    snapshot_id = Column(Integer, index=True, nullable=True)
    formula_id = Column(String, index=True, nullable=True)
    symbol = Column(String, index=True)
    signal = Column(String, index=True)
    confidence = Column(Float)
    spot_price = Column(Float)
    strike = Column(Float, nullable=True)
    direction = Column(String, nullable=True)
    entry = Column(Float, nullable=True)
    stop_loss = Column(Float, nullable=True)
    target = Column(Float, nullable=True)
    signal_reason = Column(Text, nullable=True)
    entry_premium = Column(Float, nullable=True)
    exit_premium = Column(Float, nullable=True)
    pnl = Column(Float, nullable=True)
    observed_high = Column(Float, nullable=True)
    observed_low = Column(Float, nullable=True)
    outcome_checked = Column(Boolean, default=False)
    signal_metadata = Column("metadata", JSON)  # Store additional signal metadata as JSON
    
    def __repr__(self):
        return f"<AiSignalLog(id={self.id}, symbol={self.symbol}, signal={self.signal})>"
